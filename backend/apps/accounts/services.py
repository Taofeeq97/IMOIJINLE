from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import MagicLinkToken, Profile, Role, User
from apps.accounts.policies import assign_role, user_permissions, user_roles_payload
from apps.audit.services import log_audit


class AuthError(Exception):
    def __init__(self, message: str, code: str = "auth_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def issue_tokens(user: User) -> tuple[str, str]:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_refresh_cookie(response, refresh: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
    )


def serialize_me(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "phone": user.phone,
        "locale": user.locale,
        "timezone": user.timezone,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "roles": user_roles_payload(user),
        "permissions": user_permissions(user),
        "is_staff": user.is_staff,
    }


def register_user(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    request=None,
) -> User:
    email = email.lower().strip()
    if User.objects.filter(email__iexact=email).exists():
        raise AuthError("Unable to register with that email.", code="registration_failed")
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    Profile.objects.get_or_create(user=user)
    assign_role(user=user, role=Role.APPLICANT, actor=None, request=request)
    log_audit(
        actor=user,
        action="auth.register",
        obj=user,
        after={"email": user.email},
        request=request,
    )
    return user


def login_user(*, email: str, password: str, request=None) -> tuple[User, str, str]:
    user = authenticate(
        request=request,
        username=email.lower().strip(),
        password=password,
    )
    if user is None:
        raise AuthError("Invalid email or password.", code="invalid_credentials")
    if not user.is_active:
        raise AuthError("Account is inactive.", code="inactive")
    access, refresh = issue_tokens(user)
    user.last_seen_at = timezone.now()
    user.save(update_fields=["last_seen_at"])
    log_audit(
        actor=user,
        action="auth.login",
        obj=user,
        after={"email": user.email},
        request=request,
    )
    return user, access, refresh


def refresh_tokens(*, refresh_raw: str, request=None) -> tuple[User, str, str]:
    try:
        old = RefreshToken(refresh_raw)
        user_id = old["user_id"]
        user = User.objects.get(id=user_id, is_active=True)
        old.blacklist()
    except Exception as exc:
        raise AuthError("Invalid or expired refresh token.", code="invalid_refresh") from exc
    access, refresh = issue_tokens(user)
    return user, access, refresh


def logout_user(*, refresh_raw: str | None, user: User | None, request=None) -> None:
    if refresh_raw:
        try:
            RefreshToken(refresh_raw).blacklist()
        except Exception:
            pass
    if user and user.is_authenticated:
        log_audit(actor=user, action="auth.logout", obj=user, request=request)


def request_password_reset(*, email: str, request=None) -> None:
    """Always succeed to avoid account enumeration."""
    try:
        user = User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset?uid={uid}&token={token}"
    send_mail(
        subject="Reset your Imo Ijinle Academy password",
        message=f"Reset your password: {link}\nIf you did not request this, ignore this email.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    log_audit(actor=user, action="auth.password_forgot", obj=user, request=request)


def reset_password(*, uidb64: str, token: str, new_password: str, request=None) -> User:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception as exc:
        raise AuthError("Invalid reset link.", code="invalid_reset") from exc
    if not default_token_generator.check_token(user, token):
        raise AuthError("Invalid or expired reset token.", code="invalid_reset")
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    log_audit(actor=user, action="auth.password_reset", obj=user, request=request)
    return user


def verify_email(*, uidb64: str, token: str, request=None) -> User:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception as exc:
        raise AuthError("Invalid verification link.", code="invalid_verify") from exc
    if not default_token_generator.check_token(user, token):
        raise AuthError("Invalid or expired verification token.", code="invalid_verify")
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at", "updated_at"])
    log_audit(actor=user, action="auth.verify_email", obj=user, request=request)
    return user


def send_magic_link(*, email: str, request=None) -> None:
    try:
        user = User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist:
        return
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    MagicLinkToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    link = f"{settings.FRONTEND_URL}/magic/{raw}"
    send_mail(
        subject="Your Imo Ijinle Academy sign-in link",
        message=f"Sign in: {link}\nThis link expires in 1 hour.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )
    log_audit(actor=user, action="auth.magic_link", obj=user, request=request)


def google_login_not_configured() -> None:
    raise AuthError(
        "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        code="google_not_configured",
    )
