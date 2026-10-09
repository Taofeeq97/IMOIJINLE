from django.contrib import admin

from apps.accounts.models import Invitation, Profile, RoleAssignment, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "first_name", "last_name")


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "scope_type", "scope_id", "created_at")
    list_filter = ("role", "scope_type")


admin.site.register(Profile)
admin.site.register(Invitation)
