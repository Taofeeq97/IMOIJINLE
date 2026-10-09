from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.services import log_audit
from apps.integrations import paystack as paystack_client
from apps.integrations.paystack import PaystackError
from apps.orgsettings.models import PaymentGatewaySettings
from apps.orgsettings.payment_services import decrypt_secret
from apps.payments.models import (
    AccessOverride,
    CustomCharge,
    CustomChargeTarget,
    FeeBilling,
    FeeItem,
    FeeMode,
    FeeRule,
    FeeScopeType,
    Invoice,
    InvoiceKind,
    InvoiceLine,
    InvoiceSource,
    InvoiceStatus,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentStatus,
    PaystackWebhookEvent,
    Refund,
    RefundStatus,
)

logger = logging.getLogger(__name__)

SCOPE_PRECEDENCE = {
    FeeScopeType.USER: 60,
    FeeScopeType.SUBJECT: 50,
    FeeScopeType.CLASS: 40,
    FeeScopeType.COHORT: 30,
    FeeScopeType.PROGRAM: 20,
    FeeScopeType.ALL: 10,
}


class PaymentError(Exception):
    def __init__(self, message: str, code: str = "payment_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _secret_key() -> str:
    gw = PaymentGatewaySettings.get_solo()
    secret = decrypt_secret(gw.secret_key_encrypted)
    if not secret:
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
    if not secret:
        raise PaymentError(
            "Paystack is not configured. Set gateway secret in Payment Configuration or PAYSTACK_SECRET_KEY.",
            code="paystack_unconfigured",
        )
    return secret


def _public_key() -> str:
    gw = PaymentGatewaySettings.get_solo()
    key = gw.public_key or getattr(settings, "PAYSTACK_PUBLIC_KEY", "") or ""
    if not key:
        raise PaymentError(
            "Paystack public key is not configured.",
            code="paystack_unconfigured",
        )
    return key


def verify_paystack_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    digest = hmac.new(_secret_key().encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


def _paystack_request(method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
    try:
        return paystack_client.request(method, path, payload, secret=_secret_key())
    except PaystackError as exc:
        raise PaymentError(exc.message, code=exc.code) from exc


def _next_invoice_number() -> str:
    year = timezone.now().year
    prefix = f"IMO-{year}-"
    last = (
        Invoice.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(str(last).rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = Invoice.objects.filter(number__startswith=prefix).count() + 1
    return f"{prefix}{seq:06d}"


def create_application_invoice(
    *, user, amount_kobo: int, application_id: str, currency: str = "NGN"
) -> Invoice:
    return Invoice.objects.create(
        user=user,
        number=_next_invoice_number(),
        kind=InvoiceKind.APPLICATION,
        status=InvoiceStatus.OPEN,
        currency=currency,
        amount_minor=amount_kobo,
        description="Application fee",
        source=InvoiceSource.APPLICATION,
        metadata={"application_id": str(application_id)},
    )


def _rule_matches_enrollment(rule: FeeRule, enrollment) -> bool:
    if not rule.active:
        return False
    now = timezone.now()
    if rule.starts_at and rule.starts_at > now:
        return False
    if rule.ends_at and rule.ends_at < now:
        return False

    class_obj = enrollment.class_ref
    cohort = enrollment.cohort
    program_id = getattr(cohort, "program_id", None)
    user_id = enrollment.user_id

    st = rule.scope_type
    sid = rule.scope_id
    if st == FeeScopeType.ALL:
        return True
    if st == FeeScopeType.PROGRAM:
        return sid is not None and program_id is not None and str(sid) == str(program_id)
    if st == FeeScopeType.COHORT:
        return sid is not None and str(sid) == str(cohort.id)
    if st == FeeScopeType.CLASS:
        return sid is not None and str(sid) == str(class_obj.id)
    if st == FeeScopeType.SUBJECT:
        from apps.programs.models import ClassSubject

        if sid is None:
            return False
        return ClassSubject.objects.filter(class_ref=class_obj, subject_id=sid).exists()
    if st == FeeScopeType.USER:
        return sid is not None and str(sid) == str(user_id)
    return False


def resolve_fees_for_enrollment(enrollment) -> list[FeeRule]:
    """Return matching fee rules with narrower scope winning; exclusive stops fall-through."""
    candidates = [
        r
        for r in FeeRule.objects.select_related("fee_item").filter(
            active=True, fee_item__active=True
        )
        if _rule_matches_enrollment(r, enrollment)
    ]
    candidates.sort(
        key=lambda r: (SCOPE_PRECEDENCE.get(r.scope_type, 0), r.priority),
        reverse=True,
    )
    selected: list[FeeRule] = []
    for rule in candidates:
        if rule.mode != FeeMode.MANDATORY and not selected:
            # Still include mandatory only for admit generation; optional skipped unless alone
            pass
        if rule.mode != FeeMode.MANDATORY:
            continue
        selected.append(rule)
        if rule.exclusive:
            break
    # Deduplicate by fee_item keeping highest precedence
    by_item: dict[str, FeeRule] = {}
    for rule in selected:
        key = str(rule.fee_item_id)
        if key not in by_item:
            by_item[key] = rule
    return list(by_item.values())


def _parse_relative_due(expr: str | None, *, base_at=None):
    if not expr:
        return None
    base = base_at or timezone.now()
    expr = str(expr).strip().lower()
    if expr in {"on_admission", "immediate", "now"}:
        return base
    if expr.startswith("+") and expr.endswith("d"):
        try:
            days = int(expr[1:-1])
            return base + timedelta(days=days)
        except ValueError:
            return None
    return None


def generate_installment_lines(
    *,
    invoice: Invoice,
    fee_item: FeeItem | None,
    plan: dict,
    amount_minor: int,
    description: str = "",
) -> list[InvoiceLine]:
    """Create InvoiceLine rows from plan JSON. Uses largest-remainder for pct splits."""
    installments = plan.get("installments") or []
    lines: list[InvoiceLine] = []
    if not installments:
        count = int(plan.get("count") or 0)
        if count <= 0:
            lines.append(
                InvoiceLine.objects.create(
                    invoice=invoice,
                    fee_item=fee_item,
                    description=description or invoice.description,
                    amount_minor=amount_minor,
                    installment_no=1,
                    due_at=invoice.due_at,
                )
            )
            return lines
        base = amount_minor // count
        rem = amount_minor - base * count
        amounts = [base + (1 if i < rem else 0) for i in range(count)]
        interval = (plan.get("interval") or "monthly").lower()
        first_due = (
            _parse_relative_due(plan.get("first_due"), base_at=timezone.now()) or timezone.now()
        )
        for i, amt in enumerate(amounts, start=1):
            due = first_due
            if interval == "monthly" and i > 1:
                due = first_due + timedelta(days=30 * (i - 1))
            lines.append(
                InvoiceLine.objects.create(
                    invoice=invoice,
                    fee_item=fee_item,
                    description=f"{description or invoice.description} — installment {i}/{count}",
                    amount_minor=amt,
                    installment_no=i,
                    due_at=due,
                )
            )
        return lines

    # Percent-based installments with largest-remainder
    raw = []
    for item in installments:
        pct = float(item.get("pct") or 0)
        raw.append(pct)
    total_pct = sum(raw) or 100.0
    exact = [amount_minor * (p / total_pct) for p in raw]
    floors = [int(x) for x in exact]
    rem = amount_minor - sum(floors)
    order = sorted(range(len(floors)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in order[:rem]:
        floors[i] += 1

    for idx, item in enumerate(installments):
        due = _parse_relative_due(item.get("due"), base_at=timezone.now())
        lines.append(
            InvoiceLine.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=f"{description or invoice.description} — installment {idx + 1}",
                amount_minor=floors[idx],
                installment_no=idx + 1,
                due_at=due,
            )
        )
    return lines


@transaction.atomic
def apply_fee_rules_on_admit(*, enrollment, actor=None, request=None) -> list[Invoice]:
    """Create invoices for mandatory fee rules matching the enrollment."""
    rules = resolve_fees_for_enrollment(enrollment)
    invoices: list[Invoice] = []
    for rule in rules:
        existing = Invoice.objects.filter(
            user=enrollment.user,
            enrollment=enrollment,
            fee_rule=rule,
            status__in=[InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID],
        ).first()
        if existing:
            continue
        fee_item = rule.fee_item
        kind = InvoiceKind.CLASS
        if rule.scope_type == FeeScopeType.SUBJECT:
            kind = InvoiceKind.SUBJECT
        invoice = Invoice.objects.create(
            user=enrollment.user,
            number=_next_invoice_number(),
            kind=kind,
            status=InvoiceStatus.OPEN,
            currency=fee_item.currency,
            amount_minor=fee_item.amount_minor,
            description=fee_item.name,
            source=InvoiceSource.RULE,
            enrollment=enrollment,
            fee_rule=rule,
            fee_item=fee_item,
            gate_rule=rule.gate_rule or {},
            metadata={
                "class_id": str(enrollment.class_ref_id),
                "cohort_id": str(enrollment.cohort_id),
                "scope_type": rule.scope_type,
                "scope_id": str(rule.scope_id) if rule.scope_id else None,
            },
            due_at=_parse_relative_due((rule.due_rule or {}).get("due"), base_at=timezone.now()),
        )
        if rule.billing == FeeBilling.INSTALLMENTS and rule.plan:
            generate_installment_lines(
                invoice=invoice,
                fee_item=fee_item,
                plan=rule.plan,
                amount_minor=fee_item.amount_minor,
                description=fee_item.name,
            )
        else:
            InvoiceLine.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=fee_item.name,
                amount_minor=fee_item.amount_minor,
                installment_no=1,
                due_at=invoice.due_at,
            )
        invoices.append(invoice)
        log_audit(
            actor=actor,
            action="invoice.from_fee_rule",
            obj=invoice,
            after={"fee_rule_id": str(rule.id), "amount_minor": invoice.amount_minor},
            request=request,
        )
    return invoices


def resolve_custom_charge_recipients(
    charge: CustomCharge | None = None, *, target_type: str = "", target_ids: list | None = None
) -> list:
    """Return distinct User instances who would receive invoices."""
    from apps.accounts.models import User
    from apps.admissions.models import Enrollment

    ttype = target_type or (charge.target_type if charge else "")
    tids = [
        str(x)
        for x in (target_ids if target_ids is not None else (charge.target_ids if charge else []))
    ]
    user_ids: set = set()

    if ttype == CustomChargeTarget.USER:
        user_ids.update(tids)
    elif ttype == CustomChargeTarget.CLASS:
        user_ids.update(
            str(uid)
            for uid in Enrollment.objects.filter(class_ref_id__in=tids).values_list(
                "user_id", flat=True
            )
        )
    elif ttype == CustomChargeTarget.COHORT:
        user_ids.update(
            str(uid)
            for uid in Enrollment.objects.filter(cohort_id__in=tids).values_list(
                "user_id", flat=True
            )
        )
    elif ttype == CustomChargeTarget.ENROLLMENTS:
        user_ids.update(
            str(uid)
            for uid in Enrollment.objects.filter(id__in=tids).values_list("user_id", flat=True)
        )

    users = list(User.objects.filter(id__in=user_ids))
    return users


def preview_custom_charge(*, target_type: str, target_ids: list, amount_minor: int) -> dict:
    recipients = resolve_custom_charge_recipients(target_type=target_type, target_ids=target_ids)
    return {
        "recipient_count": len(recipients),
        "total_minor": len(recipients) * int(amount_minor),
        "recipient_ids": [str(u.id) for u in recipients],
    }


@transaction.atomic
def create_custom_charge(
    *,
    title: str,
    amount_minor: int,
    target_type: str,
    target_ids: list,
    description: str = "",
    currency: str = "NGN",
    mandatory: bool = True,
    due_at=None,
    gate_rule: dict | None = None,
    created_by=None,
    notify: bool = True,
    fee_item: FeeItem | None = None,
    request=None,
) -> tuple[CustomCharge, list[Invoice]]:
    charge = CustomCharge.objects.create(
        title=title,
        description=description,
        amount_minor=amount_minor,
        currency=currency,
        target_type=target_type,
        target_ids=[str(x) for x in target_ids],
        mandatory=mandatory,
        due_at=due_at,
        gate_rule=gate_rule or {},
        created_by=created_by,
        notify=notify,
        fee_item=fee_item,
    )
    recipients = resolve_custom_charge_recipients(charge)
    invoices: list[Invoice] = []
    for user in recipients:
        invoice = Invoice.objects.create(
            user=user,
            number=_next_invoice_number(),
            kind=InvoiceKind.CUSTOM,
            status=InvoiceStatus.OPEN,
            currency=currency,
            amount_minor=amount_minor,
            description=title,
            source=InvoiceSource.CUSTOM,
            custom_charge=charge,
            fee_item=fee_item,
            gate_rule=gate_rule or {},
            due_at=due_at,
            metadata={"custom_charge_id": str(charge.id), "target_type": target_type},
        )
        InvoiceLine.objects.create(
            invoice=invoice,
            fee_item=fee_item,
            description=title,
            amount_minor=amount_minor,
            installment_no=1,
            due_at=due_at,
        )
        invoices.append(invoice)
    log_audit(
        actor=created_by,
        action="custom_charge.create",
        obj=charge,
        after={"recipients": len(invoices), "amount_minor": amount_minor},
        request=request,
    )
    return charge, invoices


def _blocking_invoices_for(*, user, class_id=None, subject_id=None) -> list[Invoice]:
    qs = Invoice.objects.filter(
        user=user,
        status__in=[InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID],
    )
    blocking = []
    for inv in qs:
        rule = inv.gate_rule or {}
        if not rule:
            continue
        block = str(rule.get("block") or "none")
        if block in {"", "none"}:
            continue
        grace = int(rule.get("grace_days") or 0)
        if inv.due_at and grace:
            if timezone.now() < inv.due_at + timedelta(days=grace):
                continue
        if block.startswith("class:") and class_id:
            if str(block.split(":", 1)[1]) == str(class_id):
                blocking.append(inv)
            continue
        if block.startswith("subject:") and subject_id:
            if str(block.split(":", 1)[1]) == str(subject_id):
                blocking.append(inv)
            continue
        if block in {"class_access", "cohort_access"} and class_id:
            meta_class = (inv.metadata or {}).get("class_id")
            if meta_class and str(meta_class) != str(class_id):
                continue
            blocking.append(inv)
            continue
        if block == "subject_access" and subject_id:
            meta_subj = (inv.metadata or {}).get("subject_id")
            if meta_subj and str(meta_subj) != str(subject_id):
                continue
            blocking.append(inv)
            continue
    return blocking


def _has_active_override(*, user, class_id=None, subject_id=None) -> bool:
    now = timezone.now()
    qs = AccessOverride.objects.filter(user=user, active=True)
    qs = qs.filter(Q(until__isnull=True) | Q(until__gte=now))
    if class_id and qs.filter(scope_type="class", scope_id=class_id).exists():
        return True
    if subject_id and qs.filter(scope_type="subject", scope_id=subject_id).exists():
        return True
    return False


def can_access_class(*, user, class_id) -> dict:
    if _has_active_override(user=user, class_id=class_id):
        return {"allowed": True, "reason": "override", "blocking_invoice_ids": []}
    blocking = _blocking_invoices_for(user=user, class_id=class_id)
    if blocking:
        return {
            "allowed": False,
            "reason": "payment_required",
            "blocking_invoice_ids": [str(i.id) for i in blocking],
        }
    return {"allowed": True, "reason": "ok", "blocking_invoice_ids": []}


def can_access_subject(*, user, subject_id, class_id=None) -> dict:
    if _has_active_override(user=user, subject_id=subject_id, class_id=class_id):
        return {"allowed": True, "reason": "override", "blocking_invoice_ids": []}
    blocking = _blocking_invoices_for(user=user, class_id=class_id, subject_id=subject_id)
    if blocking:
        return {
            "allowed": False,
            "reason": "payment_required",
            "blocking_invoice_ids": [str(i.id) for i in blocking],
        }
    return {"allowed": True, "reason": "ok", "blocking_invoice_ids": []}


def explain_access(*, user, class_id=None, subject_id=None) -> dict:
    result = {"class": None, "subject": None}
    if class_id:
        result["class"] = can_access_class(user=user, class_id=class_id)
    if subject_id:
        result["subject"] = can_access_subject(user=user, subject_id=subject_id, class_id=class_id)
    return result


def invalidate_gates_for_user(user) -> None:
    """Hook for cache invalidation; MVP evaluates gates live so this is a no-op placeholder."""
    return None


@transaction.atomic
def initiate_payment(
    *,
    invoice: Invoice,
    user,
    idempotency_key: str = "",
    callback_url: str | None = None,
    actor=None,
    request=None,
) -> Payment:
    if invoice.user_id != user.id:
        raise PaymentError("Invoice does not belong to user", code="forbidden")
    if invoice.status == InvoiceStatus.PAID:
        raise PaymentError("Invoice already paid", code="already_paid")
    if invoice.balance_minor <= 0:
        raise PaymentError("Nothing to pay", code="zero_balance")

    if idempotency_key:
        existing = Payment.objects.filter(
            invoice=invoice,
            idempotency_key=idempotency_key,
            status__in=["initiated", "pending", "success"],
        ).first()
        if existing:
            return existing

    reference = f"IMO-{uuid.uuid4()}"
    payment = Payment.objects.create(
        invoice=invoice,
        user=user,
        amount_minor=invoice.balance_minor,
        currency=invoice.currency,
        reference=reference,
        status=PaymentStatus.INITIATED,
        idempotency_key=idempotency_key or "",
    )

    attempt_no = PaymentAttempt.objects.filter(invoice=invoice).count() + 1
    attempt = PaymentAttempt.objects.create(
        invoice=invoice,
        payment=payment,
        user=user,
        reference=reference,
        status=PaymentAttemptStatus.INITIATED,
        attempt_no=attempt_no,
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    cb = callback_url or f"{settings.FRONTEND_URL}/payments/callback"
    try:
        result = _paystack_request(
            "POST",
            "/transaction/initialize",
            {
                "email": user.email,
                "amount": payment.amount_minor,
                "currency": payment.currency,
                "reference": reference,
                "callback_url": cb,
                "metadata": {
                    "invoice_id": str(invoice.id),
                    "payment_id": str(payment.id),
                    "application_id": invoice.metadata.get("application_id"),
                },
            },
        )
        data = result.get("data") or {}
        payment.authorization_url = data.get("authorization_url") or ""
        payment.access_code = data.get("access_code") or ""
        payment.status = PaymentStatus.PENDING
        payment.raw = result
        payment.save()
        attempt.authorization_url = payment.authorization_url
        attempt.access_code = payment.access_code
        attempt.status = PaymentAttemptStatus.PENDING
        attempt.save(update_fields=["authorization_url", "access_code", "status", "updated_at"])
    except PaymentError:
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "updated_at"])
        attempt.status = PaymentAttemptStatus.FAILED
        attempt.failure_message = "initialize_failed"
        attempt.save(update_fields=["status", "failure_message", "updated_at"])
        raise

    log_audit(
        actor=actor or user,
        action="payment.initiate",
        obj=payment,
        after={"reference": reference, "amount_minor": payment.amount_minor},
        request=request,
    )
    return payment


@transaction.atomic
def settle_payment(
    *, reference: str, verify_payload: dict | None = None, actor=None, request=None
) -> Payment:
    payment = Payment.objects.select_for_update().select_related("invoice").get(reference=reference)
    if payment.status == PaymentStatus.SUCCESS:
        return payment

    payload = verify_payload
    if payload is None:
        result = _paystack_request("GET", f"/transaction/verify/{reference}")
        payload = result.get("data") or {}

    status = (payload.get("status") or "").lower()
    attempt = PaymentAttempt.objects.filter(reference=reference).order_by("-created_at").first()

    if status != "success":
        payment.status = PaymentStatus.FAILED
        payment.raw = payload
        payment.save()
        if attempt:
            attempt.status = PaymentAttemptStatus.FAILED
            attempt.failure_code = str(payload.get("gateway_response") or "")[:64]
            attempt.failure_message = str(payload.get("gateway_response") or "not_successful")[:255]
            attempt.channel = payload.get("channel") or ""
            attempt.save()
        raise PaymentError("Payment not successful", code="not_successful")

    amount = int(payload.get("amount") or 0)
    currency = (payload.get("currency") or "").upper()
    if amount != payment.amount_minor:
        raise PaymentError("Amount mismatch", code="amount_mismatch")
    if currency and currency != payment.currency.upper():
        raise PaymentError("Currency mismatch", code="currency_mismatch")

    payment.status = PaymentStatus.SUCCESS
    payment.paid_at = timezone.now()
    payment.channel = payload.get("channel") or ""
    payment.paystack_id = str(payload.get("id") or "")
    payment.fees_minor = int(payload.get("fees") or 0)
    payment.raw = payload
    payment.save()

    if attempt:
        elapsed = None
        if attempt.created_at:
            elapsed = int((timezone.now() - attempt.created_at).total_seconds())
        attempt.status = PaymentAttemptStatus.SUCCESS
        attempt.channel = payment.channel
        attempt.time_to_complete_s = elapsed
        attempt.save()

    invoice = payment.invoice
    invoice.amount_paid_minor = min(
        invoice.amount_minor, invoice.amount_paid_minor + payment.amount_minor
    )
    if invoice.amount_paid_minor >= invoice.amount_minor:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = timezone.now()
        # Mark lines paid
        for line in invoice.lines.all():
            line.amount_paid_minor = line.line_total_minor
            line.save(update_fields=["amount_paid_minor", "updated_at"])
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
        remaining = payment.amount_minor
        for line in invoice.lines.order_by("installment_no", "created_at"):
            if remaining <= 0:
                break
            need = line.balance_minor
            if need <= 0:
                continue
            apply = min(need, remaining)
            line.amount_paid_minor += apply
            line.save(update_fields=["amount_paid_minor", "updated_at"])
            remaining -= apply
    invoice.save()

    invalidate_gates_for_user(payment.user)

    log_audit(
        actor=actor,
        action="payment.settle",
        obj=payment,
        after={"reference": reference, "status": "success"},
        request=request,
    )

    from apps.admissions.services import on_application_fee_paid

    app_id = invoice.metadata.get("application_id")
    if app_id:
        on_application_fee_paid(application_id=app_id, payment=payment, request=request)

    return payment


@transaction.atomic
def request_refund(
    *,
    payment: Payment,
    amount_minor: int | None = None,
    reason: str = "",
    requested_by=None,
    request=None,
) -> Refund:
    if payment.status not in {PaymentStatus.SUCCESS, PaymentStatus.PARTIALLY_REFUNDED}:
        raise PaymentError("Only successful payments can be refunded", code="invalid_status")
    refundable = payment.amount_minor - payment.amount_refunded_minor
    amt = int(amount_minor if amount_minor is not None else refundable)
    if amt <= 0 or amt > refundable:
        raise PaymentError("Invalid refund amount", code="invalid_amount")

    refund = Refund.objects.create(
        payment=payment,
        amount_minor=amt,
        reason=reason,
        status=RefundStatus.REQUESTED,
        requested_by=requested_by,
        approved_by=requested_by,
    )

    payload: dict[str, Any] = {"transaction": payment.reference}
    if amt < payment.amount_minor:
        payload["amount"] = amt
    try:
        result = _paystack_request("POST", "/refund", payload)
        data = result.get("data") or {}
        refund.paystack_refund_id = str(data.get("id") or data.get("transaction") or "")
        refund.status = RefundStatus.PROCESSED
        refund.raw = result
        refund.save()
    except PaymentError as exc:
        refund.status = RefundStatus.FAILED
        refund.raw = {"error": exc.message, "code": exc.code}
        refund.save()
        raise

    payment.amount_refunded_minor += amt
    if payment.amount_refunded_minor >= payment.amount_minor:
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED
    payment.save(update_fields=["amount_refunded_minor", "status", "updated_at"])

    invoice = payment.invoice
    invoice.amount_paid_minor = max(0, invoice.amount_paid_minor - amt)
    if invoice.amount_paid_minor <= 0:
        invoice.status = InvoiceStatus.REFUNDED
        invoice.paid_at = None
    elif invoice.amount_paid_minor < invoice.amount_minor:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    invoice.save()

    invalidate_gates_for_user(payment.user)

    log_audit(
        actor=requested_by,
        action="payment.refund",
        obj=refund,
        after={"amount_minor": amt, "payment_reference": payment.reference},
        request=request,
    )
    return refund


def persist_webhook_event(*, raw_body: bytes, signature: str | None) -> PaystackWebhookEvent:
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    existing = PaystackWebhookEvent.objects.filter(payload_hash=payload_hash).first()
    if existing:
        return existing
    valid = verify_paystack_signature(raw_body, signature)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {}
    event = PaystackWebhookEvent.objects.create(
        event_id=str((payload.get("data") or {}).get("id") or ""),
        event_type=payload.get("event") or "",
        signature_valid=valid,
        payload_hash=payload_hash,
        payload=payload,
    )
    return event


def process_webhook_event(event: PaystackWebhookEvent) -> None:
    if event.processed_at:
        return
    if not event.signature_valid:
        event.processing_error = "invalid_signature"
        event.processed_at = timezone.now()
        event.save(update_fields=["processing_error", "processed_at", "updated_at"])
        raise PaymentError("Invalid webhook signature", code="invalid_signature")

    if event.event_type == "charge.success":
        data = event.payload.get("data") or {}
        reference = data.get("reference")
        if reference:
            settle_payment(reference=reference, verify_payload=data)
    elif event.event_type in {"refund.processed", "refund.pending", "refund.failed"}:
        data = event.payload.get("data") or {}
        refund_id = str(data.get("id") or "")
        if refund_id:
            refund = Refund.objects.filter(paystack_refund_id=refund_id).first()
            if refund:
                if event.event_type == "refund.processed":
                    refund.status = RefundStatus.PROCESSED
                elif event.event_type == "refund.failed":
                    refund.status = RefundStatus.FAILED
                else:
                    refund.status = RefundStatus.PENDING
                refund.raw = data
                refund.save()
    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at", "updated_at"])


# --- Finance aggregations ---


def finance_overview(*, currency: str = "NGN") -> dict:
    inv = Invoice.objects.filter(currency=currency).exclude(status=InvoiceStatus.VOID)
    invoiced = inv.aggregate(s=Sum("amount_minor"))["s"] or 0
    collected = (
        Payment.objects.filter(currency=currency, status=PaymentStatus.SUCCESS).aggregate(
            s=Sum("amount_minor")
        )["s"]
        or 0
    )
    refunded = (
        Refund.objects.filter(status=RefundStatus.PROCESSED).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )
    outstanding_minor = 0
    overdue_minor = 0
    now = timezone.now()
    for row in inv.filter(status__in=[InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID]).values(
        "amount_minor", "amount_paid_minor", "due_at"
    ):
        bal = max(0, row["amount_minor"] - row["amount_paid_minor"])
        outstanding_minor += bal
        if row["due_at"] and row["due_at"] < now:
            overdue_minor += bal

    attempts = PaymentAttempt.objects.count()
    successes = PaymentAttempt.objects.filter(status=PaymentAttemptStatus.SUCCESS).count()
    success_rate = (successes / attempts) if attempts else 0.0
    collection_rate = (collected / invoiced) if invoiced else 0.0

    return {
        "currency": currency,
        "invoiced_minor": invoiced,
        "collected_minor": collected,
        "refunded_minor": refunded,
        "outstanding_minor": outstanding_minor,
        "overdue_minor": overdue_minor,
        "collection_rate": round(collection_rate, 4),
        "success_rate": round(success_rate, 4),
        "attempts": attempts,
        "successes": successes,
    }


def finance_attempts_vs_paid() -> dict:
    total = PaymentAttempt.objects.count()
    by_status = {
        row["status"]: row["c"]
        for row in PaymentAttempt.objects.values("status").annotate(c=Count("id"))
    }
    successes = by_status.get(PaymentAttemptStatus.SUCCESS, 0)
    failures = by_status.get(PaymentAttemptStatus.FAILED, 0)
    abandoned = by_status.get(PaymentAttemptStatus.ABANDONED, 0)
    unique_payers = (
        PaymentAttempt.objects.filter(status=PaymentAttemptStatus.SUCCESS)
        .values("user_id")
        .distinct()
        .count()
    )
    paid_invoices = Invoice.objects.filter(status=InvoiceStatus.PAID).count()
    avg_attempts = None
    if paid_invoices:
        attempt_counts = (
            PaymentAttempt.objects.filter(invoice__status=InvoiceStatus.PAID)
            .values("invoice_id")
            .annotate(c=Count("id"))
        )
        vals = [r["c"] for r in attempt_counts]
        avg_attempts = round(sum(vals) / len(vals), 2) if vals else 0

    return {
        "total_attempts": total,
        "successes": successes,
        "failures": failures,
        "abandoned": abandoned,
        "success_rate": round((successes / total), 4) if total else 0.0,
        "unique_payers": unique_payers,
        "avg_attempts_per_paid_invoice": avg_attempts,
        "by_status": by_status,
    }


def finance_aging() -> dict:
    now = timezone.now()
    buckets = {"1_7": 0, "8_30": 0, "31_60": 0, "60_plus": 0, "no_deadline": 0, "not_due": 0}
    qs = Invoice.objects.filter(status__in=[InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID])
    for inv in qs:
        bal = inv.balance_minor
        if bal <= 0:
            continue
        if not inv.due_at:
            buckets["no_deadline"] += bal
            continue
        if inv.due_at >= now:
            buckets["not_due"] += bal
            continue
        days = (now - inv.due_at).days
        if days <= 7:
            buckets["1_7"] += bal
        elif days <= 30:
            buckets["8_30"] += bal
        elif days <= 60:
            buckets["31_60"] += bal
        else:
            buckets["60_plus"] += bal
    return {"buckets_minor": buckets, "currency": "NGN"}


def finance_outstanding(*, limit: int = 100) -> list[dict]:
    rows = []
    qs = (
        Invoice.objects.filter(status__in=[InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID])
        .select_related("user")
        .order_by("due_at", "-created_at")[:limit]
    )
    for inv in qs:
        rows.append(
            {
                "invoice_id": str(inv.id),
                "number": inv.number,
                "user_id": str(inv.user_id),
                "user_email": inv.user.email,
                "kind": inv.kind,
                "description": inv.description,
                "amount_minor": inv.amount_minor,
                "amount_paid_minor": inv.amount_paid_minor,
                "balance_minor": inv.balance_minor,
                "due_at": inv.due_at,
                "currency": inv.currency,
                "status": inv.status,
            }
        )
    return rows
