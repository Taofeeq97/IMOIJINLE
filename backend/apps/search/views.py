from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.policies import can
from apps.search.models import OIDCSettings, unified_search


class UnifiedSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(unified_search(q=request.query_params.get("q", ""), user=request.user))


class OIDCPublicConfigView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        s = OIDCSettings.get_solo()
        return Response(
            {
                "enabled": bool(s.enabled and s.issuer and s.client_id),
                "issuer": s.issuer if s.enabled else "",
                "client_id": s.client_id if s.enabled else "",
                "scopes": s.scopes,
                "redirect_path": s.redirect_path,
                "authorize_url": (
                    f"{s.issuer.rstrip('/')}/authorize" if s.enabled and s.issuer else None
                ),
                "note": "SSO/OIDC is Phase 4 — configure issuer/client to enable login redirect.",
            }
        )


class OIDCAdminSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can(request.user, "settings.manage"):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        s = OIDCSettings.get_solo()
        return Response(
            {
                "enabled": s.enabled,
                "issuer": s.issuer,
                "client_id": s.client_id,
                "has_secret": bool(s.client_secret_encrypted),
                "scopes": s.scopes,
                "redirect_path": s.redirect_path,
            }
        )

    def put(self, request):
        if not can(request.user, "settings.manage"):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        s = OIDCSettings.get_solo()
        s.enabled = bool(request.data.get("enabled", s.enabled))
        s.issuer = request.data.get("issuer", s.issuer) or ""
        s.client_id = request.data.get("client_id", s.client_id) or ""
        if request.data.get("client_secret"):
            from apps.orgsettings.payment_services import encrypt_secret

            s.client_secret_encrypted = encrypt_secret(request.data["client_secret"])
        s.scopes = request.data.get("scopes", s.scopes) or s.scopes
        s.redirect_path = request.data.get("redirect_path", s.redirect_path) or s.redirect_path
        s.save()
        return Response({"ok": True, "enabled": s.enabled})
