from django.urls import path

from apps.learning import views

urlpatterns = [
    path("me/learning", views.MyLearningView.as_view(), name="me-learning"),
    path(
        "learn/subjects/<slug:slug>/landing",
        views.SubjectLandingView.as_view(),
        name="subject-landing",
    ),
    path(
        "learn/subjects/<uuid:subject_id>/outline",
        views.PlayerOutlineView.as_view(),
        name="player-outline",
    ),
    path(
        "learn/subjects/<uuid:subject_id>/qa",
        views.SubjectQAView.as_view(),
        name="subject-qa",
    ),
    path(
        "learn/questions/<uuid:question_id>/answers",
        views.QuestionAnswerView.as_view(),
        name="question-answer",
    ),
    path(
        "learn/subtopics/<uuid:subtopic_id>/viewer",
        views.SubtopicViewerView.as_view(),
        name="subtopic-viewer",
    ),
    path(
        "learn/subtopics/<uuid:subtopic_id>/heartbeat",
        views.SubtopicHeartbeatView.as_view(),
        name="subtopic-heartbeat",
    ),
    path(
        "learn/subtopics/<uuid:subtopic_id>/complete",
        views.SubtopicCompleteView.as_view(),
        name="subtopic-complete",
    ),
    path(
        "learn/subtopics/<uuid:subtopic_id>/video-progress",
        views.SubtopicVideoProgressView.as_view(),
        name="subtopic-video-progress",
    ),
    path(
        "learn/subtopics/<uuid:subtopic_id>/notes",
        views.SubtopicNotesView.as_view(),
        name="subtopic-notes",
    ),
    path("learn/notes/<uuid:note_id>", views.NoteDetailView.as_view(), name="note-detail"),
]
