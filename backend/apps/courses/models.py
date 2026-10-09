from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel


class SubjectLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"
    ALL = "all", "All levels"


class SubjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In review"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Subject(BaseModel):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=240, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description_json = models.JSONField(default=dict, blank=True)
    language = models.CharField(max_length=16, default="en")
    level = models.CharField(max_length=16, choices=SubjectLevel.choices, default=SubjectLevel.ALL)
    category = models.CharField(max_length=64, blank=True)
    subcategory = models.CharField(max_length=64, blank=True)
    primary_topic_tags = models.JSONField(default=list, blank=True)
    cover_image = models.ImageField(upload_to="subjects/", blank=True, null=True)
    promo_video = models.URLField(blank=True)
    intended_learners = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"learn": [], "requirements": [], "audience": []}',
    )
    welcome_message = models.TextField(blank=True)
    completion_message = models.TextField(blank=True)
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="subjects_instructing"
    )
    status = models.CharField(
        max_length=16, choices=SubjectStatus.choices, default=SubjectStatus.DRAFT
    )
    settings = models.JSONField(default=dict, blank=True)
    pricing = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"mode":"free|class_fee|paid","amount_kobo":0,"currency":"NGN"}',
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title)[:200] or "subject"
            candidate = base
            n = 1
            while Subject.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class Topic(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=200)
    objective_text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.subject.title} · {self.title}"


class SubtopicKind(models.TextChoices):
    SUBTOPIC = "subtopic", "Subtopic (lesson)"
    QUIZ = "quiz", "Quiz"
    ASSIGNMENT = "assignment", "Assignment"
    PRACTICE_TEST = "practice_test", "Practice test"


class Subtopic(BaseModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="subtopics")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    kind = models.CharField(
        max_length=32, choices=SubtopicKind.choices, default=SubtopicKind.SUBTOPIC
    )
    is_published = models.BooleanField(default=False)
    is_free_preview = models.BooleanField(default=False)
    estimated_time_s = models.PositiveIntegerField(default=0)
    min_time_s = models.PositiveIntegerField(default=0)
    description_json = models.JSONField(default=dict, blank=True)
    drip_rule = models.JSONField(default=dict, blank=True)
    unlock_rule = models.JSONField(default=dict, blank=True)
    require_full_watch = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return self.title


class ContentType(models.TextChoices):
    VIDEO = "video", "Video"
    VIDEO_SLIDES = "video_slides", "Video + slides"
    ARTICLE = "article", "Article"
    PDF = "pdf", "PDF"
    SPREADSHEET = "spreadsheet", "Spreadsheet"
    DOCUMENT = "document", "Document (Word)"
    PRESENTATION = "presentation", "Presentation"
    AUDIO = "audio", "Audio"
    IMAGE = "image", "Image"
    LINK = "link", "Link / Embed"
    LIVE = "live", "Live session"


class ProcessingStatus(models.TextChoices):
    UPLOADING = "uploading", "Uploading"
    PROCESSING = "processing", "Processing"
    READY = "ready", "Ready"
    ERRORED = "errored", "Errored"
    CONVERTED = "converted", "Converted"


class VideoAsset(BaseModel):
    provider = models.CharField(max_length=32, default="mux")
    provider_asset_id = models.CharField(max_length=128, blank=True)
    playback_id = models.CharField(max_length=128, blank=True)
    policy = models.CharField(max_length=16, default="signed")
    duration_s = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.READY
    )
    captions = models.JSONField(default=list, blank=True)
    chapters = models.JSONField(default=list, blank=True)
    thumbnail_url = models.URLField(blank=True)
    downloadable = models.BooleanField(default=False)
    raw = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.provider}:{self.playback_id or self.id}"


class SubtopicContent(BaseModel):
    subtopic = models.OneToOneField(Subtopic, on_delete=models.CASCADE, related_name="content")
    content_type = models.CharField(max_length=32, choices=ContentType.choices)
    title = models.CharField(max_length=200, blank=True)
    body_json = models.JSONField(default=dict, blank=True)
    file = models.FileField(upload_to="content/", blank=True, null=True)
    preview_file = models.FileField(upload_to="content/preview/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    processing_status = models.CharField(
        max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.READY
    )
    video_asset = models.ForeignKey(
        VideoAsset, null=True, blank=True, on_delete=models.SET_NULL, related_name="contents"
    )
    duration_s = models.PositiveIntegerField(default=0)
    thumbnail_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.subtopic_id} · {self.content_type}"


class ResourceKind(models.TextChoices):
    FILE = "file", "Downloadable file"
    LINK = "link", "External link"
    LIBRARY = "library", "Library asset"


class SubtopicResource(BaseModel):
    subtopic = models.ForeignKey(Subtopic, on_delete=models.CASCADE, related_name="resources")
    kind = models.CharField(max_length=16, choices=ResourceKind.choices, default=ResourceKind.FILE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="resources/", blank=True, null=True)
    url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    download_allowed = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "created_at"]


class UploadPurpose(models.TextChoices):
    CONTENT = "content", "Subtopic content"
    RESOURCE = "resource", "Resource"
    COVER = "cover", "Cover image"
    CAPTION = "caption", "Caption"
    PROMO = "promo", "Promo video"


class UploadSession(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="uploads"
    )
    purpose = models.CharField(max_length=32, choices=UploadPurpose.choices)
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.UPLOADING
    )
    object_key = models.CharField(max_length=512, blank=True)
    file = models.FileField(upload_to="uploads/", blank=True, null=True)
    subtopic = models.ForeignKey(
        Subtopic, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploads"
    )
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class SubjectPreviewToken(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="preview_tokens")
    token_hash = models.CharField(max_length=128, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
