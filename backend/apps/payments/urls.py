from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments import views

router = DefaultRouter()
router.register(r"fee-items", views.FeeItemViewSet, basename="fee-item")
router.register(r"fee-rules", views.FeeRuleViewSet, basename="fee-rule")
router.register(r"custom-charges", views.CustomChargeViewSet, basename="custom-charge")
router.register(r"invoices", views.InvoiceViewSet, basename="invoice")
router.register(r"refunds", views.RefundViewSet, basename="refund")
router.register(
    r"payment-notification-configs",
    views.PaymentNotificationConfigViewSet,
    basename="payment-notification-config",
)

urlpatterns = [
    path("webhooks/paystack", views.PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("payments/<str:reference>/status", views.PaymentStatusView.as_view(), name="payment-status"),
    path("me/invoices", views.MeInvoicesView.as_view(), name="me-invoices"),
    path("me/payments", views.MeInvoicesView.as_view(), name="me-payments"),
    path("access/explain", views.AccessExplainView.as_view(), name="access-explain"),
    path("finance/overview", views.FinanceOverviewView.as_view(), name="finance-overview"),
    path(
        "finance/attempts-vs-paid",
        views.FinanceAttemptsVsPaidView.as_view(),
        name="finance-attempts-vs-paid",
    ),
    path("finance/aging", views.FinanceAgingView.as_view(), name="finance-aging"),
    path("finance/outstanding", views.FinanceOutstandingView.as_view(), name="finance-outstanding"),
    path("", include(router.urls)),
]
