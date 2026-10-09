from django.urls import path

from apps.assessments import views

urlpatterns = [
    path("subtopics/<uuid:subtopic_id>/quiz/", views.SubtopicQuizView.as_view(), name="subtopic-quiz"),
    path("quizzes/<uuid:quiz_id>", views.QuizDetailView.as_view(), name="quiz-detail"),
    path(
        "quizzes/<uuid:quiz_id>/attempts",
        views.QuizAttemptsView.as_view(),
        name="quiz-attempts",
    ),
    path(
        "attempts/<uuid:attempt_id>/responses",
        views.AttemptResponsesView.as_view(),
        name="attempt-responses",
    ),
    path(
        "attempts/<uuid:attempt_id>/submit",
        views.AttemptSubmitView.as_view(),
        name="attempt-submit",
    ),
    path(
        "attempts/<uuid:attempt_id>/review",
        views.AttemptReviewView.as_view(),
        name="attempt-review",
    ),
    path(
        "subtopics/<uuid:subtopic_id>/assignment/",
        views.SubtopicAssignmentView.as_view(),
        name="subtopic-assignment",
    ),
    path(
        "assignments/<uuid:assignment_id>",
        views.AssignmentDetailView.as_view(),
        name="assignment-detail",
    ),
    path(
        "assignments/<uuid:assignment_id>/submissions",
        views.AssignmentSubmissionsView.as_view(),
        name="assignment-submissions",
    ),
    path("submissions/<uuid:submission_id>", views.SubmissionDetailView.as_view(), name="submission-detail"),
    path(
        "submissions/<uuid:submission_id>/grade",
        views.SubmissionGradeView.as_view(),
        name="submission-grade",
    ),
    path("grading/queue", views.GradingQueueView.as_view(), name="grading-queue"),
    path("grades/release", views.ReleaseGradesView.as_view(), name="grades-release"),
    path(
        "classes/<uuid:class_id>/gradebook",
        views.ClassGradebookView.as_view(),
        name="class-gradebook",
    ),
    path("me/grades", views.MyGradesView.as_view(), name="me-grades"),
]
