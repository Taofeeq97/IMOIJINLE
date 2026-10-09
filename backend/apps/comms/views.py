from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.policies import can
from apps.comms import services
from apps.comms.models import Announcement, Notification, NotificationPreference
from apps.comms.serializers import (
    AnnouncementSerializer,
    AnnouncementWriteSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)


class AnnouncementListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if can(request.user, "programs.manage") or request.user.is_staff:
            qs = Announcement.objects.all()[:100]
            return Response(AnnouncementSerializer(qs, many=True).data)
        rows = services.list_announcements_for_user(request.user)
        return Response(AnnouncementSerializer(rows, many=True).data)

    def post(self, request):
        if not (can(request.user, "programs.manage") or can(request.user, "teach") or request.user.is_staff):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        ser = AnnouncementWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        ann = Announcement.objects.create(
            scope_type=data["scope_type"],
            scope_id=data.get("scope_id"),
            title=data["title"],
            body_json=data.get("body_json") or {},
            publish_at=data.get("publish_at"),
            send_email=data.get("send_email", False),
            pinned=data.get("pinned", False),
            author=request.user,
            published=False,
        )
        if data.get("publish_now", True):
            services.publish_announcement(announcement=ann, actor=request.user, request=request)
        return Response(AnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class AnnouncementDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, announcement_id):
        return Announcement.objects.filter(id=announcement_id).first()

    def patch(self, request, announcement_id):
        if not (can(request.user, "programs.manage") or can(request.user, "teach") or request.user.is_staff):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        ann = self._get(announcement_id)
        if not ann:
            return Response(
                {"code": "not_found", "message": "Announcement not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if "title" in request.data:
            ann.title = str(request.data.get("title") or ann.title)
        if "body_json" in request.data and isinstance(request.data.get("body_json"), dict):
            ann.body_json = request.data["body_json"]
        ann.save()
        return Response(AnnouncementSerializer(ann).data)

    def delete(self, request, announcement_id):
        if not (can(request.user, "programs.manage") or request.user.is_staff):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        ann = self._get(announcement_id)
        if not ann:
            return Response(
                {"code": "not_found", "message": "Announcement not found.", "fields": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        ann.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)[:100]
        return Response(NotificationSerializer(qs, many=True).data)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        updated = Notification.objects.filter(
            id=notification_id, user=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"updated": updated})


class NotificationPrefsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def put(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        ser = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class AnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not (can(request.user, "programs.manage") or can(request.user, "teach") or request.user.is_staff):
            return Response({"code": "forbidden", "message": "Forbidden"}, status=403)
        return Response(services.analytics_overview(cohort_id=request.query_params.get("cohort")))
