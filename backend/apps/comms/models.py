from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Announcement(BaseModel):
    scope_type = models.CharField(
        max_length=32,
        choices=[
            ("global", "Global"),
            ("program", "Program"),
            ("cohort", "Cohort"),
            ("class", "Class"),
            ("subject", "Subject"),
            ("user", "User"),
        ],
        default="class",
    )
    scope_id = models.UUIDField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255)
    body_json = models.JSONField(default=dict, blank=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    published = models.BooleanField(default=True)
    send_email = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="announcements"
    )

    class Meta:
        ordering = ["-pinned", "-publish_at", "-created_at"]


class Notification(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class NotificationPreference(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_prefs"
    )
    email_announcements = models.BooleanField(default=True)
    email_grades = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    email_digest = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)


class EmailLog(BaseModel):
    to_email = models.EmailField()
    template_key = models.CharField(max_length=64, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, default="queued")
    provider_id = models.CharField(max_length=128, blank=True)
    error = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
