from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentConversionError(Exception):
    def __init__(self, message: str, code: str = "conversion_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def converter_base_url() -> str:
    return (getattr(settings, "DOCUMENT_CONVERTER_URL", "") or "").rstrip("/")


def ensure_converter_configured() -> None:
    if not converter_base_url():
        raise DocumentConversionError(
            "Document converter is not configured. Set DOCUMENT_CONVERTER_URL (Gotenberg).",
            code="converter_unconfigured",
        )


def convert_office_to_pdf(*, filename: str, data: bytes) -> bytes:
    """
    Convert Office/OpenDocument files to PDF via Gotenberg LibreOffice route.
    https://gotenberg.dev/docs/routes/convert-with-libreoffice
    """
    ensure_converter_configured()
    url = f"{converter_base_url()}/forms/libreoffice/convert"
    files = {"files": (filename, data)}
    resp = requests.post(url, files=files, timeout=120)
    if resp.status_code >= 400:
        raise DocumentConversionError(
            f"Gotenberg conversion failed ({resp.status_code}): {resp.text[:500]}",
            code="conversion_failed",
        )
    return resp.content


def convert_html_to_pdf(*, html: str, filename: str = "index.html") -> bytes:
    ensure_converter_configured()
    url = f"{converter_base_url()}/forms/chromium/convert/html"
    files = {"files": (filename, html.encode("utf-8"), "text/html")}
    resp = requests.post(url, files=files, timeout=120)
    if resp.status_code >= 400:
        raise DocumentConversionError(
            f"Gotenberg HTML conversion failed ({resp.status_code}): {resp.text[:500]}",
            code="conversion_failed",
        )
    return resp.content


def healthcheck() -> dict[str, Any]:
    ensure_converter_configured()
    resp = requests.get(f"{converter_base_url()}/health", timeout=10)
    return {"ok": resp.status_code == 200, "status_code": resp.status_code}
