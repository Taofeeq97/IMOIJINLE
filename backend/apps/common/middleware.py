from __future__ import annotations

import uuid

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> None:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response):  # type: ignore[no-untyped-def]
        request_id = getattr(request, "request_id", None)
        if request_id:
            response[REQUEST_ID_HEADER] = request_id
        return response
