from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", None) if request else None

    if response is None:
        return Response(
            {
                "code": "server_error",
                "message": "An unexpected error occurred.",
                "fields": {},
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    fields: dict[str, Any] = {}
    message = "Request failed."
    code = "error"

    data = response.data
    if isinstance(data, dict):
        if "detail" in data:
            message = str(data["detail"])
            code = getattr(data["detail"], "code", None) or code
            if hasattr(data["detail"], "code"):
                code = str(data["detail"].code)
        else:
            fields = {k: v for k, v in data.items() if k != "detail"}
            # flatten first message
            for key, val in fields.items():
                if isinstance(val, list) and val:
                    message = f"{key}: {val[0]}"
                    break
                if isinstance(val, str):
                    message = f"{key}: {val}"
                    break
    elif isinstance(data, list) and data:
        message = str(data[0])

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "unauthorized"
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        code = "forbidden"
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        code = "not_found"
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        code = "throttled"
    elif response.status_code >= 400:
        code = code if code != "error" else "validation_error"

    response.data = {
        "code": code,
        "message": message,
        "fields": fields if isinstance(fields, dict) else {},
        "request_id": request_id,
    }
    return response
