from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.admissions.models import Enrollment
from apps.certificates import services
from apps.certificates.models import (
    Certificate,
    CertificateIssueRule,
    CertificateTemplate,
)
from apps.certificates.serializers import (
    CertificateDesignSaveSerializer,
    CertificateIssueRuleSerializer,
    CertificateIssueRuleWriteSerializer,
    CertificateIssueSerializer,
    CertificatePreviewSerializer,
    CertificateRevokeSerializer,
    CertificateSerializer,
    CertificateTemplateCreateSerializer,
    CertificateTemplateSerializer,
    CertificateTemplateVersionSerializer,
)
from apps.courses.models import Subject
from apps.programs.models import Class


class VerifyThrottle(AnonRateThrottle):
    scope = "auth"


class CertificatesManagePermission(RolePermission):
    required_action = "certificates.manage"


class CertificateTemplateListCreateView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def get(self, request):
        qs = CertificateTemplate.objects.select_related("current_version").all()
        return Response(CertificateTemplateSerializer(qs, many=True).data)

    def post(self, request):
        ser = CertificateTemplateCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        template = services.create_template(
            name=ser.validated_data["name"],
            orientation=ser.validated_data.get("orientation") or "landscape",
            page_size=ser.validated_data.get("page_size") or "A4",
            design=ser.validated_data.get("design"),
            actor=request.user,
            request=request,
        )
        return Response(
            CertificateTemplateSerializer(template).data, status=status.HTTP_201_CREATED
        )


class CertificateTemplateDetailView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def get(self, request, template_id):
        try:
            template = CertificateTemplate.objects.select_related("current_version").get(
                id=template_id
            )
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = CertificateTemplateSerializer(template).data
        data["versions"] = CertificateTemplateVersionSerializer(
            template.versions.all()[:20], many=True
        ).data
        return Response(data)

    def patch(self, request, template_id):
        try:
            template = CertificateTemplate.objects.select_related("current_version").get(
                id=template_id
            )
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        name = request.data.get("name")
        if name:
            template.name = name
            template.save(update_fields=["name", "updated_at"])
        if "design" in request.data:
            ser = CertificateDesignSaveSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            services.save_design(
                template=template,
                design=ser.validated_data["design"],
                note=ser.validated_data.get("note") or "",
                actor=request.user,
                request=request,
            )
            template.refresh_from_db()
        return Response(CertificateTemplateSerializer(template).data)

    def delete(self, request, template_id):
        try:
            template = CertificateTemplate.objects.get(id=template_id)
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CertificateTemplatePreviewView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def post(self, request, template_id):
        try:
            template = CertificateTemplate.objects.select_related("current_version").get(
                id=template_id
            )
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = CertificatePreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = services.preview_template(
                template=template,
                design=ser.validated_data.get("design"),
                data_source=ser.validated_data.get("data_source") or "sample",
                enrollment_id=str(ser.validated_data["enrollment_id"])
                if ser.validated_data.get("enrollment_id")
                else None,
                subject_id=str(ser.validated_data["subject_id"])
                if ser.validated_data.get("subject_id")
                else None,
                actor=request.user,
                request=request,
            )
        except services.CertificateError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(result)


class CertificateTemplatePublishView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def post(self, request, template_id):
        try:
            template = CertificateTemplate.objects.select_related("current_version").get(
                id=template_id
            )
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            version = services.publish_template(
                template=template, actor=request.user, request=request
            )
        except services.CertificateError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template.refresh_from_db()
        return Response(
            {
                "template": CertificateTemplateSerializer(template).data,
                "version": CertificateTemplateVersionSerializer(version).data,
            }
        )


class CertificateIssueRuleListCreateView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def get(self, request):
        qs = CertificateIssueRule.objects.select_related(
            "template", "class_ref", "subject"
        ).all()
        return Response(CertificateIssueRuleSerializer(qs, many=True).data)

    def post(self, request):
        ser = CertificateIssueRuleWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            template = CertificateTemplate.objects.get(id=data["template"])
        except CertificateTemplate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Template not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        class_ref = None
        subject = None
        if data.get("class_ref"):
            try:
                class_ref = Class.objects.get(id=data["class_ref"])
            except Class.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "Class not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        if data.get("subject"):
            try:
                subject = Subject.objects.get(id=data["subject"])
            except Subject.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "Subject not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        if not class_ref and not subject:
            return Response(
                {
                    "code": "validation_error",
                    "message": "Provide class_ref or subject.",
                    "fields": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        rule = CertificateIssueRule.objects.create(
            name=data.get("name") or "",
            template=template,
            class_ref=class_ref,
            subject=subject,
            criteria=data.get("criteria") or {"min_completion_pct": 100},
            auto_issue=bool(data.get("auto_issue")),
            valid_for_days=data.get("valid_for_days"),
            numbering_pattern=data.get("numbering_pattern") or "IMO-{yyyy}-{seq:5}",
            is_active=data.get("is_active", True),
        )
        return Response(
            CertificateIssueRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class CertificateIssueRuleDetailView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def patch(self, request, rule_id):
        try:
            rule = CertificateIssueRule.objects.select_related(
                "template", "class_ref", "subject"
            ).get(id=rule_id)
        except CertificateIssueRule.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Rule not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        for field in (
            "name",
            "criteria",
            "auto_issue",
            "valid_for_days",
            "numbering_pattern",
            "is_active",
        ):
            if field in request.data:
                setattr(rule, field, request.data[field])
        rule.save()
        return Response(CertificateIssueRuleSerializer(rule).data)

    def delete(self, request, rule_id):
        CertificateIssueRule.objects.filter(id=rule_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CertificateIssueView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def post(self, request):
        ser = CertificateIssueSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            enrollment = Enrollment.objects.select_related(
                "user", "class_ref", "cohort", "cohort__program"
            ).get(id=data["enrollment_id"])
        except Enrollment.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Enrollment not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        rule = None
        template = None
        subject = None
        if data.get("rule_id"):
            try:
                rule = CertificateIssueRule.objects.select_related("template", "subject").get(
                    id=data["rule_id"]
                )
            except CertificateIssueRule.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "Rule not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        if data.get("template_id"):
            try:
                template = CertificateTemplate.objects.get(id=data["template_id"])
            except CertificateTemplate.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "Template not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        if data.get("subject_id"):
            try:
                subject = Subject.objects.get(id=data["subject_id"])
            except Subject.DoesNotExist:
                return Response(
                    {"code": "not_found", "message": "Subject not found.", "fields": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )
        try:
            cert = services.issue_certificate(
                enrollment=enrollment,
                rule=rule,
                template=template,
                subject=subject,
                actor=request.user,
                request=request,
                force=bool(data.get("force")),
            )
        except services.CertificateError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CertificateSerializer(cert).data, status=status.HTTP_201_CREATED)


class CertificateListView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def get(self, request):
        qs = Certificate.objects.select_related(
            "enrollment__user",
            "enrollment__class_ref",
            "subject",
            "template_version__template",
        ).all()[:200]
        return Response(CertificateSerializer(qs, many=True).data)


class CertificateRevokeView(APIView):
    permission_classes = [IsAuthenticated, CertificatesManagePermission]

    def post(self, request, certificate_id):
        try:
            cert = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Certificate not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ser = CertificateRevokeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cert = services.revoke_certificate(
            certificate=cert,
            reason=ser.validated_data.get("reason") or "",
            actor=request.user,
            request=request,
        )
        return Response(CertificateSerializer(cert).data)


class MeCertificatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Certificate.objects.filter(enrollment__user=request.user)
            .select_related(
                "enrollment__class_ref",
                "subject",
                "template_version__template",
            )
            .order_by("-issued_at")
        )
        return Response(CertificateSerializer(qs, many=True).data)


class PublicCertificateVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [VerifyThrottle]

    def get(self, request, code):
        try:
            payload = services.verify_certificate(code=code, request=request)
        except services.CertificateError as exc:
            return Response(
                {"code": exc.code, "message": exc.message, "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)
