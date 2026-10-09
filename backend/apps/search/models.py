from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel


class OIDCSettings(BaseModel):
    """Phase-4 SSO config (M9). Disabled until client_id/issuer set."""

    enabled = models.BooleanField(default=False)
    issuer = models.URLField(blank=True)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret_encrypted = models.TextField(blank=True)
    scopes = models.CharField(max_length=255, default="openid profile email")
    redirect_path = models.CharField(max_length=255, default="/auth/oidc/callback")

    class Meta:
        verbose_name_plural = "OIDC settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def unified_search(*, q: str, user, limit: int = 20) -> dict:
    """Postgres icontains search across core entities (OpenSearch adapter later)."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "results": []}

    results = []
    from apps.courses.models import Subject, Subtopic
    from apps.programs.models import Class, Cohort, Program

    for p in Program.objects.filter(Q(title__icontains=q) | Q(slug__icontains=q))[:limit]:
        results.append({"type": "program", "id": str(p.id), "title": p.title, "href": f"/admin/programs"})
    for c in Cohort.objects.filter(Q(name__icontains=q) | Q(slug__icontains=q))[:limit]:
        results.append(
            {"type": "cohort", "id": str(c.id), "title": c.name, "href": f"/admin/cohorts/{c.id}"}
        )
    for klass in Class.objects.filter(Q(name__icontains=q) | Q(slug__icontains=q))[:limit]:
        results.append(
            {
                "type": "class",
                "id": str(klass.id),
                "title": klass.name,
                "href": f"/admin/classes/{klass.id}",
            }
        )
    for s in Subject.objects.filter(Q(title__icontains=q) | Q(slug__icontains=q))[:limit]:
        results.append(
            {
                "type": "subject",
                "id": str(s.id),
                "title": s.title,
                "href": f"/subjects/{s.slug}" if not user.is_staff else f"/admin/subjects/{s.id}/manage",
            }
        )
    for st in Subtopic.objects.filter(title__icontains=q).select_related("topic__subject")[:limit]:
        results.append(
            {
                "type": "subtopic",
                "id": str(st.id),
                "title": st.title,
                "href": f"/learn/{st.topic.subject_id}/{st.id}",
            }
        )
    return {"query": q, "results": results[:limit]}
