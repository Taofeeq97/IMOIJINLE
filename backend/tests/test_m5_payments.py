import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.payments.fees import generate_invoices_for_enrollment
from apps.payments.models import FeeItem, FeeRule, Payment
from apps.programs.models import Class, Cohort, CohortStatus, Program, PublishStatus


@pytest.fixture
def api():
    return APIClient()


def auth(api, user):
    r = api.post(
        "/api/v1/auth/login", {"email": user.email, "password": "DemoPass123!"}, format="json"
    )
    assert r.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")


@pytest.fixture
def finance_user(db):
    u = User.objects.create_user(email="fin@test.local", password="DemoPass123!", is_staff=True)
    assign_role(user=u, role=Role.FINANCE_ADMIN)
    assign_role(user=u, role=Role.SUPER_ADMIN)  # ensure manage in case of perm gaps
    return u


@pytest.fixture
def student(db):
    u = User.objects.create_user(email="paystudent@test.local", password="DemoPass123!")
    assign_role(user=u, role=Role.STUDENT)
    return u


@pytest.fixture
def setup(db, student):
    program = Program.objects.create(title="P", slug="p-pay", status=PublishStatus.PUBLISHED)
    cohort = Cohort.objects.create(
        program=program, name="C", slug="c-pay", status=CohortStatus.RUNNING, capacity=40
    )
    klass = Class.objects.create(
        cohort=cohort, name="Foundation", slug="foundation-pay", status=PublishStatus.PUBLISHED
    )
    Enrollment.objects.create(
        user=student, class_ref=klass, cohort=cohort, status=EnrollmentStatus.ACTIVE
    )
    return {"klass": klass, "cohort": cohort, "student": student}


@pytest.mark.django_db
def test_custom_charge_pay_settle_and_finance(api, finance_user, setup, stub_paystack):
    student = setup["student"]
    klass = setup["klass"]
    auth(api, finance_user)

    preview = api.post(
        "/api/v1/custom-charges/?preview=1",
        {
            "title": "Lab materials",
            "amount_minor": 250000,
            "target_type": "class",
            "target_ids": [str(klass.id)],
            "gate_rule": {"block": "class_access"},
        },
        format="json",
    )
    assert preview.status_code == 200, preview.data
    assert preview.data["recipient_count"] >= 1

    created = api.post(
        "/api/v1/custom-charges/",
        {
            "title": "Lab materials",
            "amount_minor": 250000,
            "target_type": "class",
            "target_ids": [str(klass.id)],
            "gate_rule": {"block": "class_access"},
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.data["invoice_count"] >= 1
    inv_id = (
        created.data["invoices"][0]["id"]
        if "invoices" in created.data
        else created.data.get("invoice_ids", [None])[0]
    )
    if not inv_id:
        from apps.payments.models import Invoice

        inv_id = str(Invoice.objects.filter(user=student).latest("created_at").id)

    auth(api, student)
    access = api.get(f"/api/v1/access/explain?class_id={klass.id}")
    assert access.status_code == 200
    assert access.data["class"]["allowed"] is False

    pay = api.post(f"/api/v1/invoices/{inv_id}/pay/", {}, format="json")
    assert pay.status_code == 200, pay.data
    ref = pay.data["reference"]

    status = api.get(f"/api/v1/payments/{ref}/status")
    assert status.status_code == 200
    assert status.data["status"] == "success"

    access2 = api.get(f"/api/v1/access/explain?class_id={klass.id}")
    assert access2.data["class"]["allowed"] is True

    auth(api, finance_user)
    overview = api.get("/api/v1/finance/overview")
    assert overview.status_code == 200
    assert overview.data["collected_minor"] >= 250000

    payment = Payment.objects.get(reference=ref)
    refund = api.post(
        "/api/v1/refunds/",
        {"payment_id": str(payment.id), "reason": "test"},
        format="json",
    )
    assert refund.status_code in (200, 201), refund.data


@pytest.mark.django_db
def test_fee_rule_installments(api, finance_user, setup):
    item = FeeItem.objects.create(
        name="Tuition", code="tuition-test", kind="tuition", amount_minor=100000
    )
    FeeRule.objects.create(
        fee_item=item,
        scope_type="class",
        scope_id=setup["klass"].id,
        billing="installments",
        plan={"installments": [{"pct": 50, "days": 0}, {"pct": 50, "days": 30}]},
        gate_rule={"block": "class"},
        active=True,
    )
    enr = Enrollment.objects.get(user=setup["student"], class_ref=setup["klass"])
    invoices = generate_invoices_for_enrollment(enrollment=enr)
    assert len(invoices) == 1
    assert invoices[0].lines.count() == 2
    assert invoices[0].amount_minor == 100000
