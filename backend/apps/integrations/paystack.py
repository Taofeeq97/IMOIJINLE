from __future__ import annotations

from typing import Any

import requests
from django.conf import settings

PAYSTACK_BASE = getattr(settings, "PAYSTACK_BASE_URL", None) or "https://api.paystack.co"


class PaystackError(Exception):
    def __init__(self, message: str, code: str = "paystack_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _secret() -> str:
    secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
    if not secret:
        # Fall back to org settings encrypted secret via payments services caller
        raise PaystackError(
            "Paystack secret key is not configured.",
            code="paystack_unconfigured",
        )
    return secret


def request(
    method: str, path: str, payload: dict | None = None, *, secret: str | None = None
) -> dict[str, Any]:
    key = secret or _secret()
    if not key:
        raise PaystackError("Paystack secret key is not configured.", code="paystack_unconfigured")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    url = f"{PAYSTACK_BASE.rstrip('/')}{path}"
    resp = requests.request(method, url, headers=headers, json=payload, timeout=30)
    try:
        data = resp.json()
    except ValueError as exc:
        raise PaystackError(
            f"Invalid Paystack response ({resp.status_code})", code="paystack_error"
        ) from exc
    if resp.status_code >= 400 or not data.get("status"):
        raise PaystackError(data.get("message") or "Paystack request failed", code="paystack_error")
    return data
