from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from django.conf import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    def __init__(self, message: str, code: str = "storage_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def bucket_name() -> str:
    return settings.AWS_STORAGE_BUCKET_NAME


def ensure_storage_configured() -> None:
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        raise StorageError(
            "Object storage is not configured. Set MINIO_* / AWS_* credentials.",
            code="storage_unconfigured",
        )


def create_presigned_put(
    *,
    object_key: str,
    content_type: str,
    expires_in: int = 3600,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    ensure_storage_configured()
    params: dict[str, Any] = {
        "Bucket": bucket_name(),
        "Key": object_key,
        "ContentType": content_type or "application/octet-stream",
    }
    # Conditions for size are applied via browser Form POST; for PUT we return headers.
    url = _client().generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )
    # Rewrite localhost endpoint for browser if public endpoint configured
    public = getattr(settings, "AWS_S3_PUBLIC_ENDPOINT_URL", "") or ""
    if public:
        parsed_private = urlparse(settings.AWS_S3_ENDPOINT_URL or "")
        parsed_public = urlparse(public)
        if parsed_private.netloc and parsed_public.netloc:
            url = url.replace(parsed_private.netloc, parsed_public.netloc, 1)
            if parsed_public.scheme:
                url = parsed_public.scheme + "://" + url.split("://", 1)[-1]
    return {
        "upload_url": url,
        "method": "PUT",
        "headers": {"Content-Type": content_type or "application/octet-stream"},
        "object_key": object_key,
        "expires_in": expires_in,
        "max_bytes": max_bytes,
        "bucket": bucket_name(),
    }


def create_presigned_get(*, object_key: str, expires_in: int = 600) -> str:
    ensure_storage_configured()
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name(), "Key": object_key},
        ExpiresIn=expires_in,
    )


def head_object(*, object_key: str) -> dict[str, Any]:
    ensure_storage_configured()
    return _client().head_object(Bucket=bucket_name(), Key=object_key)


def object_exists(*, object_key: str) -> bool:
    try:
        head_object(object_key=object_key)
        return True
    except Exception:  # noqa: BLE001
        return False


def download_bytes(*, object_key: str) -> bytes:
    ensure_storage_configured()
    obj = _client().get_object(Bucket=bucket_name(), Key=object_key)
    return obj["Body"].read()


def upload_bytes(*, object_key: str, data: bytes, content_type: str) -> None:
    ensure_storage_configured()
    _client().put_object(
        Bucket=bucket_name(),
        Key=object_key,
        Body=data,
        ContentType=content_type,
    )


def delete_object(*, object_key: str) -> None:
    ensure_storage_configured()
    _client().delete_object(Bucket=bucket_name(), Key=object_key)
