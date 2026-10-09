from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.audit.services import log_audit
from apps.courses.models import Subject
from apps.programs import services
from apps.programs.models import Class, ClassSubject, Cohort, Program
from apps.programs.serializers import (
    AttachSubjectSerializer,
    ClassSerializer,
    ClassSubjectSerializer,
    CohortSerializer,
    ProgramSerializer,
    ReorderSerializer,
)


class ProgramsManagePermission(RolePermission):
    required_action = "programs.manage"


class ProgramViewSet(viewsets.ModelViewSet):
    """Deprecated. Cohort is the product root (academic session)."""

    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated, ProgramsManagePermission]
    lookup_field = "id"
    search_fields = ["title", "slug"]
    filterset_fields = ["status", "category"]
    http_method_names = ["get", "head", "options"]

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "code": "gone",
                "message": "Program is not part of the product model. Create a Cohort (academic session) instead.",
                "fields": {},
                "request_id": getattr(request, "request_id", None),
            },
            status=status.HTTP_410_GONE,
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="program.create",
            obj=obj,
            after=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        before = ProgramSerializer(serializer.instance).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="program.update",
            obj=obj,
            before=before,
            after=ProgramSerializer(obj).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="program.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        program = self.get_object()
        clone = Program.objects.create(
            title=f"{program.title} (copy)",
            summary=program.summary,
            description_rich=program.description_rich,
            status="draft",
            category=program.category,
            default_currency=program.default_currency,
        )
        log_audit(
            actor=request.user,
            action="program.duplicate",
            obj=clone,
            after={"source_id": str(program.id)},
            request=request,
        )
        return Response(ProgramSerializer(clone).data, status=status.HTTP_201_CREATED)


class CohortViewSet(viewsets.ModelViewSet):
    queryset = Cohort.objects.select_related("program").all()
    serializer_class = CohortSerializer
    permission_classes = [IsAuthenticated, ProgramsManagePermission]
    lookup_field = "id"
    search_fields = ["name", "slug"]
    filterset_fields = ["status", "program"]

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="cohort.create",
            obj=obj,
            after=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        before = CohortSerializer(serializer.instance).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="cohort.update",
            obj=obj,
            before=before,
            after=CohortSerializer(obj).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="cohort.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="open-applications")
    def open_applications(self, request, id=None):
        cohort = services.open_applications(
            cohort=self.get_object(), actor=request.user, request=request
        )
        return Response(CohortSerializer(cohort).data)

    @action(detail=True, methods=["post"], url_path="close-applications")
    def close_applications(self, request, id=None):
        cohort = services.close_applications(
            cohort=self.get_object(), actor=request.user, request=request
        )
        return Response(CohortSerializer(cohort).data)

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        clone = services.duplicate_cohort(
            cohort=self.get_object(), actor=request.user, request=request
        )
        return Response(CohortSerializer(clone).data, status=status.HTTP_201_CREATED)


class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.select_related("cohort").all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated, ProgramsManagePermission]
    lookup_field = "id"
    search_fields = ["name", "slug"]
    filterset_fields = ["status", "cohort"]

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="class.create",
            obj=obj,
            after=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        before = ClassSerializer(serializer.instance).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="class.update",
            obj=obj,
            before=before,
            after=ClassSerializer(obj).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="class.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, id=None):
        obj = services.publish_class(
            class_obj=self.get_object(), actor=request.user, request=request
        )
        return Response(ClassSerializer(obj).data)

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        clone = services.duplicate_class(
            class_obj=self.get_object(), actor=request.user, request=request
        )
        return Response(ClassSerializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="subjects")
    def subjects(self, request, id=None):
        class_obj = self.get_object()
        if request.method == "GET":
            qs = class_obj.class_subjects.select_related("subject").all()
            return Response(ClassSubjectSerializer(qs, many=True).data)
        ser = AttachSubjectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            subject = Subject.objects.get(id=ser.validated_data["subject_id"])
        except Subject.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Subject not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        link = services.attach_subject(
            class_obj=class_obj,
            subject=subject,
            mode=ser.validated_data["mode"],
            actor=request.user,
            request=request,
        )
        return Response(ClassSubjectSerializer(link).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="subjects/reorder")
    def reorder_subjects(self, request, id=None):
        class_obj = self.get_object()
        ser = ReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.reorder_items(
            queryset=class_obj.class_subjects.all(),
            ordered_ids=ser.validated_data["ordered_ids"],
        )
        log_audit(
            actor=request.user,
            action="class.reorder_subjects",
            obj=class_obj,
            after={"ordered_ids": [str(x) for x in ser.validated_data["ordered_ids"]]},
            request=request,
        )
        qs = class_obj.class_subjects.select_related("subject").all()
        return Response(ClassSubjectSerializer(qs, many=True).data)


class ClassSubjectDetailView(APIView):
    permission_classes = [IsAuthenticated, ProgramsManagePermission]

    def delete(self, request, class_id, class_subject_id):
        try:
            link = ClassSubject.objects.select_related("class_ref").get(
                id=class_subject_id, class_ref_id=class_id
            )
        except ClassSubject.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Link not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        log_audit(
            actor=request.user,
            action="class.detach_subject",
            obj=link,
            before={"id": str(link.id), "subject_id": str(link.subject_id)},
            request=request,
        )
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, class_id, class_subject_id):
        try:
            link = ClassSubject.objects.get(id=class_subject_id, class_ref_id=class_id)
        except ClassSubject.DoesNotExist:
            return Response(
                {
                    "code": "not_found",
                    "message": "Link not found.",
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        mode = request.data.get("mode")
        if mode:
            link.mode = mode
            link.save(update_fields=["mode", "updated_at"])
            log_audit(
                actor=request.user,
                action="class.update_subject_link",
                obj=link,
                after={"mode": mode},
                request=request,
            )
        return Response(ClassSubjectSerializer(link).data)
