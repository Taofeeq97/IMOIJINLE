from django.urls import path

from apps.search import views

urlpatterns = [
    path("search", views.UnifiedSearchView.as_view(), name="unified-search"),
    path("public/oidc/config", views.OIDCPublicConfigView.as_view(), name="oidc-public-config"),
    path("settings/oidc", views.OIDCAdminSettingsView.as_view(), name="oidc-admin-settings"),
]
