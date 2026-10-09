from django.urls import path

from apps.orgsettings.views import (
    ApplicationFeeSettingsView,
    BrandSettingsView,
    PaymentGatewaySettingsView,
    PaymentTestWebhookView,
)

urlpatterns = [
    path("brand/", BrandSettingsView.as_view(), name="settings-brand"),
    path("payments/gateway", PaymentGatewaySettingsView.as_view(), name="settings-payments-gateway"),
    path(
        "payments/application-fees",
        ApplicationFeeSettingsView.as_view(),
        name="settings-payments-application-fees",
    ),
    path("payments/test-webhook", PaymentTestWebhookView.as_view(), name="settings-payments-test-webhook"),
]
