"""Shared HTTP stubs for external providers in unit/API tests (not product mocks)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture
def stub_paystack():
    def _request(method, path, payload=None, *, secret=None):
        if path == "/transaction/initialize":
            ref = (payload or {}).get("reference") or "IMO-TEST"
            return {
                "status": True,
                "data": {
                    "authorization_url": f"https://checkout.paystack.com/test/{ref}",
                    "access_code": "access_test",
                    "reference": ref,
                },
            }
        if path.startswith("/transaction/verify/"):
            ref = path.rsplit("/", 1)[-1]
            from apps.payments.models import Payment

            amt = 500000
            cur = "NGN"
            p = Payment.objects.filter(reference=ref).first()
            if p:
                amt = p.amount_minor
                cur = p.currency
            return {
                "status": True,
                "data": {
                    "status": "success",
                    "reference": ref,
                    "amount": amt,
                    "currency": cur,
                    "id": 12345,
                    "channel": "card",
                    "fees": 0,
                },
            }
        if path == "/refund":
            return {"status": True, "data": {"id": "rf_test", "status": "processed"}}
        return {"status": True, "data": {}}

    with patch("apps.integrations.paystack.request", side_effect=_request):
        with patch("apps.payments.services._secret_key", return_value="sk_test_fixture"):
            with patch("apps.payments.services._public_key", return_value="pk_test_fixture"):
                yield


@pytest.fixture
def stub_storage():
    store: dict[str, bytes] = {}

    def put(*, object_key, content_type, expires_in=3600, max_bytes=None):
        return {
            "upload_url": f"https://storage.test/{object_key}",
            "method": "PUT",
            "headers": {"Content-Type": content_type},
            "object_key": object_key,
            "expires_in": expires_in,
            "max_bytes": max_bytes,
            "bucket": "test",
        }

    def head(*, object_key):
        if object_key not in store:
            # Treat as uploaded for test complete flow after we mark it
            store[object_key] = b"x"
        return {
            "ContentLength": len(store[object_key]),
            "ContentType": "application/octet-stream",
            "ETag": '"x"',
        }

    def download(*, object_key):
        return store.get(object_key, b"%PDF-1.4")

    def upload(*, object_key, data, content_type):
        store[object_key] = data

    with patch("apps.integrations.storage.create_presigned_put", side_effect=put):
        with patch("apps.integrations.storage.head_object", side_effect=head):
            with patch("apps.integrations.storage.download_bytes", side_effect=download):
                with patch("apps.integrations.storage.upload_bytes", side_effect=upload):
                    with patch("apps.integrations.storage.ensure_storage_configured"):
                        yield store


@pytest.fixture
def stub_mux():
    with patch(
        "apps.integrations.mux.create_direct_upload",
        return_value={
            "id": "upload_test",
            "url": "https://upload.mux.com/test",
            "status": "waiting",
        },
    ):
        with patch(
            "apps.integrations.mux.get_asset",
            return_value={"status": "ready", "playback_ids": [{"id": "play_test"}], "duration": 12},
        ):
            yield


@pytest.fixture
def stub_documents():
    with patch(
        "apps.integrations.documents.convert_office_to_pdf", return_value=b"%PDF-1.4 converted"
    ):
        with patch("apps.integrations.documents.ensure_converter_configured"):
            yield
