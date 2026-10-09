from django.contrib import admin

from apps.admissions.models import Admission, Application, Enrollment


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant_email", "cohort", "status", "submitted_at", "fee_paid_at")
    list_filter = ("status",)
    search_fields = ("applicant_email", "applicant_name")
    readonly_fields = ("id", "created_at", "updated_at", "submitted_at")


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ("application", "class_ref", "admitted_by", "admitted_at")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "class_ref", "cohort", "status", "enrolled_at")
    list_filter = ("status",)
