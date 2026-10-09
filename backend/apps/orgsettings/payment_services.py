from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.audit.services import log_audit
from apps.orgsettings.models import ApplicationFeeSettings, PaymentGatewaySettings

_SECRET_SALT = "imo-paystack-secret-v1"


def encrypt_secret(raw: str) -> str:
    if not raw:
        return ""
    return signing.dumps(raw, salt=_SECRET_SALT)


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return signing.loads(token, salt=_SECRET_SALT)
    except signing.BadSignature:
        return ""


def mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}••••{value[-4:]}"


def gateway_public_payload(obj: PaymentGatewaySettings) -> dict[str, Any]:
    api_base = getattr(settings, "API_PUBLIC_URL", None) or "http://localhost:8000"
    return {
        "mode": obj.mode,
        "public_key_masked": mask_key(obj.public_key),
        "public_key_set": bool(obj.public_key),
        "secret_key_set": bool(obj.secret_key_encrypted),
        "default_currency": obj.default_currency,
        "channels": {
            "card": obj.channel_card,
            "bank": obj.channel_bank,
            "ussd": obj.channel_ussd,
            "transfer": obj.channel_transfer,
            "mobile_money": obj.channel_mobile_money,
        },
        "webhook_url": f"{api_base}/api/v1/payments/webhooks/paystack/",
        "last_tested_at": obj.last_tested_at.isoformat() if obj.last_tested_at else None,
        "last_test_ok": obj.last_test_ok,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


def update_gateway(*, data: dict[str, Any], actor, request=None) -> PaymentGatewaySettings:
    obj = PaymentGatewaySettings.get_solo()
    before = gateway_public_payload(obj)
    if "mode" in data and data["mode"] in {"test", "live"}:
        obj.mode = data["mode"]
    if "public_key" in data and data["public_key"] is not None:
        obj.public_key = str(data["public_key"])
    if "secret_key" in data and data["secret_key"]:
        obj.secret_key_encrypted = encrypt_secret(str(data["secret_key"]))
    if "default_currency" in data and data["default_currency"]:
        obj.default_currency = str(data["default_currency"]).upper()[:3]
    channels = data.get("channels") or {}
    if "card" in channels:
        obj.channel_card = bool(channels["card"])
    if "bank" in channels:
        obj.channel_bank = bool(channels["bank"])
    if "ussd" in channels:
        obj.channel_ussd = bool(channels["ussd"])
    if "transfer" in channels:
        obj.channel_transfer = bool(channels["transfer"])
    if "mobile_money" in channels:
        obj.channel_mobile_money = bool(channels["mobile_money"])
    obj.save()
    after = gateway_public_payload(obj)
    log_audit(
        actor=actor,
        action="settings.payments.gateway.update",
        obj=obj,
        before=before,
        after=after,
        request=request,
    )
    return obj


def application_fee_payload(obj: ApplicationFeeSettings) -> dict[str, Any]:
    return {
        "default_amount_kobo": obj.default_amount_kobo,
        "default_amount_naira": (obj.default_amount_kobo or 0) / 100,
        "is_free": obj.is_free,
        "refundable_policy": obj.refundable_policy or {},
        "fee_required_before_admit": obj.fee_required_before_admit,
        "waiver_codes": obj.waiver_codes or [],
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


def update_application_fees(*, data: dict[str, Any], actor, request=None) -> ApplicationFeeSettings:
    obj = ApplicationFeeSettings.get_solo()
    before = application_fee_payload(obj)
    if "is_free" in data:
        obj.is_free = bool(data["is_free"])
        if obj.is_free:
            obj.default_amount_kobo = 0
    if "default_amount_kobo" in data and data["default_amount_kobo"] is not None:
        amount = int(data["default_amount_kobo"])
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        obj.default_amount_kobo = amount
        obj.is_free = amount == 0
    if "default_amount_naira" in data and data["default_amount_naira"] is not None:
        naira = float(data["default_amount_naira"])
        amount = int(round(naira * 100))
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        obj.default_amount_kobo = amount
        obj.is_free = amount == 0
    if "refundable_policy" in data and data["refundable_policy"] is not None:
        obj.refundable_policy = data["refundable_policy"]
    if "fee_required_before_admit" in data:
        obj.fee_required_before_admit = bool(data["fee_required_before_admit"])
    if "waiver_codes" in data and data["waiver_codes"] is not None:
        obj.waiver_codes = data["waiver_codes"]
    obj.save()
    after = application_fee_payload(obj)
    log_audit(
        actor=actor,
        action="settings.payments.application_fees.update",
        obj=obj,
        before=before,
        after=after,
        request=request,
    )
    return obj


def mark_gateway_tested(*, ok: bool, actor, request=None) -> PaymentGatewaySettings:
    obj = PaymentGatewaySettings.get_solo()
    obj.last_tested_at = timezone.now()
    obj.last_test_ok = ok
    obj.save(update_fields=["last_tested_at", "last_test_ok", "updated_at"])
    log_audit(
        actor=actor,
        action="settings.payments.test_webhook",
        obj=obj,
        after={"ok": ok},
        request=request,
    )
    return obj
