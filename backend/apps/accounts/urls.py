from django.urls import path

from apps.accounts import views
from apps.admissions.views import OnboardingSetPasswordView, OnboardingVerifyView

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="auth-register"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("refresh", views.RefreshView.as_view(), name="auth-refresh"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("password/forgot", views.PasswordForgotView.as_view(), name="auth-password-forgot"),
    path("password/reset", views.PasswordResetView.as_view(), name="auth-password-reset"),
    path("verify-email", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("magic-link", views.MagicLinkView.as_view(), name="auth-magic-link"),
    path("google", views.GoogleAuthView.as_view(), name="auth-google"),
    path("onboarding/verify", OnboardingVerifyView.as_view(), name="auth-onboarding-verify"),
    path(
        "onboarding/set-password",
        OnboardingSetPasswordView.as_view(),
        name="auth-onboarding-set-password",
    ),
]
