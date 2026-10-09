from django.urls import path

from apps.admissions import views

urlpatterns = [
    path("public/cohorts/", views.PublicCohortListView.as_view(), name="public-cohorts"),
    path("public/cohorts/<slug:slug>/", views.PublicCohortView.as_view(), name="public-cohort"),
    path("public/applications/<slug:slug>/", views.PublicApplyView.as_view(), name="public-apply"),
    path(
        "public/applications/by-id/<uuid:application_id>/resend-onboarding",
        views.ResendOnboardingView.as_view(),
        name="public-resend-onboarding",
    ),
    path(
        "public/applications/by-id/<uuid:application_id>/email",
        views.ChangeApplicationEmailView.as_view(),
        name="public-change-email",
    ),
    path("portal/applications", views.PortalApplicationsView.as_view(), name="portal-applications"),
    path(
        "portal/applications/<uuid:application_id>",
        views.PortalApplicationDetailView.as_view(),
        name="portal-application-detail",
    ),
    path(
        "portal/applications/<uuid:application_id>/pay",
        views.PortalPayView.as_view(),
        name="portal-pay",
    ),
    path("applications", views.AdminApplicationsView.as_view(), name="admin-applications"),
    path(
        "applications/<uuid:application_id>",
        views.AdminApplicationDetailView.as_view(),
        name="admin-application-detail",
    ),
    path(
        "applications/<uuid:application_id>/admit",
        views.AdmitApplicationView.as_view(),
        name="admin-admit",
    ),
    path("applications/bulk-admit", views.BulkAdmitView.as_view(), name="admin-bulk-admit"),
]
