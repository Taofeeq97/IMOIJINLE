from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.courses import views

router = DefaultRouter()
router.register(r"subjects", views.SubjectViewSet, basename="subject")
router.register(r"topics", views.TopicViewSet, basename="topic")
router.register(r"subtopics", views.SubtopicViewSet, basename="subtopic")

urlpatterns = [
    path("uploads/presign", views.UploadPresignView.as_view(), name="uploads-presign"),
    path(
        "uploads/<uuid:upload_id>/complete",
        views.UploadCompleteView.as_view(),
        name="uploads-complete",
    ),
    path(
        "subtopics/<uuid:subtopic_id>/mux-upload",
        views.MuxDirectUploadView.as_view(),
        name="subtopic-mux-upload",
    ),
    path("webhooks/mux", views.MuxWebhookView.as_view(), name="mux-webhook"),
    path(
        "videos/<uuid:video_asset_id>/playback-token",
        views.VideoPlaybackTokenView.as_view(),
        name="video-playback-token",
    ),
    path(
        "resources/<uuid:resource_id>", views.ResourceDeleteView.as_view(), name="resource-delete"
    ),
    path(
        "public/subjects/<uuid:subject_id>/preview",
        views.PublicPreviewView.as_view(),
        name="subject-public-preview",
    ),
    path("", include(router.urls)),
]
