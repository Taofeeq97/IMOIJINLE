from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class ProgressStatus(models.TextChoices):
    LOCKED = "locked", "Locked"
    AVAILABLE = "available", "Available"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"


class ItemProgress(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="item_progress")
    subtopic = models.ForeignKey("courses.Subtopic", on_delete=models.CASCADE, related_name="progress_rows")
    enrollment = models.ForeignKey(
        "admissions.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="item_progress",
    )
    status = models.CharField(max_length=16, choices=ProgressStatus.choices, default=ProgressStatus.AVAILABLE)
    percent = models.PositiveSmallIntegerField(default=0)
    time_spent_s = models.PositiveIntegerField(default=0)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "subtopic"], name="uniq_item_progress_user_subtopic")
        ]


class VideoProgress(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="video_progress")
    subtopic = models.ForeignKey("courses.Subtopic", on_delete=models.CASCADE, related_name="video_progress")
    video_asset = models.ForeignKey(
        "courses.VideoAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="progress_rows"
    )
    last_position_s = models.PositiveIntegerField(default=0)
    furthest_position_s = models.PositiveIntegerField(default=0)
    watched_segments = models.JSONField(default=list, blank=True)
    watched_pct = models.PositiveSmallIntegerField(default=0)
    playback_rate = models.FloatField(default=1.0)
    caption_lang = models.CharField(max_length=16, blank=True)
    device_id = models.CharField(max_length=64, blank=True)
    client_ts = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "subtopic"], name="uniq_video_progress_user_subtopic")
        ]


class SubjectProgress(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subject_progress")
    subject = models.ForeignKey("courses.Subject", on_delete=models.CASCADE, related_name="progress_rows")
    enrollment = models.ForeignKey(
        "admissions.Enrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subject_progress",
    )
    completed_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    percent = models.PositiveSmallIntegerField(default=0)
    last_subtopic = models.ForeignKey(
        "courses.Subtopic", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "subject"], name="uniq_subject_progress_user_subject")
        ]


class Question(BaseModel):
    subject = models.ForeignKey("courses.Subject", on_delete=models.CASCADE, related_name="questions")
    subtopic = models.ForeignKey(
        "courses.Subtopic", null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qa_questions")
    title = models.CharField(max_length=200)
    body = models.TextField()
    upvote_count = models.PositiveIntegerField(default=0)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class Answer(BaseModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="qa_answers")
    body = models.TextField()
    is_instructor = models.BooleanField(default=False)
    upvote_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]


class Note(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    subtopic = models.ForeignKey("courses.Subtopic", on_delete=models.CASCADE, related_name="notes")
    body = models.TextField()
    timestamp_s = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
