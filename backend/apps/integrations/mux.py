from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MUX_API = "https://api.mux.com"


class MuxError(Exception):
    def __init__(self, message: str, code: str = "mux_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _credentials() -> tuple[str, str]:
    token_id = getattr(settings, "MUX_TOKEN_ID", "") or ""
    token_secret = getattr(settings, "MUX_TOKEN_SECRET", "") or ""
    if not token_id or not token_secret:
        raise MuxError(
            "Mux is not configured. Set MUX_TOKEN_ID and MUX_TOKEN_SECRET.",
            code="mux_unconfigured",
        )
    return token_id, token_secret


def _auth_header() -> dict[str, str]:
    token_id, token_secret = _credentials()
    raw = f"{token_id}:{token_secret}".encode()
    return {
        "Authorization": "Basic " + base64.b64encode(raw).decode(),
        "Content-Type": "application/json",
    }


def create_direct_upload(
    *,
    cors_origin: str,
    passthrough: str = "",
    new_asset_settings: dict | None = None,
) -> dict[str, Any]:
    """Create a Mux Direct Upload. Client PUTs the video file to upload_url."""
    payload = {
        "cors_origin": cors_origin,
        "new_asset_settings": new_asset_settings
        or {
            "playback_policy": ["signed"]
            if getattr(settings, "MUX_PLAYBACK_POLICY", "signed") == "signed"
            else ["public"],
            "mp4_support": "standard",
        },
    }
    if passthrough:
        payload["new_asset_settings"]["passthrough"] = passthrough
    resp = requests.post(
        f"{MUX_API}/video/v1/uploads",
        headers=_auth_header(),
        json=payload,
        timeout=30,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise MuxError(
            data.get("error", {}).get("messages", [resp.text])[0]
            if isinstance(data.get("error"), dict)
            else (resp.text or "Mux upload create failed")
        )
    return data.get("data") or {}


def get_upload(upload_id: str) -> dict[str, Any]:
    resp = requests.get(
        f"{MUX_API}/video/v1/uploads/{upload_id}", headers=_auth_header(), timeout=30
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise MuxError(resp.text or "Mux get upload failed")
    return data.get("data") or {}


def get_asset(asset_id: str) -> dict[str, Any]:
    resp = requests.get(f"{MUX_API}/video/v1/assets/{asset_id}", headers=_auth_header(), timeout=30)
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise MuxError(resp.text or "Mux get asset failed")
    return data.get("data") or {}


def create_asset_from_url(*, input_url: str, passthrough: str = "") -> dict[str, Any]:
    policy = (
        ["signed"] if getattr(settings, "MUX_PLAYBACK_POLICY", "signed") == "signed" else ["public"]
    )
    payload: dict[str, Any] = {
        "input": [{"url": input_url}],
        "playback_policy": policy,
        "mp4_support": "standard",
    }
    if passthrough:
        payload["passthrough"] = passthrough
    resp = requests.post(
        f"{MUX_API}/video/v1/assets", headers=_auth_header(), json=payload, timeout=30
    )
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise MuxError(resp.text or "Mux create asset failed")
    return data.get("data") or {}


def verify_webhook_signature(*, raw_body: bytes, signature_header: str | None) -> bool:
    """
    Verify Mux webhook signature.
    Header format: t=<timestamp>,v1=<signature>
    """
    secret = getattr(settings, "MUX_WEBHOOK_SECRET", "") or ""
    if not secret:
        # If no webhook secret configured, reject in production-minded mode
        if not getattr(settings, "DEBUG", False):
            return False
        logger.warning("MUX_WEBHOOK_SECRET unset; accepting webhook only because DEBUG=True")
        return True
    if not signature_header:
        return False
    parts = dict(p.split("=", 1) for p in signature_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > 300:
        return False
    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode()
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def sign_playback_id(playback_id: str, *, expires_in: int = 3600) -> str:
    """
    Return a signed Mux JWT for playback when MUX_SIGNING_KEY_ID + private key are set.
    For public playback policy, returns the bare playback_id (caller uses unsigned stream).
    """
    key_id = getattr(settings, "MUX_SIGNING_KEY_ID", "") or ""
    private_key = getattr(settings, "MUX_SIGNING_PRIVATE_KEY", "") or ""
    if getattr(settings, "MUX_PLAYBACK_POLICY", "signed") != "signed":
        return playback_id
    if not key_id or not private_key:
        raise MuxError(
            "Signed playback requires MUX_SIGNING_KEY_ID and MUX_SIGNING_PRIVATE_KEY.",
            code="mux_signing_unconfigured",
        )
    try:
        import jwt  # PyJWT
    except ImportError as exc:
        raise MuxError("PyJWT is required for Mux signed playback.", code="dependency") from exc

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": playback_id,
            "aud": "v",
            "exp": now + expires_in,
            "kid": key_id,
        },
        private_key.replace("\\n", "\n"),
        algorithm="RS256",
        headers={"kid": key_id},
    )
    return token if isinstance(token, str) else token.decode()


def parse_webhook(raw_body: bytes) -> dict[str, Any]:
    return json.loads(raw_body.decode("utf-8"))
