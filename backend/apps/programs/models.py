from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel


class PublishStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class CohortStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    APPLICATIONS_OPEN = "applications_open", "Applications open"
    APPLICATIONS_CLOSED = "applications_closed", "Applications closed"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class Program(BaseModel):
    """Deprecated legacy table.

    Product hierarchy is Cohort (= academic session) › Class › Subject › Topic › Subtopic.
    Kept only so older migrations/DBs remain loadable; do not create new Program rows.
    """

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    description_rich = models.JSONField(default=dict, blank=True)
    cover = models.ImageField(upload_to="programs/", blank=True, null=True)
    status = models.CharField(max_length=16, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    category = models.CharField(max_length=64, blank=True)
    default_currency = models.CharField(max_length=3, default="NGN")

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title)[:200] or "program"
            candidate = base
            n = 1
            while Program.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class Cohort(BaseModel):
    """Academic session / intake root. Classes belong to a cohort."""

    program = models.ForeignKey(
        Program,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cohorts",
        help_text="Deprecated — always leave null. Cohort is the hierarchy root.",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.JSONField(default=dict, blank=True)
    cover_image = models.ImageField(upload_to="cohorts/", blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    capacity = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=32, choices=CohortStatus.choices, default=CohortStatus.PLANNED)
    application_opens_at = models.DateTimeField(null=True, blank=True)
    application_closes_at = models.DateTimeField(null=True, blank=True)
    application_fee_kobo = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Override application fee in kobo; null = inherit global default",
    )
    waitlist_enabled = models.BooleanField(default=False)
    waitlist_auto_promote = models.BooleanField(default=False)
    acceptance_deadline_days = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name)[:200] or "cohort"
            candidate = base
            n = 1
            while Cohort.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class Class(BaseModel):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="classes")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="classes/", blank=True, null=True)
    status = models.CharField(max_length=16, choices=PublishStatus.choices, default=PublishStatus.DRAFT)
    capacity = models.PositiveIntegerField(default=50)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["cohort", "slug"], name="uniq_class_slug_per_cohort"),
        ]

    def __str__(self) -> str:
        return f"{self.cohort.name} · {self.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name)[:200] or "class"
            candidate = base
            n = 1
            while Class.objects.filter(cohort=self.cohort, slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class TutorRole(models.TextChoices):
    LEAD = "lead", "Lead"
    ASSISTANT = "assistant", "Assistant"


class ClassTutor(BaseModel):
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="tutors")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_tutors")
    role = models.CharField(max_length=16, choices=TutorRole.choices, default=TutorRole.LEAD)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["class_ref", "user"], name="uniq_class_tutor"),
        ]


class SubjectAttachMode(models.TextChoices):
    LINKED = "linked", "Linked"
    CLONED = "cloned", "Cloned"


class ClassSubject(BaseModel):
    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="class_subjects")
    subject = models.ForeignKey("courses.Subject", on_delete=models.CASCADE, related_name="class_links")
    order = models.PositiveIntegerField(default=0)
    mode = models.CharField(
        max_length=16, choices=SubjectAttachMode.choices, default=SubjectAttachMode.LINKED
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["class_ref", "subject"], name="uniq_class_subject"),
        ]
