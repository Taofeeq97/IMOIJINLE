from __future__ import annotations

from rest_framework import serializers

from apps.comms.models import Announcement, Notification, NotificationPreference


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = (
            "id",
            "scope_type",
            "scope_id",
            "title",
            "body_json",
            "publish_at",
            "published",
            "send_email",
            "pinned",
            "author",
            "created_at",
        )
        read_only_fields = ("id", "author", "created_at")


class AnnouncementWriteSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(
        choices=["global", "program", "cohort", "class", "subject", "user"], default="class"
    )
    scope_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255)
    body_json = serializers.JSONField(required=False)
    publish_at = serializers.DateTimeField(required=False, allow_null=True)
    send_email = serializers.BooleanField(required=False, default=False)
    pinned = serializers.BooleanField(required=False, default=False)
    publish_now = serializers.BooleanField(required=False, default=True)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "kind", "title", "body", "payload", "read_at", "created_at")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "email_announcements",
            "email_grades",
            "email_payments",
            "email_digest",
            "in_app_enabled",
        )
