import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.courses.models import (
    ContentType,
    Subject,
    SubjectStatus,
    Subtopic,
    SubtopicContent,
    Topic,
)
from apps.learning.models import ItemProgress, ProgressStatus
from apps.programs.models import Class, ClassSubject, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def student(db):
    u = User.objects.create_user(
        email="learner@test.local", password="DemoPass123!", first_name="Learn", last_name="Er"
    )
    assign_role(user=u, role=Role.STUDENT)
    return u


@pytest.fixture
def tutor(db):
    u = User.objects.create_user(
        email="tutorlearn@test.local", password="DemoPass123!", is_staff=True, first_name="Tu", last_name="Tor"
    )
    assign_role(user=u, role=Role.TUTOR)
    return u


@pytest.fixture
def learning_setup(db, student, tutor):
    program = Program.objects.create(title="P", slug="p-learn", status=PublishStatus.PUBLISHED)
    cohort = Cohort.objects.create(
        program=program, name="C", slug="c-learn", status=CohortStatus.RUNNING, capacity=40
    )
    klass = Class.objects.create(
        cohort=cohort, name="Foundation", slug="foundation", status=PublishStatus.PUBLISHED
    )
    subject = Subject.objects.create(
        title="Spirit Foundations",
        slug="spirit-foundations-learn",
        status=SubjectStatus.PUBLISHED,
        description_json={"html": "<p>Overview</p>"},
        intended_learners={"learn": ["A", "B", "C", "D"], "requirements": [], "audience": []},
    )
    subject.instructors.add(tutor)
    ClassSubject.objects.create(class_ref=klass, subject=subject, order=0)
    Enrollment.objects.create(
        user=student, class_ref=klass, cohort=cohort, status=EnrollmentStatus.ACTIVE
    )
    topic = Topic.objects.create(subject=subject, title="Getting started", order=0, is_published=True)
    lesson = Subtopic.objects.create(
        topic=topic,
        title="Welcome",
        order=0,
        is_published=True,
        estimated_time_s=300,
        min_time_s=20,
        is_free_preview=True,
    )
    quiz = Subtopic.objects.create(
        topic=topic,
        title="Check-in",
        order=1,
        is_published=True,
        estimated_time_s=120,
        min_time_s=10,
    )
    SubtopicContent.objects.create(
        subtopic=lesson,
        content_type=ContentType.ARTICLE,
        title="Welcome article",
        body_json={"html": "<p>Hello</p>"},
        processing_status="ready",
        duration_s=300,
    )
    return {
        "subject": subject,
        "klass": klass,
        "lesson": lesson,
        "quiz": quiz,
        "student": student,
        "tutor": tutor,
    }


def auth(api: APIClient, user: User) -> str:
    r = api.post("/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json")
    assert r.status_code == 200
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.mark.django_db
def test_my_learning_and_landing(api, learning_setup):
    student = learning_setup["student"]
    subject = learning_setup["subject"]
    auth(api, student)

    mine = api.get("/api/v1/me/learning")
    assert mine.status_code == 200
    assert len(mine.data["classes"]) == 1
    assert mine.data["subjects"][0]["subject_slug"] == subject.slug

    landing = api.get(f"/api/v1/learn/subjects/{subject.slug}/landing")
    assert landing.status_code == 200
    assert landing.data["has_access"] is True
    assert landing.data["continue_subtopic_id"]


@pytest.mark.django_db
def test_viewer_heartbeat_study_gate_complete(api, learning_setup):
    student = learning_setup["student"]
    subject = learning_setup["subject"]
    lesson = learning_setup["lesson"]
    auth(api, student)

    viewer = api.get(f"/api/v1/learn/subtopics/{lesson.id}/viewer")
    assert viewer.status_code == 200
    assert viewer.data["content"]["content_type"] == "article"
    assert viewer.data["progress"]["can_complete"] is False

    outline = api.get(f"/api/v1/learn/subjects/{subject.id}/outline")
    assert outline.status_code == 200
    assert outline.data["total_count"] == 2

    early = api.post(f"/api/v1/learn/subtopics/{lesson.id}/complete", {}, format="json")
    assert early.status_code == 400
    assert early.data["code"] == "study_time_gate"

    # accumulate study time via heartbeats (clamped to 30s each)
    for _ in range(1):
        hb = api.post(
            f"/api/v1/learn/subtopics/{lesson.id}/heartbeat",
            {"delta_s": 25},
            format="json",
        )
        assert hb.status_code == 200
    assert hb.data["time_spent_s"] >= 20
    assert hb.data["can_complete"] is True

    done = api.post(f"/api/v1/learn/subtopics/{lesson.id}/complete", {}, format="json")
    assert done.status_code == 200
    assert done.data["status"] == ProgressStatus.COMPLETED

    ip = ItemProgress.objects.get(user=student, subtopic=lesson)
    assert ip.status == ProgressStatus.COMPLETED

    outline2 = api.get(f"/api/v1/learn/subjects/{subject.id}/outline")
    assert outline2.data["completed_count"] == 1
    assert outline2.data["percent"] == 50


@pytest.mark.django_db
def test_qa_and_notes(api, learning_setup):
    student = learning_setup["student"]
    tutor = learning_setup["tutor"]
    subject = learning_setup["subject"]
    lesson = learning_setup["lesson"]

    auth(api, student)
    q = api.post(
        f"/api/v1/learn/subjects/{subject.id}/qa",
        {"title": "What is spirit science?", "body": "Explain briefly.", "subtopic_id": str(lesson.id)},
        format="json",
    )
    assert q.status_code == 201, q.data
    qid = q.data["id"]

    note = api.post(
        f"/api/v1/learn/subtopics/{lesson.id}/notes",
        {"body": "Remember this", "timestamp_s": 12},
        format="json",
    )
    assert note.status_code == 201
    notes = api.get(f"/api/v1/learn/subtopics/{lesson.id}/notes")
    assert len(notes.data) == 1

    auth(api, tutor)
    ans = api.post(
        f"/api/v1/learn/questions/{qid}/answers",
        {"body": "It is the study of consciousness and matter."},
        format="json",
    )
    assert ans.status_code == 201
    assert ans.data["is_instructor"] is True

    qs = api.get(f"/api/v1/learn/subjects/{subject.id}/qa")
    assert qs.data[0]["is_resolved"] is True
    assert len(qs.data[0]["answers"]) == 1

    auth(api, student)
    deleted = api.delete(f"/api/v1/learn/notes/{note.data['id']}")
    assert deleted.status_code == 204


@pytest.mark.django_db
def test_unenrolled_blocked_except_preview(api, learning_setup, db):
    outsider = User.objects.create_user(email="out@test.local", password="DemoPass123!")
    assign_role(user=outsider, role=Role.STUDENT)
    lesson = learning_setup["lesson"]
    quiz = learning_setup["quiz"]
    subject = learning_setup["subject"]

    auth(api, outsider)
    # free preview lesson allowed
    ok = api.get(f"/api/v1/learn/subtopics/{lesson.id}/viewer")
    assert ok.status_code == 200

    blocked = api.get(f"/api/v1/learn/subtopics/{quiz.id}/viewer")
    assert blocked.status_code == 403

    outline = api.get(f"/api/v1/learn/subjects/{subject.id}/outline")
    assert outline.status_code == 200
    locked = [s for t in outline.data["topics"] for s in t["subtopics"] if s["id"] == str(quiz.id)]
    assert locked and locked[0]["locked"] is True
