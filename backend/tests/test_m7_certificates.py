import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.certificates.services import default_design
from apps.programs.models import Class, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


def auth(api, user):
    r = api.post("/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json")
    assert r.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


@pytest.mark.django_db
def test_certificate_preview_issue_verify_revoke(api, db):
    admin = User.objects.create_user(email="certadmin@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=admin, role=Role.PROGRAM_ADMIN)
    student = User.objects.create_user(
        email="certstudent@test.local", password="DemoPass123!", first_name="Ada", last_name="Lovelace"
    )
    assign_role(user=student, role=Role.STUDENT)
    program = Program.objects.create(title="Spirit", slug="spirit-c", status=PublishStatus.PUBLISHED)
    cohort = Cohort.objects.create(program=program, name="Jan", slug="jan-c", status=CohortStatus.RUNNING)
    klass = Class.objects.create(cohort=cohort, name="Foundation", slug="f-c", status=PublishStatus.PUBLISHED)
    enr = Enrollment.objects.create(
        user=student, class_ref=klass, cohort=cohort, status=EnrollmentStatus.ACTIVE
    )

    auth(api, admin)
    tmpl = api.post(
        "/api/v1/certificate-templates",
        {"name": "Completion", "design": default_design()},
        format="json",
    )
    assert tmpl.status_code == 201, tmpl.data
    tid = tmpl.data["id"]

    preview = api.post(
        f"/api/v1/certificate-templates/{tid}/preview",
        {"enrollment_id": str(enr.id), "data_source": "enrollment"},
        format="json",
    )
    assert preview.status_code == 200, preview.data
    assert "Ada" in preview.data["html"]

    pub = api.post(f"/api/v1/certificate-templates/{tid}/publish", {}, format="json")
    assert pub.status_code == 200, pub.data

    issued = api.post(
        "/api/v1/certificates/issue",
        {"enrollment_id": str(enr.id), "template_id": tid, "force": True},
        format="json",
    )
    assert issued.status_code == 201, issued.data
    code = issued.data["code"] if isinstance(issued.data, dict) and "code" in issued.data else issued.data[0]["code"]

    verify = api.get(f"/api/v1/public/certificates/verify/{code}")
    assert verify.status_code == 200
    assert verify.data["status"] in ("issued", "valid")

    auth(api, student)
    mine = api.get("/api/v1/me/certificates")
    assert mine.status_code == 200
    assert len(mine.data) >= 1

    auth(api, admin)
    cid = issued.data["id"] if "id" in issued.data else issued.data[0]["id"]
    rev = api.post(f"/api/v1/certificates/{cid}/revoke", {"reason": "error"}, format="json")
    assert rev.status_code == 200
    verify2 = api.get(f"/api/v1/public/certificates/verify/{code}")
    assert verify2.data["status"] in ("revoked", "invalid")
