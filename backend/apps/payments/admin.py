from django.contrib import admin

from apps.payments.models import (
    AccessOverride,
    CustomCharge,
    FeeItem,
    FeeRule,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAttempt,
    PaymentNotificationConfig,
    PaystackWebhookEvent,
    Refund,
)


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "amount_minor", "currency", "active")
    list_filter = ("kind", "active")
    search_fields = ("code", "name")


@admin.register(FeeRule)
class FeeRuleAdmin(admin.ModelAdmin):
    list_display = ("fee_item", "scope_type", "scope_id", "mode", "billing", "priority", "active")
    list_filter = ("scope_type", "mode", "billing", "active")


@admin.register(CustomCharge)
class CustomChargeAdmin(admin.ModelAdmin):
    list_display = ("title", "amount_minor", "target_type", "created_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "kind", "status", "amount_minor", "currency", "created_at")
    list_filter = ("kind", "status", "source")
    search_fields = ("number", "description")


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "installment_no", "amount_minor", "due_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "status", "amount_minor", "currency", "paid_at")
    list_filter = ("status",)
    search_fields = ("reference",)


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "status", "attempt_no", "created_at")
    list_filter = ("status",)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("payment", "amount_minor", "status", "created_at")
    list_filter = ("status",)


@admin.register(AccessOverride)
class AccessOverrideAdmin(admin.ModelAdmin):
    list_display = ("user", "scope_type", "scope_id", "active", "until")


@admin.register(PaymentNotificationConfig)
class PaymentNotificationConfigAdmin(admin.ModelAdmin):
    list_display = ("event", "scope_type", "enabled")
    list_filter = ("event", "enabled")




@admin.register(PaystackWebhookEvent)
class PaystackWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "signature_valid", "processed_at", "created_at")
    readonly_fields = ("payload", "payload_hash")
