from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel


class TemplateStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class PageOrientation(models.TextChoices):
    LANDSCAPE = "landscape", "Landscape"
    PORTRAIT = "portrait", "Portrait"


class PageSize(models.TextChoices):
    A4 = "A4", "A4"
    LETTER = "Letter", "Letter"
    CUSTOM = "custom", "Custom"


class CertificateStatus(models.TextChoices):
    ISSUED = "issued", "Issued"
    REVOKED = "revoked", "Revoked"
    REISSUED = "reissued", "Reissued"


class CertificateTemplate(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    status = models.CharField(
        max_length=16, choices=TemplateStatus.choices, default=TemplateStatus.DRAFT
    )
    orientation = models.CharField(
        max_length=16, choices=PageOrientation.choices, default=PageOrientation.LANDSCAPE
    )
    page_size = models.CharField(max_length=16, choices=PageSize.choices, default=PageSize.A4)
    page_custom = models.JSONField(default=dict, blank=True)
    current_version = models.ForeignKey(
        "CertificateTemplateVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificate_templates_created",
    )
    last_previewed_at = models.DateTimeField(null=True, blank=True)
    last_preview_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name)[:200] or "certificate"
            candidate = base
            n = 1
            while CertificateTemplate.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class CertificateTemplateVersion(BaseModel):
    template = models.ForeignKey(
        CertificateTemplate, on_delete=models.CASCADE, related_name="versions"
    )
    version_no = models.PositiveIntegerField()
    design = models.JSONField(default=dict)
    thumbnail = models.ImageField(upload_to="certificates/thumbnails/", blank=True, null=True)
    note = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificate_versions_created",
    )

    class Meta:
        ordering = ["-version_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version_no"], name="uniq_cert_template_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.template.name} v{self.version_no}"


class CertificateIssueRule(BaseModel):
    name = models.CharField(max_length=200, blank=True)
    template = models.ForeignKey(
        CertificateTemplate, on_delete=models.CASCADE, related_name="issue_rules"
    )
    class_ref = models.ForeignKey(
        "programs.Class",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="certificate_rules",
    )
    subject = models.ForeignKey(
        "courses.Subject",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="certificate_rules",
    )
    criteria = models.JSONField(default=dict, blank=True)
    auto_issue = models.BooleanField(default=False)
    valid_for_days = models.PositiveIntegerField(null=True, blank=True)
    numbering_pattern = models.CharField(max_length=120, default="IMO-{yyyy}-{seq:5}", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or f"Rule {self.id}"


class Certificate(BaseModel):
    code = models.CharField(max_length=16, unique=True, db_index=True)
    enrollment = models.ForeignKey(
        "admissions.Enrollment", on_delete=models.CASCADE, related_name="certificates"
    )
    template_version = models.ForeignKey(
        CertificateTemplateVersion, on_delete=models.PROTECT, related_name="certificates"
    )
    issue_rule = models.ForeignKey(
        CertificateIssueRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
    )
    subject = models.ForeignKey(
        "courses.Subject",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates_issued",
    )
    status = models.CharField(
        max_length=16, choices=CertificateStatus.choices, default=CertificateStatus.ISSUED
    )
    revoked_reason = models.TextField(blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    pdf_file = models.FileField(upload_to="certificates/pdf/", blank=True, null=True)
    html_snapshot = models.TextField(blank=True)
    data_snapshot = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="superseded_by",
    )

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return self.code


class CertificateVerificationLog(BaseModel):
    certificate = models.ForeignKey(
        Certificate, on_delete=models.CASCADE, related_name="verification_logs"
    )
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
