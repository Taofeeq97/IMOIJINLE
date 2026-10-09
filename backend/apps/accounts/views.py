from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.serializers import (
    GoogleAuthSerializer,
    LoginSerializer,
    MagicLinkSerializer,
    PasswordForgotSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    VerifyEmailSerializer,
)


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            user = services.register_user(request=request, **ser.validated_data)
        except services.AuthError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        access, refresh = services.issue_tokens(user)
        resp = Response(
            {"access": access, "user": services.serialize_me(user)},
            status=status.HTTP_201_CREATED,
        )
        services.set_refresh_cookie(resp, refresh)
        return resp


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            user, access, refresh = services.login_user(
                email=ser.validated_data["email"],
                password=ser.validated_data["password"],
                request=request,
            )
        except services.AuthError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        resp = Response({"access": access, "user": services.serialize_me(user)})
        services.set_refresh_cookie(resp, refresh)
        return resp


class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or request.data.get("refresh")
        if not raw:
            return Response(
                {
                    "code": "invalid_refresh",
                    "message": "Refresh token missing.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            user, access, refresh = services.refresh_tokens(refresh_raw=raw, request=request)
        except services.AuthError as exc:
            resp = Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
            services.clear_refresh_cookie(resp)
            return resp
        resp = Response({"access": access, "user": services.serialize_me(user)})
        services.set_refresh_cookie(resp, refresh)
        return resp


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or request.data.get("refresh")
        user = request.user if request.user.is_authenticated else None
        services.logout_user(refresh_raw=raw, user=user, request=request)
        resp = Response({"detail": "Logged out."})
        services.clear_refresh_cookie(resp)
        return resp


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.serialize_me(request.user))


class PasswordForgotView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = PasswordForgotSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.request_password_reset(email=ser.validated_data["email"], request=request)
        return Response({"detail": "If that email exists, a reset link was sent."})


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = PasswordResetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.reset_password(
                uidb64=ser.validated_data["uid"],
                token=ser.validated_data["token"],
                new_password=ser.validated_data["password"],
                request=request,
            )
        except services.AuthError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Password updated."})


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = VerifyEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.verify_email(
                uidb64=ser.validated_data["uid"],
                token=ser.validated_data["token"],
                request=request,
            )
        except services.AuthError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Email verified."})


class MagicLinkView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = MagicLinkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.send_magic_link(email=ser.validated_data["email"], request=request)
        return Response({"detail": "If that email exists, a magic link was sent."})


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        ser = GoogleAuthSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]:
            return Response(
                {
                    "code": "google_not_configured",
                    "message": "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        # Full Google token verification lands when credentials are present (M8 hardening / when secrets available).
        return Response(
            {
                "code": "google_not_implemented",
                "message": "Google client is configured but token verification requires live credentials verification path.",
                "fields": {},
                "request_id": getattr(request, "request_id", None),
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
