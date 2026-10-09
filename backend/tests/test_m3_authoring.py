import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.courses.models import Subject


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(email="author@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=u, role=Role.PROGRAM_ADMIN)
    return u


def auth(api: APIClient, user: User) -> str:
    r = api.post("/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json")
    assert r.status_code == 200
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.mark.django_db
def test_authoring_workspace_flow(api, admin_user, stub_storage, stub_documents, stub_mux):
    auth(api, admin_user)
    subject = api.post(
        "/api/v1/subjects/",
        {"title": "Spirit Foundations", "subtitle": "Orientation", "level": "beginner"},
        format="json",
    )
    assert subject.status_code == 201
    sid = subject.data["id"]

    learners = api.put(
        f"/api/v1/subjects/{sid}/intended-learners/",
        {
            "learn": ["Core ideas", "Daily rhythm", "Community norms", "Practice basics"],
            "requirements": ["Open mind"],
            "audience": ["New students"],
        },
        format="json",
    )
    assert learners.status_code == 200

    landing = api.put(
        f"/api/v1/subjects/{sid}/landing/",
        {
            "title": "Spirit Foundations",
            "subtitle": "Start here",
            "description_json": {"html": "<p>A rich landing description for students.</p>"},
            "language": "en",
            "level": "beginner",
            "category": "Foundations",
        },
        format="json",
    )
    assert landing.status_code == 200

    api.put(
        f"/api/v1/subjects/{sid}/messages/",
        {"welcome_message": "Welcome!", "completion_message": "Well done!"},
        format="json",
    )
    api.put(
        f"/api/v1/subjects/{sid}/pricing/",
        {"mode": "class_fee", "amount_kobo": 0, "currency": "NGN"},
        format="json",
    )

    topic = api.post(
        f"/api/v1/subjects/{sid}/topics/",
        {"title": "Getting started", "objective_text": "Orient"},
        format="json",
    )
    assert topic.status_code == 201
    tid = topic.data["id"]

    lesson = api.post(
        f"/api/v1/topics/{tid}/subtopics/",
        {"title": "Welcome video", "kind": "subtopic", "min_time_s": 60},
        format="json",
    )
    quiz = api.post(
        f"/api/v1/topics/{tid}/subtopics/",
        {"title": "Check-in quiz", "kind": "quiz"},
        format="json",
    )
    assert lesson.status_code == 201 and quiz.status_code == 201
    lid = lesson.data["id"]

    article = api.post(
        f"/api/v1/subtopics/{lid}/content/",
        {
            "content_type": "article",
            "body_json": {"html": "<p>Hello learners</p>"},
            "duration_s": 300,
        },
        format="json",
    )
    assert article.status_code == 200
    assert article.data["content_type"] == "article"

    # S3/MinIO presign → client PUT (stubbed) → complete
    presign = api.post(
        "/api/v1/uploads/presign",
        {
            "purpose": "content",
            "filename": "handout.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 12,
            "subtopic_id": lid,
        },
        format="json",
    )
    assert presign.status_code == 201
    assert "upload_url" in presign.data
    assert presign.data["method"] == "PUT"
    upload_id = presign.data["upload_id"]
    complete = api.post(f"/api/v1/uploads/{upload_id}/complete", {}, format="json")
    assert complete.status_code == 200

    pdf_content = api.post(
        f"/api/v1/subtopics/{lid}/content/",
        {"content_type": "pdf", "upload_id": upload_id, "title": "Handout"},
        format="json",
    )
    assert pdf_content.status_code == 200
    assert pdf_content.data["processing_status"] in {"processing", "converted", "ready"}

    lesson2 = api.post(
        f"/api/v1/topics/{tid}/subtopics/",
        {"title": "Reading", "kind": "subtopic"},
        format="json",
    )
    lid2 = lesson2.data["id"]
    presign2 = api.post(
        "/api/v1/uploads/presign",
        {
            "purpose": "content",
            "filename": "notes.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "size_bytes": 20,
        },
        format="json",
    )
    api.post(f"/api/v1/uploads/{presign2.data['upload_id']}/complete", {}, format="json")
    word = api.post(
        f"/api/v1/subtopics/{lid2}/content/",
        {"content_type": "document", "upload_id": presign2.data["upload_id"]},
        format="json",
    )
    assert word.status_code == 200
    assert word.data["processing_status"] in {"processing", "converted"}

    # Mux direct upload create
    lesson3 = api.post(f"/api/v1/topics/{tid}/subtopics/", {"title": "Film", "kind": "subtopic"}, format="json")
    mux = api.post(
        f"/api/v1/subtopics/{lesson3.data['id']}/mux-upload",
        {"cors_origin": "http://localhost:3000"},
        format="json",
    )
    assert mux.status_code == 201
    assert mux.data["upload_url"].startswith("https://upload.mux.com")

    res = api.post(
        f"/api/v1/subtopics/{lid}/resources/",
        {"kind": "link", "title": "Extra reading", "url": "https://example.com/guide"},
        format="json",
    )
    assert res.status_code == 201

    checklist = api.get(f"/api/v1/subjects/{sid}/checklist/")
    assert checklist.status_code == 200
    assert checklist.data["can_publish"] is True

    tree = api.get(f"/api/v1/subjects/{sid}/curriculum/")
    assert tree.status_code == 200
    assert len(tree.data) == 1

    preview = api.post(f"/api/v1/subjects/{sid}/preview-token/", {}, format="json")
    assert preview.status_code == 200
    token = preview.data["token"]
    public = api.get(f"/api/v1/public/subjects/{sid}/preview?token={token}")
    assert public.status_code == 200
    assert public.data["preview"] is True

    published = api.post(f"/api/v1/subjects/{sid}/publish/", {}, format="json")
    assert published.status_code == 200
    assert published.data["status"] == "published"


@pytest.mark.django_db
def test_duplicate_topic_and_reorder(api, admin_user):
    auth(api, admin_user)
    subject = Subject.objects.create(title="Dup", slug="dup-m3")
    t = api.post(f"/api/v1/subjects/{subject.id}/topics/", {"title": "One"}, format="json")
    tid = t.data["id"]
    api.post(f"/api/v1/topics/{tid}/subtopics/", {"title": "A", "kind": "subtopic"}, format="json")
    api.post(f"/api/v1/topics/{tid}/subtopics/", {"title": "B", "kind": "subtopic"}, format="json")
    dup = api.post(f"/api/v1/topics/{tid}/duplicate/", {}, format="json")
    assert dup.status_code == 201
    assert dup.data["title"].endswith("(copy)")

    topics = api.get(f"/api/v1/subjects/{subject.id}/topics/")
    ids = [row["id"] for row in topics.data]
    reorder = api.post(
        f"/api/v1/subjects/{subject.id}/topics/reorder/",
        {"ordered_ids": list(reversed(ids))},
        format="json",
    )
    assert reorder.status_code == 200
    assert reorder.data[0]["id"] == ids[-1]
