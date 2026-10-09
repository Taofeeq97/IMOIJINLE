from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.orgsettings import payment_services
from apps.orgsettings.models import ApplicationFeeSettings, BrandSettings, PaymentGatewaySettings
from apps.orgsettings.serializers import BrandSettingsSerializer


class BrandSettingsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        brand = BrandSettings.get_solo()
        return Response(BrandSettingsSerializer(brand).data)


class SettingsManagePermission(RolePermission):
    required_action = "settings.manage"


class PaymentGatewaySettingsView(APIView):
    permission_classes = [IsAuthenticated, SettingsManagePermission]

    def get(self, request):
        obj = PaymentGatewaySettings.get_solo()
        return Response(payment_services.gateway_public_payload(obj))

    def put(self, request):
        obj = payment_services.update_gateway(data=request.data, actor=request.user, request=request)
        return Response(payment_services.gateway_public_payload(obj))


class ApplicationFeeSettingsView(APIView):
    permission_classes = [IsAuthenticated, SettingsManagePermission]

    def get(self, request):
        obj = ApplicationFeeSettings.get_solo()
        return Response(payment_services.application_fee_payload(obj))

    def put(self, request):
        try:
            obj = payment_services.update_application_fees(
                data=request.data, actor=request.user, request=request
            )
        except ValueError as exc:
            return Response(
                {
                    "code": "validation_error",
                    "message": str(exc),
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payment_services.application_fee_payload(obj))


class PaymentTestWebhookView(APIView):
    permission_classes = [IsAuthenticated, SettingsManagePermission]

    def post(self, request):
        obj = PaymentGatewaySettings.get_solo()
        ok = bool(obj.public_key) and bool(obj.secret_key_encrypted)
        payment_services.mark_gateway_tested(ok=ok, actor=request.user, request=request)
        return Response(
            {
                "ok": ok,
                "message": "Test event recorded."
                if ok
                else "Keys missing — configure public and secret keys first.",
                "payload": {"event": "charge.success", "data": {"reference": "TEST_LOCAL"}},
            }
        )
