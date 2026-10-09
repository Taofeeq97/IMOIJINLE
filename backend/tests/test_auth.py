import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role, can
from apps.audit.models import AuditLog


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user(db):
    u = User.objects.create_user(
        email="student@test.local",
        password="DemoPass123!",
        first_name="Stu",
        last_name="Dent",
    )
    assign_role(user=u, role=Role.STUDENT)
    return u


@pytest.mark.django_db
def test_health(api):
    r = api.get("/api/v1/health/")
    assert r.status_code == 200
    assert r.data["status"] == "ok"


@pytest.mark.django_db
def test_register_and_me(api):
    r = api.post(
        "/api/v1/auth/register",
        {"email": "new@test.local", "password": "DemoPass123!", "first_name": "New"},
        format="json",
    )
    assert r.status_code == 201
    assert "access" in r.data
    assert r.data["user"]["email"] == "new@test.local"
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me = api.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert "apply" in me.data["permissions"]


@pytest.mark.django_db
def test_login_happy_path(api, user):
    r = api.post(
        "/api/v1/auth/login",
        {"email": "student@test.local", "password": "DemoPass123!"},
        format="json",
    )
    assert r.status_code == 200
    assert "access" in r.data
    assert r.cookies.get("refresh_token") is not None
    assert AuditLog.objects.filter(action="auth.login").exists()


@pytest.mark.django_db
def test_me_requires_auth(api):
    r = api.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.django_db
def test_register_validation(api):
    r = api.post(
        "/api/v1/auth/register",
        {"email": "bad", "password": "short"},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_role_assignment_audited(user):
    assert AuditLog.objects.filter(action="role.assign").exists()


@pytest.mark.django_db
def test_policy_deny_by_default(user):
    assert can(user, "settings.manage") is False
    assert can(user, "learn") is True


@pytest.mark.django_db
def test_refresh_rotation(api, user):
    login = api.post(
        "/api/v1/auth/login",
        {"email": "student@test.local", "password": "DemoPass123!"},
        format="json",
    )
    assert login.status_code == 200
    refresh = login.cookies["refresh_token"].value
    api.cookies["refresh_token"] = refresh
    r = api.post("/api/v1/auth/refresh", {}, format="json")
    assert r.status_code == 200
    assert "access" in r.data
    # old refresh blacklisted
    api.cookies["refresh_token"] = refresh
    r2 = api.post("/api/v1/auth/refresh", {}, format="json")
    assert r2.status_code == 401


@pytest.mark.django_db
def test_brand_public(api):
    r = api.get("/api/v1/settings/brand/")
    assert r.status_code == 200
    assert "primary_color" in r.data


@pytest.mark.django_db
def test_google_not_configured(api):
    r = api.post("/api/v1/auth/google", {"id_token": "x"}, format="json")
    assert r.status_code == 501
