from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    ACCOUNT_PENDING = "account_pending", "Account pending"
    ACCOUNT_ACTIVE = "account_active", "Account active"
    FEE_PENDING = "fee_pending", "Fee pending"
    FEE_PAID = "fee_paid", "Fee paid"
    UNDER_REVIEW = "under_review", "Under review"
    ADMITTED = "admitted", "Admitted"
    WAITLISTED = "waitlisted", "Waitlisted"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class Application(BaseModel):
    cohort = models.ForeignKey(
        "programs.Cohort", on_delete=models.CASCADE, related_name="applications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    applicant_email = models.EmailField(db_index=True)
    applicant_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=32, blank=True)
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=32, choices=ApplicationStatus.choices, default=ApplicationStatus.SUBMITTED
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    onboarding_token_hash = models.CharField(max_length=128, blank=True)
    onboarding_sent_at = models.DateTimeField(null=True, blank=True)
    fee_invoice = models.ForeignKey(
        "payments.Invoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applications",
    )
    fee_paid_at = models.DateTimeField(null=True, blank=True)
    admitted_class_ids = models.JSONField(default=list, blank=True)
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cohort", "applicant_email"],
                name="uniq_application_email_per_cohort",
            )
        ]

    def __str__(self) -> str:
        return f"{self.applicant_email} → {self.cohort.slug} ({self.status})"


class Admission(BaseModel):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="admissions"
    )
    class_ref = models.ForeignKey(
        "programs.Class", on_delete=models.CASCADE, related_name="admissions"
    )
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    admitted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    fee_handling = models.CharField(max_length=32, default="generate")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "class_ref"], name="uniq_admission_app_class"
            )
        ]


class EnrollmentStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Pending payment"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    WITHDRAWN = "withdrawn", "Withdrawn"


class Enrollment(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    class_ref = models.ForeignKey(
        "programs.Class", on_delete=models.CASCADE, related_name="enrollments"
    )
    cohort = models.ForeignKey(
        "programs.Cohort", on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(
        max_length=32, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "class_ref"], name="uniq_enrollment_user_class")
        ]
