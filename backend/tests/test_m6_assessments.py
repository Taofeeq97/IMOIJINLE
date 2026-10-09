import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.courses.models import Subject, SubjectStatus, Subtopic, SubtopicKind, Topic
from apps.programs.models import Class, ClassSubject, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def student(db):
    u = User.objects.create_user(
        email="m6student@test.local", password="DemoPass123!", first_name="Stu", last_name="Dent"
    )
    assign_role(user=u, role=Role.STUDENT)
    return u


@pytest.fixture
def tutor(db):
    u = User.objects.create_user(
        email="m6tutor@test.local",
        password="DemoPass123!",
        is_staff=True,
        first_name="Tu",
        last_name="Tor",
    )
    assign_role(user=u, role=Role.TUTOR)
    return u


@pytest.fixture
def m6_setup(db, student, tutor):
    program = Program.objects.create(title="P6", slug="p-m6", status=PublishStatus.PUBLISHED)
    cohort = Cohort.objects.create(
        program=program, name="C6", slug="c-m6", status=CohortStatus.RUNNING, capacity=40
    )
    klass = Class.objects.create(
        cohort=cohort, name="Assess Class", slug="assess-class", status=PublishStatus.PUBLISHED
    )
    subject = Subject.objects.create(
        title="Assessment Subject",
        slug="assessment-subject",
        status=SubjectStatus.PUBLISHED,
    )
    subject.instructors.add(tutor)
    ClassSubject.objects.create(class_ref=klass, subject=subject, order=0)
    Enrollment.objects.create(
        user=student, class_ref=klass, cohort=cohort, status=EnrollmentStatus.ACTIVE
    )
    topic = Topic.objects.create(subject=subject, title="Unit 1", order=0, is_published=True)
    quiz_st = Subtopic.objects.create(
        topic=topic,
        title="Week 1 Quiz",
        order=0,
        kind=SubtopicKind.QUIZ,
        is_published=True,
    )
    assign_st = Subtopic.objects.create(
        topic=topic,
        title="Reflection Essay",
        order=1,
        kind=SubtopicKind.ASSIGNMENT,
        is_published=True,
    )
    return {
        "klass": klass,
        "subject": subject,
        "quiz_st": quiz_st,
        "assign_st": assign_st,
        "student": student,
        "tutor": tutor,
    }


def auth(api: APIClient, user: User) -> str:
    r = api.post(
        "/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json"
    )
    assert r.status_code == 200
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.mark.django_db
def test_quiz_attempt_submit_auto_score(api, m6_setup):
    tutor = m6_setup["tutor"]
    student = m6_setup["student"]
    quiz_st = m6_setup["quiz_st"]

    auth(api, tutor)
    created = api.post(
        f"/api/v1/subtopics/{quiz_st.id}/quiz/",
        {
            "title": "Week 1 Quiz",
            "settings": {"attempts": 2, "pass_pct": 50},
            "release_scores": True,
            "questions": [
                {
                    "prompt": "2+2?",
                    "question_type": "mcq",
                    "choices": [
                        {"id": "a", "text": "3"},
                        {"id": "b", "text": "4"},
                    ],
                    "correct_answer": {"choice_id": "b"},
                    "points": 2,
                    "order": 0,
                },
                {
                    "prompt": "Earth is round",
                    "question_type": "true_false",
                    "choices": [
                        {"id": "t", "text": "True"},
                        {"id": "f", "text": "False"},
                    ],
                    "correct_answer": {"value": True},
                    "points": 1,
                    "order": 1,
                },
                {
                    "prompt": "Capital of Nigeria?",
                    "question_type": "short",
                    "correct_answer": {"text": "Abuja"},
                    "points": 2,
                    "order": 2,
                },
            ],
        },
        format="json",
    )
    assert created.status_code == 200, created.data
    quiz_id = created.data["id"]
    assert float(created.data["points_total"]) == 5
    questions = created.data["questions"]
    assert len(questions) == 3

    detail = api.get(f"/api/v1/quizzes/{quiz_id}")
    assert detail.status_code == 200
    assert "correct_answer" in detail.data["questions"][0]

    auth(api, student)
    student_quiz = api.get(f"/api/v1/quizzes/{quiz_id}")
    assert student_quiz.status_code == 200
    assert "correct_answer" not in student_quiz.data["questions"][0]

    attempt = api.post(f"/api/v1/quizzes/{quiz_id}/attempts", {}, format="json")
    assert attempt.status_code == 201, attempt.data
    attempt_id = attempt.data["id"]
    assert attempt.data["status"] == "in_progress"

    q_mcq, q_tf, q_short = questions
    saved = api.put(
        f"/api/v1/attempts/{attempt_id}/responses",
        {
            "responses": [
                {"question_id": q_mcq["id"], "answer": {"choice_id": "b"}},
                {"question_id": q_tf["id"], "answer": {"value": True}},
                {"question_id": q_short["id"], "answer": {"text": "abuja"}},
            ]
        },
        format="json",
    )
    assert saved.status_code == 200

    submitted = api.post(f"/api/v1/attempts/{attempt_id}/submit", {}, format="json")
    assert submitted.status_code == 200, submitted.data
    assert submitted.data["status"] == "graded"
    assert float(submitted.data["score"]) == 5.0
    assert submitted.data["released"] is True

    review = api.get(f"/api/v1/attempts/{attempt_id}/review")
    assert review.status_code == 200
    assert review.data["released"] is True
    assert float(review.data["score"]) == 5.0
    assert len(review.data["responses"]) == 3
    assert all(r["is_correct"] for r in review.data["responses"])


@pytest.mark.django_db
def test_assignment_grade_rubric_release(api, m6_setup):
    tutor = m6_setup["tutor"]
    student = m6_setup["student"]
    assign_st = m6_setup["assign_st"]
    klass = m6_setup["klass"]

    auth(api, tutor)
    created = api.post(
        f"/api/v1/subtopics/{assign_st.id}/assignment/",
        {
            "title": "Reflection Essay",
            "instructions_json": {"html": "<p>Write a reflection.</p>"},
            "points": 10,
            "rubric": {
                "title": "Reflection rubric",
                "criteria": [
                    {
                        "id": "clarity",
                        "title": "Clarity",
                        "max_points": 5,
                        "levels": [
                            {"label": "Strong", "points": 5},
                            {"label": "Ok", "points": 3},
                        ],
                    },
                    {
                        "id": "depth",
                        "title": "Depth",
                        "max_points": 5,
                        "levels": [
                            {"label": "Deep", "points": 5},
                            {"label": "Shallow", "points": 2},
                        ],
                    },
                ],
            },
        },
        format="json",
    )
    assert created.status_code == 200, created.data
    assignment_id = created.data["id"]
    assert created.data["rubric"]["criteria"][0]["id"] == "clarity"

    auth(api, student)
    submission = api.post(
        f"/api/v1/assignments/{assignment_id}/submissions",
        {
            "text": "My reflection on the week.",
            "link": "https://example.com/doc",
        },
        format="json",
    )
    assert submission.status_code == 201, submission.data
    submission_id = submission.data["id"]
    assert submission.data["status"] == "submitted"

    before = api.get(f"/api/v1/submissions/{submission_id}")
    assert before.status_code == 200
    assert "grade" not in before.data or before.data.get("grade") is None

    auth(api, tutor)
    queue = api.get("/api/v1/grading/queue")
    assert queue.status_code == 200
    assert any(r["submission_id"] == submission_id for r in queue.data["results"])

    graded = api.put(
        f"/api/v1/submissions/{submission_id}/grade",
        {
            "rubric_scores": {
                "clarity": {"points": 5, "comment": "Clear"},
                "depth": {"points": 4, "comment": "Good insight"},
            },
            "feedback_json": {"comment": "Nice work overall."},
        },
        format="json",
    )
    assert graded.status_code == 200, graded.data
    assert float(graded.data["final_score"]) == 9.0
    assert graded.data["released_at"] is None

    released = api.post(
        "/api/v1/grades/release",
        {"submission_ids": [submission_id]},
        format="json",
    )
    assert released.status_code == 200
    assert released.data["results"][0]["ok"] is True

    gradebook = api.get(f"/api/v1/classes/{klass.id}/gradebook")
    assert gradebook.status_code == 200
    assert len(gradebook.data["columns"]) >= 1
    student_row = next(s for s in gradebook.data["students"] if s["user_id"] == str(student.id))
    assert any(g.get("released") and g.get("score") == 9.0 for g in student_row["grades"].values())

    auth(api, student)
    after = api.get(f"/api/v1/submissions/{submission_id}")
    assert after.status_code == 200
    assert after.data["grade"]["final_score"] == 9.0
    assert after.data["grade"]["feedback_json"]["comment"] == "Nice work overall."

    mine = api.get("/api/v1/me/grades")
    assert mine.status_code == 200
    assert any(g["score"] == 9.0 for g in mine.data["results"])


@pytest.mark.django_db
def test_enrollment_required_to_attempt(api, m6_setup, tutor):
    quiz_st = m6_setup["quiz_st"]
    auth(api, tutor)
    created = api.post(
        f"/api/v1/subtopics/{quiz_st.id}/quiz/",
        {
            "title": "Gate Quiz",
            "questions": [
                {
                    "prompt": "Yes?",
                    "question_type": "true_false",
                    "correct_answer": {"value": True},
                    "points": 1,
                }
            ],
        },
        format="json",
    )
    quiz_id = created.data["id"]

    outsider = User.objects.create_user(email="outsider@test.local", password="DemoPass123!")
    assign_role(user=outsider, role=Role.STUDENT)
    auth(api, outsider)
    attempt = api.post(f"/api/v1/quizzes/{quiz_id}/attempts", {}, format="json")
    assert attempt.status_code == 403
    assert attempt.data["code"] == "not_enrolled"
