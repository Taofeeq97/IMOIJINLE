import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.audit.models import AuditLog
from apps.courses.models import Subject, Topic
from apps.orgsettings.models import PaymentGatewaySettings
from apps.orgsettings.payment_services import encrypt_secret, gateway_public_payload


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(
        email="admin@test.local",
        password="DemoPass123!",
        is_staff=True,
    )
    assign_role(user=u, role=Role.PROGRAM_ADMIN)
    return u


@pytest.fixture
def student_user(db):
    u = User.objects.create_user(email="stu@test.local", password="DemoPass123!")
    assign_role(user=u, role=Role.STUDENT)
    return u


@pytest.fixture
def finance_user(db):
    u = User.objects.create_user(email="fin@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=u, role=Role.FINANCE_ADMIN)
    return u


def auth(api: APIClient, user: User) -> str:
    r = api.post("/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json")
    assert r.status_code == 200
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.mark.django_db
def test_admin_can_create_hierarchy(api, admin_user):
    auth(api, admin_user)
    # Cohort is the root (academic session) — no Program parent required
    cohort = api.post(
        "/api/v1/cohorts/",
        {"name": "2026/2027 Academic Session", "capacity": 40},
        format="json",
    )
    assert cohort.status_code == 201
    assert cohort.data.get("program") in (None, "")
    klass = api.post(
        "/api/v1/classes/",
        {"name": "Foundation", "cohort": cohort.data["id"]},
        format="json",
    )
    assert klass.status_code == 201, klass.data
    subject = api.post(
        "/api/v1/subjects/",
        {"title": "Intro Subject", "level": "beginner"},
        format="json",
    )
    assert subject.status_code == 201
    topic = api.post(
        f"/api/v1/subjects/{subject.data['id']}/topics/",
        {"title": "Week 1", "objective_text": "Start"},
        format="json",
    )
    assert topic.status_code == 201
    sub = api.post(
        f"/api/v1/topics/{topic.data['id']}/subtopics/",
        {"title": "Lesson 1", "kind": "subtopic", "min_time_s": 60},
        format="json",
    )
    assert sub.status_code == 201
    attach = api.post(
        f"/api/v1/classes/{klass.data['id']}/subjects/",
        {"subject_id": subject.data["id"], "mode": "linked"},
        format="json",
    )
    assert attach.status_code == 201
    opened = api.post(f"/api/v1/cohorts/{cohort.data['id']}/open-applications/", {}, format="json")
    assert opened.status_code == 200
    assert opened.data["status"] == "applications_open"


@pytest.mark.django_db
def test_student_cannot_create_cohort(api, student_user):
    auth(api, student_user)
    r = api.post("/api/v1/cohorts/", {"name": "Nope"}, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_finance_can_update_payment_settings_not_cohorts(api, finance_user):
    auth(api, finance_user)
    denied = api.post("/api/v1/cohorts/", {"name": "Finance Cohort"}, format="json")
    assert denied.status_code == 403
    gw = api.get("/api/v1/settings/payments/gateway")
    assert gw.status_code == 200
    assert "secret_key" not in gw.data
    assert "secret_key_encrypted" not in gw.data
    put = api.put(
        "/api/v1/settings/payments/gateway",
        {"mode": "test", "public_key": "pk_test_abc12345", "secret_key": "sk_test_secretvalue"},
        format="json",
    )
    assert put.status_code == 200
    assert put.data["public_key_set"] is True
    assert put.data["secret_key_set"] is True
    assert "sk_test" not in str(put.data)
    assert AuditLog.objects.filter(action="settings.payments.gateway.update").exists()


@pytest.mark.django_db
def test_application_fee_kobo(api, admin_user):
    auth(api, admin_user)
    r = api.put(
        "/api/v1/settings/payments/application-fees",
        {"default_amount_naira": 7500, "fee_required_before_admit": True},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["default_amount_kobo"] == 750000
    assert r.data["is_free"] is False


@pytest.mark.django_db
def test_secret_never_leaked_in_gateway_payload(db):
    obj = PaymentGatewaySettings.get_solo()
    obj.public_key = "pk_test_abcdefgh"
    obj.secret_key_encrypted = encrypt_secret("sk_live_supersecret")
    obj.save()
    payload = gateway_public_payload(obj)
    assert "supersecret" not in str(payload)
    assert payload["secret_key_set"] is True


@pytest.mark.django_db
def test_publish_subject_requires_topic(api, admin_user):
    auth(api, admin_user)
    subject = api.post("/api/v1/subjects/", {"title": "Empty"}, format="json")
    r = api.post(f"/api/v1/subjects/{subject.data['id']}/publish/", {}, format="json")
    assert r.status_code == 400
    topic = api.post(f"/api/v1/subjects/{subject.data['id']}/topics/", {"title": "T1"}, format="json")
    assert topic.status_code == 201
    # Still incomplete without a subtopic (M3 publish checklist)
    r_mid = api.post(f"/api/v1/subjects/{subject.data['id']}/publish/", {}, format="json")
    assert r_mid.status_code == 400
    api.post(
        f"/api/v1/topics/{topic.data['id']}/subtopics/",
        {"title": "S1", "kind": "subtopic"},
        format="json",
    )
    r2 = api.post(f"/api/v1/subjects/{subject.data['id']}/publish/", {}, format="json")
    assert r2.status_code == 200
    assert r2.data["status"] == "published"


@pytest.mark.django_db
def test_reorder_topics(api, admin_user):
    auth(api, admin_user)
    subject = Subject.objects.create(title="Reorder Me", slug="reorder-me")
    t1 = Topic.objects.create(subject=subject, title="A", order=0)
    t2 = Topic.objects.create(subject=subject, title="B", order=1)
    r = api.post(
        f"/api/v1/subjects/{subject.id}/topics/reorder/",
        {"ordered_ids": [str(t2.id), str(t1.id)]},
        format="json",
    )
    assert r.status_code == 200
    t1.refresh_from_db()
    t2.refresh_from_db()
    assert t2.order == 0
    assert t1.order == 1
