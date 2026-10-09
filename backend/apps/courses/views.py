from __future__ import annotations

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import RolePermission
from apps.audit.services import log_audit
from apps.courses import services
from apps.courses.models import Subject, Subtopic, SubtopicResource, Topic, UploadSession
from apps.courses.serializers import (
    AddResourceSerializer,
    IntendedLearnersSerializer,
    LandingSerializer,
    MessagesSerializer,
    PresignSerializer,
    PricingSerializer,
    SetContentSerializer,
    SettingsSerializer,
    SubjectSerializer,
    SubtopicContentSerializer,
    SubtopicResourceSerializer,
    SubtopicSerializer,
    TopicSerializer,
    UploadSessionSerializer,
)
from apps.programs import services as program_services
from apps.programs.serializers import ReorderSerializer


class ContentManagePermission(RolePermission):
    required_action = "content.manage"


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated, ContentManagePermission]
    lookup_field = "id"
    search_fields = ["title", "slug", "category"]
    filterset_fields = ["status", "level", "language"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="subject.create",
            obj=obj,
            after=serializer.data,
            request=self.request,
        )

    def perform_update(self, serializer):
        before = SubjectSerializer(serializer.instance, context=self.get_serializer_context()).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="subject.update",
            obj=obj,
            before=before,
            after=SubjectSerializer(obj, context=self.get_serializer_context()).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="subject.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["get"], url_path="checklist")
    def checklist(self, request, id=None):
        return Response(services.subject_checklist(self.get_object()))

    @action(detail=True, methods=["get"], url_path="curriculum")
    def curriculum(self, request, id=None):
        return Response(services.curriculum_tree(self.get_object()))

    @action(detail=True, methods=["get", "put"], url_path="intended-learners")
    def intended_learners(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            data = subject.intended_learners or {"learn": [], "requirements": [], "audience": []}
            return Response(data)
        ser = IntendedLearnersSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subject.intended_learners = ser.validated_data
        subject.save(update_fields=["intended_learners", "updated_at"])
        log_audit(
            actor=request.user,
            action="subject.intended_learners",
            obj=subject,
            after=ser.validated_data,
            request=request,
        )
        return Response(subject.intended_learners)

    @action(detail=True, methods=["get", "put"], url_path="landing")
    def landing(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            return Response(SubjectSerializer(subject, context=self.get_serializer_context()).data)
        ser = LandingSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for key, value in ser.validated_data.items():
            setattr(subject, key, value)
        subject.save()
        if "cover" in request.FILES:
            subject.cover_image = request.FILES["cover"]
            subject.save(update_fields=["cover_image", "updated_at"])
        log_audit(actor=request.user, action="subject.landing", obj=subject, request=request)
        return Response(SubjectSerializer(subject, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get", "put"], url_path="pricing")
    def pricing(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            return Response(
                subject.pricing or {"mode": "free", "amount_kobo": 0, "currency": "NGN"}
            )
        ser = PricingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subject.pricing = ser.validated_data
        subject.save(update_fields=["pricing", "updated_at"])
        log_audit(
            actor=request.user,
            action="subject.pricing",
            obj=subject,
            after=ser.validated_data,
            request=request,
        )
        return Response(subject.pricing)

    @action(detail=True, methods=["get", "put"], url_path="messages")
    def messages(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            return Response(
                {
                    "welcome_message": subject.welcome_message,
                    "completion_message": subject.completion_message,
                }
            )
        ser = MessagesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subject.welcome_message = ser.validated_data["welcome_message"]
        subject.completion_message = ser.validated_data["completion_message"]
        subject.save(update_fields=["welcome_message", "completion_message", "updated_at"])
        return Response(ser.validated_data)

    @action(detail=True, methods=["get", "put"], url_path="settings")
    def subject_settings(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            return Response(subject.settings or {})
        ser = SettingsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subject.settings = ser.validated_data["settings"]
        subject.save(update_fields=["settings", "updated_at"])
        return Response(subject.settings)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, id=None):
        try:
            obj = services.publish_subject(
                subject=self.get_object(),
                actor=request.user,
                request=request,
                force=bool(request.data.get("force")),
            )
        except services.CourseError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubjectSerializer(obj, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="preview-token")
    def preview_token(self, request, id=None):
        raw, token = services.create_preview_token(
            subject=self.get_object(), actor=request.user, request=request
        )
        return Response(
            {
                "token": raw,
                "expires_at": token.expires_at,
                "preview_path": f"/admin/subjects/{id}/preview?token={raw}",
            }
        )

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        clone = program_services.duplicate_subject(
            subject=self.get_object(), actor=request.user, request=request
        )
        return Response(
            SubjectSerializer(clone, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="topics")
    def topics(self, request, id=None):
        subject = self.get_object()
        if request.method == "GET":
            qs = subject.topics.all()
            return Response(TopicSerializer(qs, many=True).data)
        data = {**request.data, "subject": str(subject.id)}
        if "order" not in data:
            data["order"] = subject.topics.count()
        ser = TopicSerializer(data=data)
        ser.is_valid(raise_exception=True)
        topic = ser.save()
        log_audit(
            actor=request.user, action="topic.create", obj=topic, after=ser.data, request=request
        )
        return Response(TopicSerializer(topic).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="topics/reorder")
    def reorder_topics(self, request, id=None):
        subject = self.get_object()
        ser = ReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        program_services.reorder_items(
            queryset=subject.topics.all(), ordered_ids=ser.validated_data["ordered_ids"]
        )
        log_audit(
            actor=request.user,
            action="subject.reorder_topics",
            obj=subject,
            after={"ordered_ids": [str(x) for x in ser.validated_data["ordered_ids"]]},
            request=request,
        )
        return Response(TopicSerializer(subject.topics.all(), many=True).data)


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.select_related("subject").all()
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated, ContentManagePermission]
    lookup_field = "id"
    filterset_fields = ["subject", "is_published"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def perform_update(self, serializer):
        before = TopicSerializer(serializer.instance).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="topic.update",
            obj=obj,
            before=before,
            after=TopicSerializer(obj).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="topic.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        clone = services.duplicate_topic(
            topic=self.get_object(), actor=request.user, request=request
        )
        return Response(TopicSerializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="subtopics")
    def subtopics(self, request, id=None):
        topic = self.get_object()
        if request.method == "GET":
            qs = topic.subtopics.select_related("content").prefetch_related("resources")
            return Response(SubtopicSerializer(qs, many=True, context={"request": request}).data)
        data = {**request.data, "topic": str(topic.id)}
        if "order" not in data:
            data["order"] = topic.subtopics.count()
        ser = SubtopicSerializer(data=data)
        ser.is_valid(raise_exception=True)
        sub = ser.save()
        log_audit(
            actor=request.user, action="subtopic.create", obj=sub, after=ser.data, request=request
        )
        return Response(
            SubtopicSerializer(sub, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="subtopics/reorder")
    def reorder_subtopics(self, request, id=None):
        topic = self.get_object()
        ser = ReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        program_services.reorder_items(
            queryset=topic.subtopics.all(), ordered_ids=ser.validated_data["ordered_ids"]
        )
        log_audit(
            actor=request.user,
            action="topic.reorder_subtopics",
            obj=topic,
            after={"ordered_ids": [str(x) for x in ser.validated_data["ordered_ids"]]},
            request=request,
        )
        qs = topic.subtopics.select_related("content").prefetch_related("resources")
        return Response(SubtopicSerializer(qs, many=True, context={"request": request}).data)


class SubtopicViewSet(viewsets.ModelViewSet):
    queryset = (
        Subtopic.objects.select_related("topic", "content").prefetch_related("resources").all()
    )
    serializer_class = SubtopicSerializer
    permission_classes = [IsAuthenticated, ContentManagePermission]
    lookup_field = "id"
    filterset_fields = ["topic", "kind", "is_published"]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_update(self, serializer):
        before = SubtopicSerializer(serializer.instance, context=self.get_serializer_context()).data
        obj = serializer.save()
        log_audit(
            actor=self.request.user,
            action="subtopic.update",
            obj=obj,
            before=before,
            after=SubtopicSerializer(obj, context=self.get_serializer_context()).data,
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            actor=self.request.user,
            action="subtopic.delete",
            obj=instance,
            before={"id": str(instance.id)},
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, id=None):
        clone = services.duplicate_subtopic(
            subtopic=self.get_object(), actor=request.user, request=request
        )
        return Response(
            SubtopicSerializer(clone, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post", "delete"], url_path="content")
    def content(self, request, id=None):
        subtopic = self.get_object()
        if request.method == "GET":
            if not hasattr(subtopic, "content") or not subtopic.content:
                return Response({"detail": "No content"}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                SubtopicContentSerializer(subtopic.content, context={"request": request}).data
            )
        if request.method == "DELETE":
            if hasattr(subtopic, "content") and subtopic.content:
                subtopic.content.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = SetContentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            content = services.set_subtopic_content(
                subtopic=subtopic,
                content_type=ser.validated_data["content_type"],
                actor=request.user,
                title=ser.validated_data.get("title") or "",
                body_json=ser.validated_data.get("body_json"),
                external_url=ser.validated_data.get("external_url") or "",
                upload_id=str(ser.validated_data["upload_id"])
                if ser.validated_data.get("upload_id")
                else None,
                mux_upload_id=ser.validated_data.get("mux_upload_id") or None,
                video_asset_id=str(ser.validated_data["video_asset_id"])
                if ser.validated_data.get("video_asset_id")
                else None,
                duration_s=ser.validated_data.get("duration_s") or 0,
                metadata=ser.validated_data.get("metadata"),
                request=request,
            )
        except services.CourseError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(SubtopicContentSerializer(content, context={"request": request}).data)

    @action(detail=True, methods=["get", "post"], url_path="resources")
    def resources(self, request, id=None):
        subtopic = self.get_object()
        if request.method == "GET":
            return Response(
                SubtopicResourceSerializer(
                    subtopic.resources.all(), many=True, context={"request": request}
                ).data
            )
        ser = AddResourceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            resource = services.add_resource(
                subtopic=subtopic,
                kind=ser.validated_data["kind"],
                title=ser.validated_data["title"],
                actor=request.user,
                url=ser.validated_data.get("url") or "",
                upload_id=str(ser.validated_data["upload_id"])
                if ser.validated_data.get("upload_id")
                else None,
                request=request,
            )
        except services.CourseError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "fields": {},
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            SubtopicResourceSerializer(resource, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class UploadPresignView(APIView):
    permission_classes = [IsAuthenticated, ContentManagePermission]

    def post(self, request):
        ser = PresignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subtopic = None
        if ser.validated_data.get("subtopic_id"):
            try:
                subtopic = Subtopic.objects.get(id=ser.validated_data["subtopic_id"])
            except Subtopic.DoesNotExist:
                return Response({"code": "not_found", "message": "Subtopic not found."}, status=404)
        payload = services.create_upload_session(
            user=request.user,
            purpose=ser.validated_data["purpose"],
            filename=ser.validated_data["filename"],
            mime_type=ser.validated_data.get("mime_type") or "",
            size_bytes=ser.validated_data.get("size_bytes") or 0,
            subtopic=subtopic,
        )
        return Response(payload, status=status.HTTP_201_CREATED)


class UploadCompleteView(APIView):
    permission_classes = [IsAuthenticated, ContentManagePermission]

    def post(self, request, upload_id):
        try:
            session = UploadSession.objects.get(id=upload_id, user=request.user)
        except UploadSession.DoesNotExist:
            return Response({"code": "not_found", "message": "Upload not found."}, status=404)
        try:
            session = services.complete_upload(session=session, actor=request.user, request=request)
        except services.CourseError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(UploadSessionSerializer(session).data)


class MuxDirectUploadView(APIView):
    permission_classes = [IsAuthenticated, ContentManagePermission]

    def post(self, request, subtopic_id):
        try:
            subtopic = Subtopic.objects.get(id=subtopic_id)
        except Subtopic.DoesNotExist:
            return Response({"code": "not_found", "message": "Subtopic not found."}, status=404)
        origin = (
            request.data.get("cors_origin")
            or request.headers.get("Origin")
            or settings.FRONTEND_URL
        )
        try:
            payload = services.create_mux_direct_upload(
                subtopic=subtopic,
                actor=request.user,
                cors_origin=origin,
                request=request,
            )
        except services.CourseError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(payload, status=status.HTTP_201_CREATED)


class MuxWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from apps.courses.models import ProcessingStatus, SubtopicContent, VideoAsset
        from apps.integrations import mux
        from apps.integrations.tasks import sync_mux_asset_task

        raw = request.body
        signature = request.headers.get("Mux-Signature")
        if not mux.verify_webhook_signature(raw_body=raw, signature_header=signature):
            return Response({"detail": "Invalid signature"}, status=401)
        payload = mux.parse_webhook(raw)
        event_type = payload.get("type") or ""
        data = payload.get("data") or {}

        if event_type.startswith("video.upload."):
            upload_id = data.get("id")
            asset_id = data.get("asset_id") or ""
            content = (
                SubtopicContent.objects.filter(metadata__mux_upload_id=upload_id)
                .select_related("video_asset")
                .first()
            )
            if content and content.video_asset_id:
                asset = content.video_asset
                if asset_id:
                    asset.provider_asset_id = asset_id
                if event_type.endswith("asset_created") or asset_id:
                    asset.status = ProcessingStatus.PROCESSING
                    content.processing_status = ProcessingStatus.PROCESSING
                if event_type.endswith("errored") or event_type.endswith("cancelled"):
                    asset.status = ProcessingStatus.ERRORED
                    content.processing_status = ProcessingStatus.ERRORED
                asset.raw = {**(asset.raw or {}), "upload_event": payload}
                asset.save()
                content.save(update_fields=["processing_status", "updated_at"])
                if asset.provider_asset_id:
                    sync_mux_asset_task.delay(str(asset.id))

        if event_type in {"video.asset.ready", "video.asset.errored"}:
            asset_id = data.get("id")
            asset = VideoAsset.objects.filter(provider_asset_id=asset_id).first()
            if asset:
                sync_mux_asset_task.delay(str(asset.id))
                if event_type == "video.asset.ready":
                    SubtopicContent.objects.filter(video_asset=asset).update(
                        processing_status=ProcessingStatus.READY
                    )
                else:
                    SubtopicContent.objects.filter(video_asset=asset).update(
                        processing_status=ProcessingStatus.ERRORED
                    )

        return Response({"status": "ok"})


class VideoPlaybackTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, video_asset_id):
        from apps.courses.models import VideoAsset
        from apps.integrations import mux
        from apps.integrations.mux import MuxError

        try:
            asset = VideoAsset.objects.get(id=video_asset_id)
        except VideoAsset.DoesNotExist:
            return Response({"code": "not_found", "message": "Video not found."}, status=404)
        if not asset.playback_id:
            return Response(
                {"code": "not_ready", "message": "Video is still processing."}, status=400
            )
        try:
            token = mux.sign_playback_id(asset.playback_id)
        except MuxError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        return Response(
            {
                "playback_id": asset.playback_id,
                "token": token,
                "policy": getattr(settings, "MUX_PLAYBACK_POLICY", "signed"),
            }
        )


class ResourceDeleteView(APIView):
    permission_classes = [IsAuthenticated, ContentManagePermission]

    def delete(self, request, resource_id):
        try:
            resource = SubtopicResource.objects.get(id=resource_id)
        except SubtopicResource.DoesNotExist:
            return Response(status=404)
        resource.delete()
        return Response(status=204)


class PublicPreviewView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, subject_id):
        token = request.query_params.get("token") or ""
        try:
            subject = services.resolve_preview_token(token=token, subject_id=str(subject_id))
        except services.CourseError as exc:
            return Response({"code": exc.code, "message": exc.message}, status=400)
        data = SubjectSerializer(subject, context={"request": request}).data
        data["curriculum"] = services.curriculum_tree(subject)
        data["preview"] = True
        return Response(data)
