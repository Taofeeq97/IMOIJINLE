from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Prefer Authorization header; fall back unused — refresh stays cookie-only."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            # Access tokens are expected in Authorization: Bearer — not cookies.
            return None
        return super().authenticate(request)


def get_refresh_from_request(request) -> str | None:
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
