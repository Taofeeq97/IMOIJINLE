from __future__ import annotations

import json
import uuid
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder

from apps.audit.models import AuditLog


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def log_audit(
    *,
    action: str,
    actor=None,
    obj=None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request=None,
) -> AuditLog:
    content_type = None
    object_id = None
    object_repr = ""
    if obj is not None:
        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        pk = getattr(obj, "pk", None)
        object_id = pk if isinstance(pk, uuid.UUID) else None
        object_repr = str(obj)[:255]

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        content_type=content_type,
        object_id=object_id,
        object_repr=object_repr,
        before=_json_safe(before),
        after=_json_safe(after),
        ip=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:1000] if request else ""),
        request_id=getattr(request, "request_id", "") if request else "",
    )
