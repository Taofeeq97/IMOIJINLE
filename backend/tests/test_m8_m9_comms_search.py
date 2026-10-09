import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.courses.models import Subject, SubjectStatus
from apps.programs.models import Class, ClassSubject, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


def auth(api, user):
    r = api.post("/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json")
    assert r.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


@pytest.mark.django_db
def test_announcements_notifications_analytics_search_oidc(api, db):
    admin = User.objects.create_user(email="comms@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=admin, role=Role.PROGRAM_ADMIN)
    student = User.objects.create_user(email="listen@test.local", password="DemoPass123!")
    assign_role(user=student, role=Role.STUDENT)
    program = Program.objects.create(title="Spirit Search", slug="spirit-s", status=PublishStatus.PUBLISHED)
    cohort = Cohort.objects.create(program=program, name="Coh", slug="coh-s", status=CohortStatus.RUNNING)
    klass = Class.objects.create(cohort=cohort, name="Cls", slug="cls-s", status=PublishStatus.PUBLISHED)
    Enrollment.objects.create(user=student, class_ref=klass, cohort=cohort, status=EnrollmentStatus.ACTIVE)
    Subject.objects.create(title="UniqueSubjectXYZ", slug="unique-subject-xyz", status=SubjectStatus.PUBLISHED)

    auth(api, admin)
    ann = api.post(
        "/api/v1/announcements",
        {
            "scope_type": "class",
            "scope_id": str(klass.id),
            "title": "Welcome week",
            "body_json": {"html": "<p>Hello</p>"},
            "send_email": False,
        },
        format="json",
    )
    assert ann.status_code == 201, ann.data

    overview = api.get("/api/v1/analytics/overview")
    assert overview.status_code == 200
    assert "active_enrollments" in overview.data

    search = api.get("/api/v1/search?q=UniqueSubject")
    assert search.status_code == 200
    assert any(r["type"] == "subject" for r in search.data["results"])

    oidc = api.get("/api/v1/public/oidc/config")
    assert oidc.status_code == 200
    assert oidc.data["enabled"] is False

    auth(api, student)
    notes = api.get("/api/v1/me/notifications")
    assert notes.status_code == 200
    assert any(n["title"] == "Welcome week" for n in notes.data)
