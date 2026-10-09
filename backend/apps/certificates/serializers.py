from rest_framework import serializers

from apps.certificates.models import (
    Certificate,
    CertificateIssueRule,
    CertificateTemplate,
    CertificateTemplateVersion,
)


class CertificateTemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTemplateVersion
        fields = [
            "id",
            "version_no",
            "design",
            "note",
            "is_published",
            "created_at",
            "created_by",
        ]
        read_only_fields = fields


class CertificateTemplateSerializer(serializers.ModelSerializer):
    current_version_no = serializers.SerializerMethodField()
    current_design = serializers.SerializerMethodField()

    class Meta:
        model = CertificateTemplate
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "orientation",
            "page_size",
            "page_custom",
            "current_version",
            "current_version_no",
            "current_design",
            "last_previewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "current_version",
            "current_version_no",
            "current_design",
            "last_previewed_at",
            "created_at",
            "updated_at",
        ]

    def get_current_version_no(self, obj: CertificateTemplate) -> int | None:
        return obj.current_version.version_no if obj.current_version_id else None

    def get_current_design(self, obj: CertificateTemplate) -> dict | None:
        return obj.current_version.design if obj.current_version_id else None


class CertificateTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    orientation = serializers.ChoiceField(
        choices=["landscape", "portrait"], required=False, default="landscape"
    )
    page_size = serializers.ChoiceField(
        choices=["A4", "Letter", "custom"], required=False, default="A4"
    )
    design = serializers.JSONField(required=False)


class CertificateDesignSaveSerializer(serializers.Serializer):
    design = serializers.JSONField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CertificatePreviewSerializer(serializers.Serializer):
    design = serializers.JSONField(required=False)
    data_source = serializers.ChoiceField(
        choices=["sample", "enrollment"], required=False, default="sample"
    )
    enrollment_id = serializers.UUIDField(required=False)
    subject_id = serializers.UUIDField(required=False)


class CertificateIssueRuleSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    class_name = serializers.CharField(source="class_ref.name", read_only=True, default=None)
    subject_title = serializers.CharField(source="subject.title", read_only=True, default=None)

    class Meta:
        model = CertificateIssueRule
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "class_ref",
            "class_name",
            "subject",
            "subject_title",
            "criteria",
            "auto_issue",
            "valid_for_days",
            "numbering_pattern",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "template_name",
            "class_name",
            "subject_title",
        ]


class CertificateIssueRuleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    template = serializers.UUIDField()
    class_ref = serializers.UUIDField(required=False, allow_null=True)
    subject = serializers.UUIDField(required=False, allow_null=True)
    criteria = serializers.JSONField(required=False, default=dict)
    auto_issue = serializers.BooleanField(required=False, default=False)
    valid_for_days = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    numbering_pattern = serializers.CharField(required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(required=False, default=True)


class CertificateIssueSerializer(serializers.Serializer):
    enrollment_id = serializers.UUIDField()
    rule_id = serializers.UUIDField(required=False)
    template_id = serializers.UUIDField(required=False)
    subject_id = serializers.UUIDField(required=False)
    force = serializers.BooleanField(required=False, default=False)


class CertificateRevokeSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CertificateSerializer(serializers.ModelSerializer):
    holder_name = serializers.SerializerMethodField()
    class_title = serializers.SerializerMethodField()
    subject_title = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    verify_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "id",
            "code",
            "enrollment",
            "template_version",
            "issue_rule",
            "subject",
            "issued_at",
            "issued_by",
            "status",
            "revoked_reason",
            "revoked_at",
            "expires_at",
            "data_snapshot",
            "holder_name",
            "class_title",
            "subject_title",
            "template_name",
            "verify_url",
        ]
        read_only_fields = fields

    def get_holder_name(self, obj: Certificate) -> str:
        snap = obj.data_snapshot or {}
        return (snap.get("student") or {}).get("full_name") or ""

    def get_class_title(self, obj: Certificate) -> str:
        snap = obj.data_snapshot or {}
        return (snap.get("class") or {}).get("title") or obj.enrollment.class_ref.name

    def get_subject_title(self, obj: Certificate) -> str:
        snap = obj.data_snapshot or {}
        return (snap.get("subject") or {}).get("title") or (
            obj.subject.title if obj.subject_id else ""
        )

    def get_template_name(self, obj: Certificate) -> str:
        return obj.template_version.template.name

    def get_verify_url(self, obj: Certificate) -> str:
        from apps.certificates.services import verify_url_for_code

        return verify_url_for_code(obj.code)
