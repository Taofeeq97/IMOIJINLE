from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.programs.views import ClassSubjectDetailView, ClassViewSet, CohortViewSet, ProgramViewSet

router = DefaultRouter()
router.register(r"programs", ProgramViewSet, basename="program")
router.register(r"cohorts", CohortViewSet, basename="cohort")
router.register(r"classes", ClassViewSet, basename="class")

urlpatterns = [
    path(
        "classes/<uuid:class_id>/subjects/<uuid:class_subject_id>/",
        ClassSubjectDetailView.as_view(),
        name="class-subject-detail",
    ),
    path("", include(router.urls)),
]
