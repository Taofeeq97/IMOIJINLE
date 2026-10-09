from __future__ import annotations

from rest_framework import serializers

from apps.programs.models import Class, ClassSubject, ClassTutor, Cohort, Program


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "description_rich",
            "status",
            "category",
            "default_currency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class CohortSerializer(serializers.ModelSerializer):
    """Cohort is the product root (academic session). `program` is deprecated legacy."""

    program_title = serializers.CharField(source="program.title", read_only=True, allow_null=True)
    public_apply_path = serializers.SerializerMethodField()

    class Meta:
        model = Cohort
        fields = [
            "id",
            "program",
            "program_title",
            "name",
            "slug",
            "description",
            "start_date",
            "end_date",
            "timezone",
            "capacity",
            "status",
            "application_opens_at",
            "application_closes_at",
            "application_fee_kobo",
            "waitlist_enabled",
            "waitlist_auto_promote",
            "acceptance_deadline_days",
            "order",
            "public_apply_path",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "public_apply_path",
            "program",
            "program_title",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_public_apply_path(self, obj: Cohort) -> str:
        return f"/apply/{obj.slug}"


class ClassSerializer(serializers.ModelSerializer):
    cohort_name = serializers.CharField(source="cohort.name", read_only=True)
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Class
        fields = [
            "id",
            "cohort",
            "cohort_name",
            "name",
            "slug",
            "description",
            "status",
            "capacity",
            "starts_at",
            "ends_at",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "cohort_name"]
        # UniqueConstraint(cohort, slug) would force slug required via UniqueTogetherValidator
        validators: list = []

    def validate(self, attrs):
        if not attrs.get("slug"):
            attrs["slug"] = ""
        return attrs


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(source="subject.title", read_only=True)
    subject_status = serializers.CharField(source="subject.status", read_only=True)

    class Meta:
        model = ClassSubject
        fields = [
            "id",
            "class_ref",
            "subject",
            "subject_title",
            "subject_status",
            "order",
            "mode",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "subject_title", "subject_status"]


class AttachSubjectSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField()
    mode = serializers.ChoiceField(choices=["linked", "cloned"], default="linked")


class ReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class ClassTutorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ClassTutor
        fields = ["id", "class_ref", "user", "user_email", "role", "created_at"]
        read_only_fields = ["id", "created_at", "user_email"]
