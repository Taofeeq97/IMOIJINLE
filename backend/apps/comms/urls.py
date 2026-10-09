from django.urls import path

from apps.comms import views

urlpatterns = [
    path("announcements", views.AnnouncementListCreateView.as_view(), name="announcements"),
    path(
        "announcements/<uuid:announcement_id>",
        views.AnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
    path("me/notifications", views.MyNotificationsView.as_view(), name="my-notifications"),
    path(
        "me/notifications/<uuid:notification_id>/read",
        views.NotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "me/notification-preferences",
        views.NotificationPrefsView.as_view(),
        name="notification-prefs",
    ),
    path("analytics/overview", views.AnalyticsOverviewView.as_view(), name="analytics-overview"),
]
