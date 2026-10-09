from rest_framework import serializers

from apps.admissions.models import Application, Enrollment


class PublicApplySerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    data = serializers.DictField(required=False)


class ChangeEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class OnboardingVerifySerializer(serializers.Serializer):
    token = serializers.CharField()
    application_id = serializers.UUIDField()


class OnboardingSetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    application_id = serializers.UUIDField()
    password = serializers.CharField(min_length=10)


class AdmitSerializer(serializers.Serializer):
    class_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    group = serializers.CharField(required=False, allow_blank=True)
    fee_handling = serializers.ChoiceField(
        choices=["generate", "waive", "scholarship"], default="generate"
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class BulkAdmitSerializer(serializers.Serializer):
    application_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    class_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    fee_handling = serializers.ChoiceField(
        choices=["generate", "waive", "scholarship"], default="generate"
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class ApplicationSerializer(serializers.ModelSerializer):
    cohort_name = serializers.CharField(source="cohort.name", read_only=True)
    cohort_slug = serializers.CharField(source="cohort.slug", read_only=True)
    fee_amount_kobo = serializers.SerializerMethodField()
    fee_invoice_status = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "cohort",
            "cohort_name",
            "cohort_slug",
            "applicant_email",
            "applicant_name",
            "phone",
            "data",
            "status",
            "submitted_at",
            "fee_invoice",
            "fee_invoice_status",
            "fee_amount_kobo",
            "fee_paid_at",
            "admitted_class_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_fee_amount_kobo(self, obj: Application) -> int | None:
        if obj.fee_invoice_id:
            return obj.fee_invoice.amount_minor
        from apps.admissions.services import resolve_application_fee_kobo

        return resolve_application_fee_kobo(obj.cohort)

    def get_fee_invoice_status(self, obj: Application) -> str | None:
        if obj.fee_invoice_id:
            return obj.fee_invoice.status
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="class_ref.name", read_only=True)
    cohort_name = serializers.CharField(source="cohort.name", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "class_ref",
            "class_name",
            "cohort",
            "cohort_name",
            "status",
            "enrolled_at",
        ]
