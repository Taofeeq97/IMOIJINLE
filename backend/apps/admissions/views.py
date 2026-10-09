from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.accounts.services import issue_tokens, serialize_me, set_refresh_cookie
from apps.admissions import services
from apps.admissions.models import Application, Enrollment
from apps.admissions.serializers import (
    AdmitSerializer,
    ApplicationSerializer,
    BulkAdmitSerializer,
    ChangeEmailSerializer,
    EnrollmentSerializer,
    OnboardingSetPasswordSerializer,
    OnboardingVerifySerializer,
    PublicApplySerializer,
)
from apps.payments.services import PaymentError, initiate_payment
from apps.programs.models import Class, Cohort
from apps.programs.serializers import ClassSerializer, CohortSerializer


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class AdmissionsManagePermission(RolePermission):
    required_action = "admissions.manage"


class PublicCohortListView(APIView):
    """List cohorts that are open for applications or currently running."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        qs = Cohort.objects.filter(status__in=["applications_open", "running"]).order_by(
            "order", "-created_at"
        )
        return Response(
            {
                "count": qs.count(),
                "next": None,
                "previous": None,
                "results": CohortSerializer(qs, many=True).data,
            }
        )


class PublicCohortView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        try:
            cohort = Cohort.objects.get(slug=slug)
        except Cohort.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Cohort not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        classes = Class.objects.filter(cohort=cohort, status="published")
        from apps.admissions.services import resolve_application_fee_kobo

        data = CohortSerializer(cohort).data
        data["application_fee_kobo"] = resolve_application_fee_kobo(cohort)
        data["classes"] = ClassSerializer(classes, many=True).data
        return Response(data)


class PublicApplyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request, slug):
        ser = PublicApplySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            application, _token = services.submit_application(
                cohort_slug=slug,
                full_name=ser.validated_data["full_name"],
                email=ser.validated_data["email"],
                phone=ser.validated_data.get("phone") or "",
                data=ser.validated_data.get("data") or {},
                request=request,
            )
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "application_id": str(application.id),
                "email": application.applicant_email,
                "status": application.status,
                "message": f"Application received. We've sent a link to {application.applicant_email} to continue.",
            },
            status=status.HTTP_201_CREATED,
        )


class ResendOnboardingView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request, application_id):
        try:
            application = Application.objects.get(id=application_id)
            services.resend_onboarding(application=application, request=request)
        except Application.DoesNotExist:
            pass
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "If eligible, a new link was sent."})


class ChangeApplicationEmailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def patch(self, request, application_id):
        ser = ChangeEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            application = Application.objects.get(id=application_id)
            services.change_application_email(
                application=application, new_email=ser.validated_data["email"], request=request
            )
        except Application.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Application not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Email updated. Check your inbox for a new setup link."})


class OnboardingVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = OnboardingVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            application = services.verify_onboarding_token(
                token=ser.validated_data["token"],
                application_id=str(ser.validated_data["application_id"]),
            )
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "valid": True,
                "email": application.applicant_email,
                "name": application.applicant_name,
            }
        )


class OnboardingSetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = OnboardingSetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            user = services.set_password_from_onboarding(
                token=ser.validated_data["token"],
                application_id=str(ser.validated_data["application_id"]),
                password=ser.validated_data["password"],
                request=request,
            )
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        access, refresh = issue_tokens(user)
        resp = Response({"access": access, "user": serialize_me(user)})
        set_refresh_cookie(resp, refresh)
        return resp


class PortalApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Application.objects.filter(user=request.user).select_related("cohort", "fee_invoice")
        return Response(ApplicationSerializer(qs, many=True).data)


class PortalApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id):
        try:
            application = Application.objects.select_related("cohort", "fee_invoice").get(
                id=application_id, user=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ApplicationSerializer(application).data)


class PortalPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, application_id):
        try:
            application = Application.objects.select_related("fee_invoice").get(
                id=application_id, user=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        if not application.fee_invoice_id:
            return Response(
                {
                    "code": "no_fee",
                    "message": "No application fee due.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        idem = request.headers.get("Idempotency-Key", "")
        try:
            payment = initiate_payment(
                invoice=application.fee_invoice,
                user=request.user,
                idempotency_key=idem,
                actor=request.user,
                request=request,
            )
        except PaymentError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "reference": payment.reference,
                "authorization_url": payment.authorization_url,
                "access_code": payment.access_code,
                "public_key": __import__(
                    "apps.payments.services", fromlist=["_public_key"]
                )._public_key(),
                "amount_minor": payment.amount_minor,
                "currency": payment.currency,
            }
        )


class AdminApplicationsView(APIView):
    permission_classes = [IsAuthenticated, AdmissionsManagePermission]

    def get(self, request):
        qs = Application.objects.select_related("cohort", "fee_invoice", "user").all()
        status_filter = request.query_params.get("status")
        cohort = request.query_params.get("cohort")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if cohort:
            qs = qs.filter(cohort_id=cohort)
        return Response(ApplicationSerializer(qs[:200], many=True).data)


class AdminApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated, AdmissionsManagePermission]

    def get(self, request, application_id):
        try:
            application = Application.objects.select_related("cohort", "fee_invoice", "user").get(
                id=application_id
            )
        except Application.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ApplicationSerializer(application).data
        data["admissions"] = [
            {
                "class_id": str(a.class_ref_id),
                "class_name": a.class_ref.name,
                "admitted_at": a.admitted_at,
            }
            for a in application.admissions.select_related("class_ref")
        ]
        return Response(data)


class AdmitApplicationView(APIView):
    permission_classes = [IsAuthenticated, AdmissionsManagePermission]

    def post(self, request, application_id):
        ser = AdmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            application = Application.objects.select_related("cohort", "fee_invoice", "user").get(
                id=application_id
            )
            application = services.admit_application(
                application=application,
                class_ids=ser.validated_data["class_ids"],
                admitted_by=request.user,
                fee_handling=ser.validated_data.get("fee_handling", "generate"),
                notes=ser.validated_data.get("notes") or "",
                request=request,
            )
        except Application.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except services.AdmissionsError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ApplicationSerializer(application).data)


class BulkAdmitView(APIView):
    permission_classes = [IsAuthenticated, AdmissionsManagePermission]

    def post(self, request):
        ser = BulkAdmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        results = []
        for app_id in ser.validated_data["application_ids"]:
            try:
                application = Application.objects.select_related(
                    "cohort", "fee_invoice", "user"
                ).get(id=app_id)
                application = services.admit_application(
                    application=application,
                    class_ids=ser.validated_data["class_ids"],
                    admitted_by=request.user,
                    fee_handling=ser.validated_data.get("fee_handling", "generate"),
                    notes=ser.validated_data.get("notes") or "",
                    request=request,
                )
                results.append(
                    {"id": str(application.id), "ok": True, "status": application.status}
                )
            except Exception as exc:  # noqa: BLE001
                results.append({"id": str(app_id), "ok": False, "error": str(exc)})
        return Response({"results": results})


class MyLearningView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Enrollment.objects.filter(user=request.user).select_related("class_ref", "cohort")
        return Response(EnrollmentSerializer(qs, many=True).data)
