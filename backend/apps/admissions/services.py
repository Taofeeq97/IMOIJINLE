from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.accounts.policies import assign_role
from apps.admissions.models import (
    Admission,
    Application,
    ApplicationStatus,
    Enrollment,
    EnrollmentStatus,
)
from apps.audit.services import log_audit
from apps.orgsettings.models import ApplicationFeeSettings
from apps.payments.services import create_application_invoice
from apps.programs.models import Class, Cohort, CohortStatus


class AdmissionsError(Exception):
    def __init__(self, message: str, code: str = "admissions_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def resolve_application_fee_kobo(cohort: Cohort) -> int:
    if cohort.application_fee_kobo is not None:
        return int(cohort.application_fee_kobo)
    fees = ApplicationFeeSettings.get_solo()
    if fees.is_free:
        return 0
    return int(fees.default_amount_kobo or 0)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def _send_onboarding_email(*, user: User, application: Application, raw_token: str) -> None:
    link = f"{settings.FRONTEND_URL}/onboarding/set-password?token={raw_token}&application_id={application.id}"
    send_mail(
        subject="Continue your Imo Ijinle application",
        message=(
            f"Hello {application.applicant_name},\n\n"
            f"Set up your account to continue: {link}\n\n"
            "This link expires in 72 hours. If you did not apply, ignore this email.\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def _issue_onboarding_token(application: Application) -> str:
    raw = secrets.token_urlsafe(32)
    application.onboarding_token_hash = _hash_token(raw)
    application.onboarding_sent_at = timezone.now()
    application.save(update_fields=["onboarding_token_hash", "onboarding_sent_at", "updated_at"])
    return raw


@transaction.atomic
def submit_application(
    *,
    cohort_slug: str,
    full_name: str,
    email: str,
    phone: str = "",
    data: dict | None = None,
    request=None,
) -> tuple[Application, str | None]:
    """Returns (application, raw_onboarding_token_or_None). Token only for new invites."""
    try:
        cohort = Cohort.objects.get(slug=cohort_slug)
    except Cohort.DoesNotExist as exc:
        raise AdmissionsError("Cohort not found.", code="not_found") from exc

    if cohort.status != CohortStatus.APPLICATIONS_OPEN:
        raise AdmissionsError("Applications are not open for this cohort.", code="closed")

    email_n = email.lower().strip()
    existing = Application.objects.filter(cohort=cohort, applicant_email__iexact=email_n).first()
    if existing:
        # Do not reveal; optionally re-send continue link if pending
        if existing.status in {
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.ACCOUNT_PENDING,
        }:
            raw = _issue_onboarding_token(existing)
            _send_onboarding_email(user=existing.user, application=existing, raw_token=raw)
            existing.status = ApplicationStatus.ACCOUNT_PENDING
            existing.save(update_fields=["status", "updated_at"])
        return existing, None

    first, last = _split_name(full_name)
    user = User.objects.filter(email__iexact=email_n).first()
    created_user = False
    if user is None:
        user = User(email=email_n, first_name=first, last_name=last, phone=phone, is_active=False)
        user.set_unusable_password()
        user.save()
        assign_role(user=user, role=Role.APPLICANT, actor=None, request=request)
        created_user = True
    else:
        # Existing account: attach application, send continue link, no enumeration
        pass

    application = Application.objects.create(
        cohort=cohort,
        user=user,
        applicant_email=email_n,
        applicant_name=full_name.strip(),
        phone=phone,
        data=data or {},
        status=ApplicationStatus.SUBMITTED,
    )

    fee_kobo = resolve_application_fee_kobo(cohort)
    if fee_kobo > 0:
        invoice = create_application_invoice(
            user=user, amount_kobo=fee_kobo, application_id=str(application.id)
        )
        application.fee_invoice = invoice
        application.save(update_fields=["fee_invoice", "updated_at"])

    raw_token = None
    if created_user or not user.has_usable_password() or not user.is_active:
        raw_token = _issue_onboarding_token(application)
        _send_onboarding_email(user=user, application=application, raw_token=raw_token)
        application.status = ApplicationStatus.ACCOUNT_PENDING
        application.save(update_fields=["status", "updated_at"])
    else:
        # Active existing user — skip to fee or review
        application.status = (
            ApplicationStatus.FEE_PENDING if fee_kobo > 0 else ApplicationStatus.ACCOUNT_ACTIVE
        )
        if fee_kobo == 0:
            application.status = ApplicationStatus.UNDER_REVIEW
        application.save(update_fields=["status", "updated_at"])
        send_mail(
            subject="Continue your Imo Ijinle application",
            message=f"Sign in at {settings.FRONTEND_URL}/login to continue your application.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

    log_audit(
        actor=user if user.is_active else None,
        action="application.submit",
        obj=application,
        after={"cohort": cohort.slug, "email": email_n, "status": application.status},
        request=request,
    )
    return application, raw_token


def resend_onboarding(*, application: Application, request=None) -> None:
    if application.status not in {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.ACCOUNT_PENDING,
    }:
        raise AdmissionsError("Onboarding already completed.", code="already_active")
    if application.onboarding_sent_at:
        elapsed = timezone.now() - application.onboarding_sent_at
        if elapsed < timedelta(minutes=1):
            raise AdmissionsError("Please wait before requesting another link.", code="rate_limited")
    raw = _issue_onboarding_token(application)
    _send_onboarding_email(user=application.user, application=application, raw_token=raw)
    application.status = ApplicationStatus.ACCOUNT_PENDING
    application.save(update_fields=["status", "updated_at"])
    log_audit(actor=None, action="application.resend_onboarding", obj=application, request=request)


def change_application_email(*, application: Application, new_email: str, request=None) -> Application:
    if application.status not in {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.ACCOUNT_PENDING,
    }:
        raise AdmissionsError("Email can only be changed before account activation.", code="forbidden")
    email_n = new_email.lower().strip()
    if Application.objects.filter(cohort=application.cohort, applicant_email__iexact=email_n).exclude(
        pk=application.pk
    ).exists():
        raise AdmissionsError("Unable to update email.", code="email_unavailable")

    user = application.user
    user.email = email_n
    user.save(update_fields=["email", "updated_at"])
    application.applicant_email = email_n
    application.save(update_fields=["applicant_email", "updated_at"])
    raw = _issue_onboarding_token(application)
    _send_onboarding_email(user=user, application=application, raw_token=raw)
    log_audit(actor=None, action="application.change_email", obj=application, after={"email": email_n}, request=request)
    return application


def verify_onboarding_token(*, token: str, application_id: str) -> Application:
    try:
        application = Application.objects.select_related("user").get(id=application_id)
    except Application.DoesNotExist as exc:
        raise AdmissionsError("Invalid link.", code="invalid_token") from exc
    if not application.onboarding_token_hash:
        raise AdmissionsError("This link has already been used.", code="used")
    if application.onboarding_sent_at and timezone.now() - application.onboarding_sent_at > timedelta(hours=72):
        raise AdmissionsError("This link has expired.", code="expired")
    if _hash_token(token) != application.onboarding_token_hash:
        raise AdmissionsError("Invalid link.", code="invalid_token")
    return application


@transaction.atomic
def set_password_from_onboarding(*, token: str, application_id: str, password: str, request=None) -> User:
    application = verify_onboarding_token(token=token, application_id=application_id)
    user = application.user
    user.set_password(password)
    user.is_active = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["password", "is_active", "email_verified_at", "updated_at"])

    application.onboarding_token_hash = ""
    fee_kobo = resolve_application_fee_kobo(application.cohort)
    if fee_kobo > 0:
        application.status = ApplicationStatus.FEE_PENDING
        if application.fee_invoice is None:
            invoice = create_application_invoice(
                user=user, amount_kobo=fee_kobo, application_id=str(application.id)
            )
            application.fee_invoice = invoice
    else:
        application.status = ApplicationStatus.UNDER_REVIEW
    application.save()

    log_audit(
        actor=user,
        action="auth.onboarding_set_password",
        obj=application,
        after={"status": application.status},
        request=request,
    )
    return user


def on_application_fee_paid(*, application_id: str, payment, request=None) -> None:
    try:
        application = Application.objects.select_related("fee_invoice").get(id=application_id)
    except Application.DoesNotExist:
        return
    application.fee_paid_at = timezone.now()
    application.status = ApplicationStatus.FEE_PAID
    application.save(update_fields=["fee_paid_at", "status", "updated_at"])
    log_audit(
        actor=application.user,
        action="application.fee_paid",
        obj=application,
        after={"payment_ref": payment.reference},
        request=request,
    )
    send_mail(
        subject="Application fee received — Imo Ijinle Academy",
        message=f"We received your application fee (ref {payment.reference}). Your application is under review.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.applicant_email],
        fail_silently=True,
    )
    # Move to under_review shortly after fee paid
    application.status = ApplicationStatus.UNDER_REVIEW
    application.save(update_fields=["status", "updated_at"])


@transaction.atomic
def admit_application(
    *,
    application: Application,
    class_ids: list,
    admitted_by: User,
    fee_handling: str = "generate",
    notes: str = "",
    request=None,
) -> Application:
    fees = ApplicationFeeSettings.get_solo()
    fee_kobo = resolve_application_fee_kobo(application.cohort)
    if fees.fee_required_before_admit and fee_kobo > 0:
        if application.status not in {
            ApplicationStatus.FEE_PAID,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.ADMITTED,
        } or (application.fee_invoice and application.fee_invoice.status != "paid"):
            # Allow under_review only if fee was paid
            if not application.fee_paid_at:
                raise AdmissionsError(
                    "Application fee must be paid before admit.",
                    code="fee_required",
                )

    if application.status in {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.ACCOUNT_PENDING,
    }:
        raise AdmissionsError("Applicant must activate their account first.", code="account_inactive")

    classes = list(Class.objects.filter(id__in=class_ids, cohort=application.cohort))
    if not classes:
        raise AdmissionsError("Select at least one class in this cohort.", code="invalid_classes")

    admitted_ids: list[str] = list(application.admitted_class_ids or [])
    for class_obj in classes:
        Admission.objects.get_or_create(
            application=application,
            class_ref=class_obj,
            defaults={
                "admitted_by": admitted_by,
                "notes": notes,
                "fee_handling": fee_handling,
            },
        )
        Enrollment.objects.get_or_create(
            user=application.user,
            class_ref=class_obj,
            defaults={
                "cohort": application.cohort,
                "status": EnrollmentStatus.ACTIVE,
                "notes": notes,
            },
        )
        if fee_handling == "generate":
            from apps.admissions.models import Enrollment as Enr

            enr = Enr.objects.filter(user=application.user, class_ref=class_obj).first()
            if enr:
                from apps.payments.fees import generate_invoices_for_enrollment

                generate_invoices_for_enrollment(
                    enrollment=enr, actor=admitted_by, request=request
                )
        if str(class_obj.id) not in admitted_ids:
            admitted_ids.append(str(class_obj.id))

    assign_role(user=application.user, role=Role.STUDENT, actor=admitted_by, request=request)
    application.admitted_class_ids = admitted_ids
    application.status = ApplicationStatus.ADMITTED
    application.reviewer_notes = notes
    application.save()

    send_mail(
        subject="Welcome to Imo Ijinle Academy",
        message=(
            f"Congratulations {application.applicant_name}!\n\n"
            f"You have been admitted. Sign in and open My learning: {settings.FRONTEND_URL}/learning\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.applicant_email],
        fail_silently=True,
    )
    log_audit(
        actor=admitted_by,
        action="application.admit",
        obj=application,
        after={"class_ids": admitted_ids, "fee_handling": fee_handling},
        request=request,
    )
    return application
