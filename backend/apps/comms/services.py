from __future__ import annotations

from typing import Any

from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.audit.services import log_audit
from apps.comms.models import Announcement, EmailLog, Notification, NotificationPreference


class CommsError(Exception):
    def __init__(self, message: str, code: str = "comms_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def notify(
    *,
    user,
    kind: str,
    title: str,
    body: str = "",
    payload: dict | None = None,
    email: bool = False,
    template_key: str = "",
) -> Notification:
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    n = Notification.objects.create(
        user=user,
        kind=kind,
        title=title,
        body=body,
        payload=payload or {},
    )
    should_email = email
    if kind.startswith("announcement") and not prefs.email_announcements:
        should_email = False
    if kind.startswith("payment") and not prefs.email_payments:
        should_email = False
    if kind.startswith("grade") and not prefs.email_grades:
        should_email = False
    if should_email:
        try:
            send_mail(
                subject=title,
                message=body or title,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
            EmailLog.objects.create(
                to_email=user.email,
                template_key=template_key or kind,
                subject=title,
                status="sent",
            )
        except Exception as exc:  # noqa: BLE001
            EmailLog.objects.create(
                to_email=user.email,
                template_key=template_key or kind,
                subject=title,
                status="failed",
                error=str(exc),
            )
    return n


def publish_announcement(*, announcement: Announcement, actor=None, request=None) -> Announcement:
    announcement.published = True
    if not announcement.publish_at:
        announcement.publish_at = timezone.now()
    announcement.save()
    recipients = _recipients_for(announcement)
    for user in recipients:
        notify(
            user=user,
            kind="announcement",
            title=announcement.title,
            body=str((announcement.body_json or {}).get("html") or ""),
            payload={"announcement_id": str(announcement.id)},
            email=announcement.send_email,
            template_key="announcement",
        )
    log_audit(
        actor=actor,
        action="announcement.publish",
        obj=announcement,
        after={"title": announcement.title, "recipients": len(recipients)},
        request=request,
    )
    return announcement


def _recipients_for(announcement: Announcement):
    from apps.accounts.models import User

    st = announcement.scope_type
    sid = announcement.scope_id
    if st == "global":
        return list(User.objects.filter(is_active=True, role_assignments__role="student").distinct())
    if st == "user" and sid:
        return list(User.objects.filter(id=sid))
    if st == "class" and sid:
        user_ids = Enrollment.objects.filter(
            class_ref_id=sid, status=EnrollmentStatus.ACTIVE
        ).values_list("user_id", flat=True)
        return list(User.objects.filter(id__in=user_ids))
    if st == "cohort" and sid:
        user_ids = Enrollment.objects.filter(
            cohort_id=sid, status=EnrollmentStatus.ACTIVE
        ).values_list("user_id", flat=True)
        return list(User.objects.filter(id__in=user_ids))
    if st == "subject" and sid:
        from apps.programs.models import ClassSubject

        class_ids = ClassSubject.objects.filter(subject_id=sid).values_list("class_ref_id", flat=True)
        user_ids = Enrollment.objects.filter(
            class_ref_id__in=class_ids, status=EnrollmentStatus.ACTIVE
        ).values_list("user_id", flat=True)
        return list(User.objects.filter(id__in=user_ids))
    return []


def list_announcements_for_user(user) -> list[Announcement]:
    now = timezone.now()
    class_ids = list(
        Enrollment.objects.filter(user=user, status=EnrollmentStatus.ACTIVE).values_list(
            "class_ref_id", flat=True
        )
    )
    cohort_ids = list(
        Enrollment.objects.filter(user=user, status=EnrollmentStatus.ACTIVE).values_list(
            "cohort_id", flat=True
        )
    )
    qs = Announcement.objects.filter(published=True).filter(
        Q(publish_at__isnull=True) | Q(publish_at__lte=now)
    )
    scoped = qs.filter(
        Q(scope_type="global")
        | Q(scope_type="user", scope_id=user.id)
        | Q(scope_type="class", scope_id__in=class_ids)
        | Q(scope_type="cohort", scope_id__in=cohort_ids)
    )
    return list(scoped[:100])


def analytics_overview(*, cohort_id: str | None = None) -> dict[str, Any]:
    """Lightweight learning analytics for M8 (not finance)."""
    from apps.admissions.models import Application, Enrollment
    from apps.learning.models import ItemProgress, ProgressStatus, SubjectProgress

    enr = Enrollment.objects.filter(status=EnrollmentStatus.ACTIVE)
    apps = Application.objects.all()
    if cohort_id:
        enr = enr.filter(cohort_id=cohort_id)
        apps = apps.filter(cohort_id=cohort_id)
    completed = ItemProgress.objects.filter(status=ProgressStatus.COMPLETED)
    if cohort_id:
        completed = completed.filter(enrollment__cohort_id=cohort_id)
    sp = SubjectProgress.objects.all()
    avg_pct = 0
    if sp.exists():
        vals = list(sp.values_list("percent", flat=True))
        avg_pct = int(round(sum(vals) / len(vals))) if vals else 0
    return {
        "applications": apps.count(),
        "active_enrollments": enr.count(),
        "completed_items": completed.count(),
        "avg_subject_progress_pct": avg_pct,
        "at_risk_students": SubjectProgress.objects.filter(percent__lt=20)
        .exclude(last_accessed_at__isnull=True)
        .count(),
    }
