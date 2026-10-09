import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Application, ApplicationStatus, Enrollment
from apps.admissions.services import verify_onboarding_token
from apps.orgsettings.models import ApplicationFeeSettings, PaymentGatewaySettings
from apps.orgsettings.payment_services import encrypt_secret
from apps.programs.models import Class, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_user(email="admin@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=u, role=Role.PROGRAM_ADMIN)
    return u


@pytest.fixture
def open_cohort(db):
    program = Program.objects.create(title="Track", slug="track", status="published")
    cohort = Cohort.objects.create(
        program=program,
        name="Intake",
        slug="intake-a",
        status=CohortStatus.APPLICATIONS_OPEN,
        capacity=40,
        application_fee_kobo=500000,
    )
    Class.objects.create(
        cohort=cohort,
        name="Foundation",
        slug="foundation",
        status=PublishStatus.PUBLISHED,
        order=0,
    )
    fees = ApplicationFeeSettings.get_solo()
    fees.default_amount_kobo = 500000
    fees.is_free = False
    fees.fee_required_before_admit = True
    fees.save()
    gw = PaymentGatewaySettings.get_solo()
    gw.public_key = "pk_test_fixture"
    gw.secret_key_encrypted = encrypt_secret("sk_test_fixture")
    gw.save()
    return cohort


def auth(api: APIClient, user: User) -> str:
    r = api.post(
        "/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json"
    )
    assert r.status_code == 200
    token = r.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.mark.django_db
def test_apply_onboard_pay_admit_flow(api, admin_user, open_cohort, stub_paystack):
    mail.outbox.clear()
    pub = api.get(f"/api/v1/public/cohorts/{open_cohort.slug}/")
    assert pub.status_code == 200
    assert pub.data["application_fee_kobo"] == 500000

    apply = api.post(
        f"/api/v1/public/applications/{open_cohort.slug}/",
        {"full_name": "Ada Lovelace", "email": "ada@example.com", "phone": "0801"},
        format="json",
    )
    assert apply.status_code == 201, apply.data
    app_id = apply.data["application_id"]
    application = Application.objects.get(id=app_id)
    assert application.status == ApplicationStatus.ACCOUNT_PENDING
    assert application.fee_invoice_id
    assert len(mail.outbox) >= 1

    # Extract token from email body
    body = mail.outbox[-1].body
    assert "token=" in body
    token = body.split("token=")[1].split("&")[0]
    verify_onboarding_token(token=token, application_id=app_id)

    set_pw = api.post(
        "/api/v1/auth/onboarding/set-password",
        {"token": token, "application_id": app_id, "password": "SecurePass99!"},
        format="json",
    )
    assert set_pw.status_code == 200, set_pw.data
    access = set_pw.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    application.refresh_from_db()
    assert application.status == ApplicationStatus.FEE_PENDING

    pay = api.post(
        f"/api/v1/portal/applications/{app_id}/pay",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="idem-1",
    )
    assert pay.status_code == 200, pay.data
    reference = pay.data["reference"]

    confirm = api.get(f"/api/v1/payments/{reference}/status")
    assert confirm.status_code == 200, confirm.data
    assert confirm.data["status"] == "success"

    application.refresh_from_db()
    assert application.status == ApplicationStatus.UNDER_REVIEW
    assert application.fee_paid_at is not None

    auth(api, admin_user)
    klass = Class.objects.get(cohort=open_cohort, slug="foundation")
    admit = api.post(
        f"/api/v1/applications/{app_id}/admit",
        {"class_ids": [str(klass.id)], "fee_handling": "generate"},
        format="json",
    )
    assert admit.status_code == 200, admit.data
    assert admit.data["status"] == "admitted"

    applicant = User.objects.get(email="ada@example.com")
    r = api.post(
        "/api/v1/auth/login",
        {"email": applicant.email, "password": "SecurePass99!"},
        format="json",
    )
    assert r.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    learning = api.get("/api/v1/me/learning")
    assert learning.status_code == 200
    assert len(learning.data["classes"]) == 1
    assert learning.data["classes"][0]["class_name"] == "Foundation"
    assert Enrollment.objects.filter(user=applicant, class_ref=klass).exists()


@pytest.mark.django_db
def test_cannot_admit_before_fee_when_required(api, admin_user, open_cohort):
    apply = api.post(
        f"/api/v1/public/applications/{open_cohort.slug}/",
        {"full_name": "Bob", "email": "bob@example.com"},
        format="json",
    )
    app_id = apply.data["application_id"]
    body = mail.outbox[-1].body
    token = body.split("token=")[1].split("&")[0]
    api.post(
        "/api/v1/auth/onboarding/set-password",
        {"token": token, "application_id": app_id, "password": "SecurePass99!"},
        format="json",
    )

    auth(api, admin_user)
    klass = Class.objects.get(cohort=open_cohort, slug="foundation")
    admit = api.post(
        f"/api/v1/applications/{app_id}/admit",
        {"class_ids": [str(klass.id)]},
        format="json",
    )
    assert admit.status_code == 400
    assert admit.data["code"] == "fee_required"


@pytest.mark.django_db
def test_closed_cohort_rejects_apply(api, open_cohort):
    open_cohort.status = CohortStatus.APPLICATIONS_CLOSED
    open_cohort.save()
    r = api.post(
        f"/api/v1/public/applications/{open_cohort.slug}/",
        {"full_name": "Cara", "email": "cara@example.com"},
        format="json",
    )
    assert r.status_code == 400
    assert r.data["code"] == "closed"


@pytest.mark.django_db
def test_onboarding_token_single_use(api, open_cohort):
    apply = api.post(
        f"/api/v1/public/applications/{open_cohort.slug}/",
        {"full_name": "Dan", "email": "dan@example.com"},
        format="json",
    )
    app_id = apply.data["application_id"]
    token = mail.outbox[-1].body.split("token=")[1].split("&")[0]
    first = api.post(
        "/api/v1/auth/onboarding/set-password",
        {"token": token, "application_id": app_id, "password": "SecurePass99!"},
        format="json",
    )
    assert first.status_code == 200
    second = api.post(
        "/api/v1/auth/onboarding/set-password",
        {"token": token, "application_id": app_id, "password": "SecurePass99!"},
        format="json",
    )
    assert second.status_code == 400
