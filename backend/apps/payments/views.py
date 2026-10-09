from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.accounts.policies import can
from apps.payments.models import (
    CustomCharge,
    FeeItem,
    FeeRule,
    Invoice,
    Payment,
    PaymentNotificationConfig,
    Refund,
)
from apps.payments.serializers import (
    CustomChargeCreateSerializer,
    CustomChargeSerializer,
    FeeItemSerializer,
    FeeRuleSerializer,
    InvoicePaySerializer,
    InvoiceSerializer,
    PaymentNotificationConfigSerializer,
    PaymentSerializer,
    RefundCreateSerializer,
    RefundSerializer,
)
from apps.payments.services import (
    PaymentError,
    create_custom_charge,
    explain_access,
    finance_aging,
    finance_attempts_vs_paid,
    finance_outstanding,
    finance_overview,
    initiate_payment,
    persist_webhook_event,
    preview_custom_charge,
    process_webhook_event,
    request_refund,
    settle_payment,
)


class FinanceManagePermission(RolePermission):
    required_action = "finance.manage"


class FinanceViewPermission(RolePermission):
    required_action = "finance.view_all"


class PaystackWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.body
        signature = request.headers.get("X-Paystack-Signature") or request.META.get(
            "HTTP_X_PAYSTACK_SIGNATURE"
        )
        event = persist_webhook_event(raw_body=raw, signature=signature)
        if not event.signature_valid:
            return Response({"detail": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            process_webhook_event(event)
        except PaymentError as exc:
            return Response(
                {"code": exc.code, "message": exc.message}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"status": "ok"})


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            payment = Payment.objects.select_related("invoice").get(
                reference=reference, user=request.user
            )
        except Payment.DoesNotExist:
            if can(request.user, "finance.view_all") or can(request.user, "finance.manage"):
                try:
                    payment = Payment.objects.select_related("invoice").get(reference=reference)
                except Payment.DoesNotExist:
                    payment = None
            else:
                payment = None
        if payment is None:
            return Response(
                {
                    "code": "not_found",
                    "message": "Payment not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        if payment.status != "success":
            try:
                payment = settle_payment(reference=reference, actor=request.user, request=request)
            except PaymentError:
                payment.refresh_from_db()
        return Response(
            {
                "reference": payment.reference,
                "status": payment.status,
                "amount_minor": payment.amount_minor,
                "currency": payment.currency,
                "invoice_status": payment.invoice.status,
                "paid_at": payment.paid_at,
                "authorization_url": payment.authorization_url,
                "access_code": payment.access_code,
            }
        )


class FeeItemViewSet(viewsets.ModelViewSet):
    queryset = FeeItem.objects.all()
    serializer_class = FeeItemSerializer
    permission_classes = [IsAuthenticated, FinanceManagePermission]
    lookup_field = "id"
    search_fields = ["name", "code"]
    filterset_fields = ["kind", "active", "currency"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), FinanceViewPermission()]
        return super().get_permissions()


class FeeRuleViewSet(viewsets.ModelViewSet):
    queryset = FeeRule.objects.select_related("fee_item").all()
    serializer_class = FeeRuleSerializer
    permission_classes = [IsAuthenticated, FinanceManagePermission]
    lookup_field = "id"
    filterset_fields = ["scope_type", "active", "mode", "billing", "fee_item"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), FinanceViewPermission()]
        return super().get_permissions()


class CustomChargeViewSet(viewsets.ModelViewSet):
    queryset = CustomCharge.objects.all()
    serializer_class = CustomChargeSerializer
    permission_classes = [IsAuthenticated, FinanceManagePermission]
    lookup_field = "id"
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), FinanceViewPermission()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        preview = str(request.query_params.get("preview", "")).lower() in {"1", "true", "yes"}
        ser = CustomChargeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if preview:
            result = preview_custom_charge(
                target_type=data["target_type"],
                target_ids=data["target_ids"],
                amount_minor=data["amount_minor"],
            )
            return Response(result)

        fee_item = None
        if data.get("fee_item"):
            fee_item = FeeItem.objects.filter(id=data["fee_item"]).first()

        charge, invoices = create_custom_charge(
            title=data["title"],
            description=data.get("description") or "",
            amount_minor=data["amount_minor"],
            currency=data.get("currency") or "NGN",
            target_type=data["target_type"],
            target_ids=data["target_ids"],
            mandatory=data.get("mandatory", True),
            due_at=data.get("due_at"),
            gate_rule=data.get("gate_rule") or {},
            created_by=request.user,
            notify=data.get("notify", True),
            fee_item=fee_item,
            request=request,
        )
        out = CustomChargeSerializer(charge).data
        out["invoice_count"] = len(invoices)
        out["invoice_ids"] = [str(i.id) for i in invoices]
        return Response(out, status=status.HTTP_201_CREATED)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    filterset_fields = ["status", "kind", "source", "currency"]

    def get_queryset(self):
        qs = Invoice.objects.select_related("user", "fee_item", "custom_charge").prefetch_related(
            "lines"
        )
        if can(self.request.user, "finance.view_all") or can(self.request.user, "finance.manage"):
            user_id = self.request.query_params.get("user_id")
            if user_id:
                qs = qs.filter(user_id=user_id)
            return qs
        return qs.filter(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, id=None):
        invoice = self.get_object()
        if invoice.user_id != request.user.id:
            return Response(
                {"code": "forbidden", "message": "Only the invoice owner can pay.", "fields": {}},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = InvoicePaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        idem = (
            request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY") or ""
        )
        try:
            payment = initiate_payment(
                invoice=invoice,
                user=request.user,
                idempotency_key=idem,
                callback_url=ser.validated_data.get("callback_url"),
                actor=request.user,
                request=request,
            )
        except PaymentError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "reference": payment.reference,
                "authorization_url": payment.authorization_url,
                "access_code": payment.access_code,
                "amount_minor": payment.amount_minor,
                "currency": payment.currency,
                "status": payment.status,
                "payment": PaymentSerializer(payment).data,
            }
        )


class MeInvoicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Invoice.objects.filter(user=request.user)
            .prefetch_related("lines")
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(InvoiceSerializer(qs, many=True).data)


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.select_related("payment", "requested_by").all()
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated, FinanceManagePermission]
    lookup_field = "id"
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), FinanceViewPermission()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = RefundCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            payment = Payment.objects.get(id=ser.validated_data["payment_id"])
        except Payment.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Payment not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            refund = request_refund(
                payment=payment,
                amount_minor=ser.validated_data.get("amount_minor"),
                reason=ser.validated_data.get("reason") or "",
                requested_by=request.user,
                request=request,
            )
        except PaymentError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)


class FinanceOverviewView(APIView):
    permission_classes = [IsAuthenticated, FinanceViewPermission]

    def get(self, request):
        currency = request.query_params.get("currency") or "NGN"
        return Response(finance_overview(currency=currency))


class FinanceAttemptsVsPaidView(APIView):
    permission_classes = [IsAuthenticated, FinanceViewPermission]

    def get(self, request):
        return Response(finance_attempts_vs_paid())


class FinanceAgingView(APIView):
    permission_classes = [IsAuthenticated, FinanceViewPermission]

    def get(self, request):
        return Response(finance_aging())


class FinanceOutstandingView(APIView):
    permission_classes = [IsAuthenticated, FinanceViewPermission]

    def get(self, request):
        limit = int(request.query_params.get("limit") or 100)
        return Response({"results": finance_outstanding(limit=limit)})


class AccessExplainView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        class_id = request.query_params.get("class_id")
        subject_id = request.query_params.get("subject_id")
        if not class_id and not subject_id:
            return Response(
                {
                    "code": "validation_error",
                    "message": "Provide class_id and/or subject_id.",
                    "fields": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user_id = request.query_params.get("user_id")
        if user_id and (
            can(request.user, "finance.view_all") or can(request.user, "finance.manage")
        ):
            from apps.accounts.models import User

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "User not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        return Response(explain_access(user=user, class_id=class_id, subject_id=subject_id))


class PaymentNotificationConfigViewSet(viewsets.ModelViewSet):
    queryset = PaymentNotificationConfig.objects.all()
    serializer_class = PaymentNotificationConfigSerializer
    permission_classes = [IsAuthenticated, FinanceManagePermission]
    lookup_field = "id"
    filterset_fields = ["event", "scope_type", "enabled"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated(), FinanceViewPermission()]
        return super().get_permissions()
