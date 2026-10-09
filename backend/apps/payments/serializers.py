from __future__ import annotations

from rest_framework import serializers

from apps.payments.models import (
    CustomCharge,
    FeeItem,
    FeeRule,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAttempt,
    PaymentNotificationConfig,
    Refund,
)


class FeeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeItem
        fields = [
            "id",
            "name",
            "code",
            "kind",
            "amount_minor",
            "currency",
            "taxable",
            "description",
            "active",
            "refundable_policy",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FeeRuleSerializer(serializers.ModelSerializer):
    fee_item_detail = FeeItemSerializer(source="fee_item", read_only=True)

    class Meta:
        model = FeeRule
        fields = [
            "id",
            "fee_item",
            "fee_item_detail",
            "scope_type",
            "scope_id",
            "mode",
            "billing",
            "plan",
            "due_rule",
            "gate_rule",
            "priority",
            "exclusive",
            "starts_at",
            "ends_at",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    line_total_minor = serializers.IntegerField(read_only=True)
    balance_minor = serializers.IntegerField(read_only=True)

    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "fee_item",
            "description",
            "amount_minor",
            "discount_minor",
            "installment_no",
            "due_at",
            "amount_paid_minor",
            "line_total_minor",
            "balance_minor",
            "status",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    balance_minor = serializers.IntegerField(read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "user",
            "user_email",
            "kind",
            "status",
            "currency",
            "amount_minor",
            "amount_paid_minor",
            "balance_minor",
            "description",
            "due_at",
            "paid_at",
            "source",
            "enrollment",
            "fee_rule",
            "fee_item",
            "custom_charge",
            "gate_rule",
            "metadata",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CustomChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCharge
        fields = [
            "id",
            "title",
            "description",
            "amount_minor",
            "currency",
            "target_type",
            "target_ids",
            "mandatory",
            "due_at",
            "gate_rule",
            "created_by",
            "notify",
            "fee_item",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class CustomChargeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    amount_minor = serializers.IntegerField(min_value=1)
    currency = serializers.CharField(max_length=3, default="NGN")
    target_type = serializers.ChoiceField(choices=["cohort", "class", "enrollments", "user"])
    target_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    mandatory = serializers.BooleanField(default=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    gate_rule = serializers.DictField(required=False, default=dict)
    notify = serializers.BooleanField(default=True)
    fee_item = serializers.UUIDField(required=False, allow_null=True)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "user",
            "amount_minor",
            "currency",
            "provider",
            "reference",
            "status",
            "channel",
            "access_code",
            "authorization_url",
            "paid_at",
            "fees_minor",
            "amount_refunded_minor",
            "created_at",
        ]
        read_only_fields = fields


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "invoice",
            "payment",
            "user",
            "reference",
            "status",
            "attempt_no",
            "channel",
            "failure_code",
            "failure_message",
            "created_at",
        ]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source="payment.reference", read_only=True)

    class Meta:
        model = Refund
        fields = [
            "id",
            "payment",
            "payment_reference",
            "amount_minor",
            "reason",
            "status",
            "paystack_refund_id",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "paystack_refund_id",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
            "payment_reference",
        ]


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    amount_minor = serializers.IntegerField(required=False, min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PaymentNotificationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentNotificationConfig
        fields = [
            "id",
            "scope_type",
            "scope_id",
            "event",
            "enabled",
            "channels",
            "recipients",
            "offsets",
            "quiet_hours",
            "send_digest",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvoicePaySerializer(serializers.Serializer):
    callback_url = serializers.URLField(required=False, allow_null=True)
