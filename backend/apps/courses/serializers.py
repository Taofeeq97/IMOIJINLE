from __future__ import annotations

from rest_framework import serializers

from apps.courses.models import (
    Subject,
    Subtopic,
    SubtopicContent,
    SubtopicResource,
    Topic,
    UploadSession,
    VideoAsset,
)


class SubjectSerializer(serializers.ModelSerializer):
    topic_count = serializers.IntegerField(source="topics.count", read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            "id",
            "title",
            "subtitle",
            "slug",
            "description_json",
            "language",
            "level",
            "category",
            "subcategory",
            "primary_topic_tags",
            "cover_image",
            "cover_image_url",
            "promo_video",
            "intended_learners",
            "welcome_message",
            "completion_message",
            "status",
            "settings",
            "pricing",
            "version",
            "topic_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "created_at",
            "updated_at",
            "topic_count",
            "cover_image_url",
        ]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "cover_image": {"required": False, "allow_null": True},
        }

    def get_cover_image_url(self, obj: Subject) -> str | None:
        if obj.cover_image:
            request = self.context.get("request")
            url = obj.cover_image.url
            return request.build_absolute_uri(url) if request else url
        return None


class IntendedLearnersSerializer(serializers.Serializer):
    learn = serializers.ListField(child=serializers.CharField(max_length=160), allow_empty=True)
    requirements = serializers.ListField(
        child=serializers.CharField(max_length=200), allow_empty=True
    )
    audience = serializers.ListField(child=serializers.CharField(max_length=200), allow_empty=True)


class LandingSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=60, required=False)
    subtitle = serializers.CharField(max_length=120, required=False, allow_blank=True)
    description_json = serializers.DictField(required=False)
    language = serializers.CharField(max_length=16, required=False)
    level = serializers.CharField(max_length=16, required=False)
    category = serializers.CharField(max_length=64, required=False, allow_blank=True)
    subcategory = serializers.CharField(max_length=64, required=False, allow_blank=True)
    promo_video = serializers.URLField(required=False, allow_blank=True)
    primary_topic_tags = serializers.ListField(child=serializers.CharField(), required=False)


class PricingSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["free", "class_fee", "paid"])
    amount_kobo = serializers.IntegerField(min_value=0, required=False, default=0)
    currency = serializers.CharField(max_length=3, required=False, default="NGN")
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    installments_enabled = serializers.BooleanField(required=False, default=False)
    gate_rule = serializers.DictField(required=False)


class MessagesSerializer(serializers.Serializer):
    welcome_message = serializers.CharField(allow_blank=True)
    completion_message = serializers.CharField(allow_blank=True)


class SettingsSerializer(serializers.Serializer):
    settings = serializers.DictField()


class TopicSerializer(serializers.ModelSerializer):
    subtopic_count = serializers.IntegerField(source="subtopics.count", read_only=True)

    class Meta:
        model = Topic
        fields = [
            "id",
            "subject",
            "title",
            "objective_text",
            "order",
            "is_published",
            "subtopic_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "subtopic_count"]


class VideoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = [
            "id",
            "provider",
            "playback_id",
            "duration_s",
            "status",
            "captions",
            "chapters",
            "thumbnail_url",
            "downloadable",
        ]


class SubtopicContentSerializer(serializers.ModelSerializer):
    video_asset = VideoAssetSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()

    class Meta:
        model = SubtopicContent
        fields = [
            "id",
            "content_type",
            "title",
            "body_json",
            "external_url",
            "mime_type",
            "size_bytes",
            "processing_status",
            "video_asset",
            "duration_s",
            "thumbnail_url",
            "metadata",
            "file_url",
            "preview_url",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj: SubtopicContent) -> str | None:
        request = self.context.get("request")
        if obj.file:
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        object_key = (obj.metadata or {}).get("object_key")
        if object_key:
            from apps.integrations import storage

            try:
                return storage.create_presigned_get(object_key=object_key, expires_in=3600)
            except Exception:  # noqa: BLE001
                return None
        return None

    def get_preview_url(self, obj: SubtopicContent) -> str | None:
        request = self.context.get("request")
        if obj.preview_file:
            url = obj.preview_file.url
            return request.build_absolute_uri(url) if request else url
        preview_key = (obj.metadata or {}).get("preview_object_key")
        if preview_key:
            from apps.integrations import storage

            try:
                return storage.create_presigned_get(object_key=preview_key, expires_in=3600)
            except Exception:  # noqa: BLE001
                return None
        return None


class SubtopicResourceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SubtopicResource
        fields = [
            "id",
            "subtopic",
            "kind",
            "title",
            "url",
            "order",
            "download_allowed",
            "file_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "file_url"]

    def get_file_url(self, obj: SubtopicResource) -> str | None:
        if not obj.file:
            return None
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class SubtopicSerializer(serializers.ModelSerializer):
    content = SubtopicContentSerializer(read_only=True)
    resources = SubtopicResourceSerializer(many=True, read_only=True)
    has_content = serializers.SerializerMethodField()

    class Meta:
        model = Subtopic
        fields = [
            "id",
            "topic",
            "title",
            "order",
            "kind",
            "is_published",
            "is_free_preview",
            "estimated_time_s",
            "min_time_s",
            "require_full_watch",
            "description_json",
            "drip_rule",
            "unlock_rule",
            "has_content",
            "content",
            "resources",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "has_content", "content", "resources"]

    def get_has_content(self, obj: Subtopic) -> bool:
        return hasattr(obj, "content") and obj.content is not None


class SetContentSerializer(serializers.Serializer):
    content_type = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    body_json = serializers.DictField(required=False)
    external_url = serializers.URLField(required=False, allow_blank=True)
    upload_id = serializers.UUIDField(required=False)
    mux_upload_id = serializers.CharField(required=False, allow_blank=True)
    video_asset_id = serializers.UUIDField(required=False)
    duration_s = serializers.IntegerField(required=False, min_value=0)
    metadata = serializers.DictField(required=False)


class AddResourceSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["file", "link", "library"])
    title = serializers.CharField(max_length=200)
    url = serializers.URLField(required=False, allow_blank=True)
    upload_id = serializers.UUIDField(required=False)


class PresignSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=["content", "resource", "cover", "caption", "promo"])
    filename = serializers.CharField(max_length=255)
    mime_type = serializers.CharField(required=False, allow_blank=True)
    size_bytes = serializers.IntegerField(required=False, min_value=0)
    subtopic_id = serializers.UUIDField(required=False)


class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSession
        fields = [
            "id",
            "purpose",
            "filename",
            "mime_type",
            "size_bytes",
            "status",
            "object_key",
            "error_message",
            "created_at",
        ]
