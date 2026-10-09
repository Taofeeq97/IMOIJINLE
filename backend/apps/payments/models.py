from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class FeeItemKind(models.TextChoices):
    TUITION = "tuition", "Tuition"
    APPLICATION = "application", "Application"
    ADDON = "addon", "Addon"
    MATERIALS = "materials", "Materials"
    LATE_FEE = "late_fee", "Late fee"
    CUSTOM = "custom", "Custom"


class FeeItem(BaseModel):
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=64, unique=True)
    kind = models.CharField(max_length=32, choices=FeeItemKind.choices, default=FeeItemKind.TUITION)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="NGN")
    taxable = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    refundable = models.BooleanField(default=True)
    refundable_policy = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} ({self.amount_minor})"


class FeeScopeType(models.TextChoices):
    ALL = "all", "All"
    PROGRAM = "program", "Program"
    COHORT = "cohort", "Cohort"
    CLASS = "class", "Class"
    SUBJECT = "subject", "Subject"
    USER = "user", "User"


class FeeMode(models.TextChoices):
    MANDATORY = "mandatory", "Mandatory"
    OPTIONAL = "optional", "Optional"


class FeeBilling(models.TextChoices):
    ONE_OFF = "one_off", "One-off"
    INSTALLMENTS = "installments", "Installments"


class FeeRule(BaseModel):
    fee_item = models.ForeignKey(FeeItem, on_delete=models.CASCADE, related_name="rules")
    scope_type = models.CharField(
        max_length=32, choices=FeeScopeType.choices, default=FeeScopeType.CLASS
    )
    scope_id = models.UUIDField(null=True, blank=True, db_index=True)
    mode = models.CharField(max_length=16, choices=FeeMode.choices, default=FeeMode.MANDATORY)
    billing = models.CharField(
        max_length=24, choices=FeeBilling.choices, default=FeeBilling.ONE_OFF
    )
    plan = models.JSONField(default=dict, blank=True)
    due_rule = models.JSONField(default=dict, blank=True)
    gate_rule = models.JSONField(default=dict, blank=True)
    priority = models.IntegerField(default=100)
    exclusive = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["priority", "-created_at"]


class CustomChargeTarget(models.TextChoices):
    COHORT = "cohort", "Cohort"
    CLASS = "class", "Class"
    ENROLLMENTS = "enrollments", "Enrollments"
    USER = "user", "User"


class CustomCharge(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    target_type = models.CharField(max_length=32, choices=CustomChargeTarget.choices)
    target_ids = models.JSONField(default=list, blank=True)
    mandatory = models.BooleanField(default=True)
    due_at = models.DateTimeField(null=True, blank=True)
    gate_rule = models.JSONField(default=dict, blank=True)
    notify = models.BooleanField(default=True)
    fee_item = models.ForeignKey(
        FeeItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="custom_charges"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_charges_created",
    )

    class Meta:
        ordering = ["-created_at"]


class InvoiceKind(models.TextChoices):
    APPLICATION = "application", "Application fee"
    CLASS = "class", "Class fee"
    SUBJECT = "subject", "Subject fee"
    CUSTOM = "custom", "Custom"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    PARTIALLY_PAID = "partially_paid", "Partially paid"
    PAID = "paid", "Paid"
    VOID = "void", "Void"
    REFUNDED = "refunded", "Refunded"


class InvoiceSource(models.TextChoices):
    RULE = "rule", "Fee rule"
    CUSTOM = "custom", "Custom charge"
    APPLICATION = "application", "Application"
    MANUAL = "manual", "Manual"


class Invoice(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices"
    )
    number = models.CharField(max_length=64, blank=True, db_index=True)
    kind = models.CharField(max_length=32, choices=InvoiceKind.choices)
    status = models.CharField(
        max_length=32, choices=InvoiceStatus.choices, default=InvoiceStatus.OPEN
    )
    currency = models.CharField(max_length=3, default="NGN")
    amount_minor = models.BigIntegerField()
    amount_paid_minor = models.BigIntegerField(default=0)
    description = models.CharField(max_length=255, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=32, choices=InvoiceSource.choices, default=InvoiceSource.MANUAL, blank=True
    )
    enrollment = models.ForeignKey(
        "admissions.Enrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    fee_rule = models.ForeignKey(
        FeeRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    fee_item = models.ForeignKey(
        FeeItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    custom_charge = models.ForeignKey(
        CustomCharge, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    gate_rule = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def balance_minor(self) -> int:
        return max(0, self.amount_minor - self.amount_paid_minor)


class InvoiceLine(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    fee_item = models.ForeignKey(
        FeeItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_lines"
    )
    description = models.CharField(max_length=255, blank=True)
    amount_minor = models.BigIntegerField()
    discount_minor = models.BigIntegerField(default=0)
    installment_no = models.PositiveSmallIntegerField(default=1)
    due_at = models.DateTimeField(null=True, blank=True)
    amount_paid_minor = models.BigIntegerField(default=0)
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="open")

    class Meta:
        ordering = ["installment_no", "created_at"]

    @property
    def line_total_minor(self) -> int:
        return max(0, self.amount_minor - self.discount_minor)

    @property
    def balance_minor(self) -> int:
        return max(0, self.line_total_minor - self.amount_paid_minor)

    # Alias used by installment helpers that speak in unit amounts
    @property
    def unit_amount_minor(self) -> int:
        return self.amount_minor


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    ABANDONED = "abandoned", "Abandoned"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"


class Payment(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    amount_minor = models.BigIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    provider = models.CharField(max_length=32, default="paystack")
    reference = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED
    )
    channel = models.CharField(max_length=32, blank=True)
    access_code = models.CharField(max_length=128, blank=True)
    authorization_url = models.URLField(blank=True)
    paystack_id = models.CharField(max_length=64, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    fees_minor = models.BigIntegerField(default=0)
    amount_refunded_minor = models.BigIntegerField(default=0)
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)
    invoice_line = models.ForeignKey(
        InvoiceLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class PaymentAttemptStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    OPENED = "opened", "Opened"
    PENDING = "pending", "Pending"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    ABANDONED = "abandoned", "Abandoned"
    EXPIRED = "expired", "Expired"


class PaymentAttempt(BaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_attempts"
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="attempts"
    )
    reference = models.CharField(max_length=64, blank=True, db_index=True)
    access_code = models.CharField(max_length=128, blank=True)
    authorization_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=32, choices=PaymentAttemptStatus.choices, default=PaymentAttemptStatus.INITIATED
    )
    channel = models.CharField(max_length=32, blank=True)
    failure_code = models.CharField(max_length=64, blank=True)
    failure_message = models.CharField(max_length=255, blank=True)
    attempt_no = models.PositiveIntegerField(default=1)
    device_type = models.CharField(max_length=32, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    time_to_complete_s = models.PositiveIntegerField(null=True, blank=True)
    retry_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retries"
    )

    class Meta:
        ordering = ["-created_at"]


class RefundStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    PROCESSING = "processing", "Processing"
    PENDING = "pending", "Pending"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"


class Refund(BaseModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="refunds")
    amount_minor = models.BigIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32, choices=RefundStatus.choices, default=RefundStatus.REQUESTED
    )
    paystack_refund_id = models.CharField(max_length=64, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunds_requested",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refunds_approved",
    )
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class AccessOverride(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_overrides"
    )
    scope_type = models.CharField(
        max_length=32, choices=[("class", "Class"), ("subject", "Subject")]
    )
    scope_id = models.UUIDField(db_index=True)
    until = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_overrides_granted",
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]


class NotificationScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    PROGRAM = "program", "Program"
    COHORT = "cohort", "Cohort"
    FEE_ITEM = "fee_item", "Fee item"
    CUSTOM_CHARGE = "custom_charge", "Custom charge"


class PaymentNotificationConfig(BaseModel):
    scope_type = models.CharField(
        max_length=32, choices=NotificationScopeType.choices, default=NotificationScopeType.GLOBAL
    )
    scope_id = models.UUIDField(null=True, blank=True)
    event = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)
    channels = models.JSONField(default=list, blank=True)
    recipients = models.JSONField(default=list, blank=True)
    offsets = models.JSONField(default=list, blank=True)
    quiet_hours = models.JSONField(default=dict, blank=True)
    send_digest = models.BooleanField(default=False)

    class Meta:
        ordering = ["event", "scope_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["scope_type", "scope_id", "event"],
                name="uniq_payment_notification_scope_event",
            )
        ]


class FinanceDailyRollup(BaseModel):
    date = models.DateField(db_index=True)
    cohort_id = models.UUIDField(null=True, blank=True)
    class_id = models.UUIDField(null=True, blank=True)
    fee_item_id = models.UUIDField(null=True, blank=True)
    channel = models.CharField(max_length=32, blank=True)
    invoiced_minor = models.BigIntegerField(default=0)
    collected_minor = models.BigIntegerField(default=0)
    refunded_minor = models.BigIntegerField(default=0)
    outstanding_minor = models.BigIntegerField(default=0)
    overdue_minor = models.BigIntegerField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    successes = models.PositiveIntegerField(default=0)
    failures = models.PositiveIntegerField(default=0)
    abandoned = models.PositiveIntegerField(default=0)
    fees_minor = models.BigIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "cohort_id", "class_id", "fee_item_id", "channel"],
                name="uniq_finance_daily_rollup_dims",
            )
        ]


class PaystackWebhookEvent(BaseModel):
    event_id = models.CharField(max_length=128, blank=True, db_index=True)
    event_type = models.CharField(max_length=64, blank=True)
    signature_valid = models.BooleanField(default=False)
    payload_hash = models.CharField(max_length=64, unique=True)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
