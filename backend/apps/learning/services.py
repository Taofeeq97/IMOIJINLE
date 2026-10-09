from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.admissions.models import Enrollment, EnrollmentStatus
from apps.courses.models import ContentType, ProcessingStatus, Subject, SubjectStatus, Subtopic, Topic
from apps.integrations import mux, storage
from apps.integrations.mux import MuxError
from apps.learning.models import (
    Answer,
    ItemProgress,
    Note,
    ProgressStatus,
    Question,
    SubjectProgress,
    VideoProgress,
)
from apps.programs.models import ClassSubject


class LearningError(Exception):
    def __init__(self, message: str, code: str = "learning_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


WATCH_COMPLETE_PCT = 90


def user_enrollments(user):
    return Enrollment.objects.filter(user=user, status=EnrollmentStatus.ACTIVE).select_related(
        "class_ref", "cohort"
    )


def accessible_subject_ids(user) -> set[str]:
    class_ids = user_enrollments(user).values_list("class_ref_id", flat=True)
    return {
        str(sid)
        for sid in ClassSubject.objects.filter(class_ref_id__in=class_ids).values_list("subject_id", flat=True)
    }


def assert_subject_access(*, user, subject: Subject, allow_preview: bool = False) -> Enrollment | None:
    if user.is_staff or user.is_superuser:
        return user_enrollments(user).first()
    enrollment = (
        user_enrollments(user)
        .filter(class_ref__class_subjects__subject=subject)
        .distinct()
        .first()
    )
    if enrollment:
        try:
            from apps.payments.services import can_access_subject

            access = can_access_subject(
                user=user,
                subject_id=str(subject.id),
                class_id=str(enrollment.class_ref_id),
            )
            if not access.get("allowed", True):
                raise LearningError(
                    "Payment required before accessing this subject.",
                    code="payment_gate",
                )
        except LearningError:
            raise
        except Exception:  # noqa: BLE001
            pass
        return enrollment
    if allow_preview and subject.status == SubjectStatus.PUBLISHED:
        # free preview only checked at subtopic level
        return None
    raise LearningError("You do not have access to this subject.", code="forbidden")


def assert_subtopic_access(*, user, subtopic: Subtopic) -> Enrollment | None:
    subject = subtopic.topic.subject
    enrollment = assert_subject_access(user=user, subject=subject, allow_preview=True)
    if enrollment:
        return enrollment
    if subtopic.is_free_preview and subject.status == SubjectStatus.PUBLISHED:
        return None
    raise LearningError("You do not have access to this subtopic.", code="forbidden")


def _subtopics_qs(subject: Subject):
    return Subtopic.objects.filter(topic__subject=subject, is_published=True).select_related(
        "topic", "content", "content__video_asset"
    )


def recompute_subject_progress(*, user, subject: Subject, enrollment=None) -> SubjectProgress:
    subs = list(_subtopics_qs(subject))
    total = len(subs)
    completed = ItemProgress.objects.filter(
        user=user, subtopic_id__in=[s.id for s in subs], status=ProgressStatus.COMPLETED
    ).count()
    percent = int(round((completed / total) * 100)) if total else 0
    sp, _ = SubjectProgress.objects.get_or_create(user=user, subject=subject)
    sp.enrollment = enrollment or sp.enrollment
    sp.completed_count = completed
    sp.total_count = total
    sp.percent = percent
    just_completed = percent >= 100 and not sp.completed_at
    if just_completed:
        sp.completed_at = timezone.now()
    sp.last_accessed_at = timezone.now()
    sp.save()
    if percent >= 100:
        try:
            from apps.certificates.services import maybe_auto_issue_on_progress

            maybe_auto_issue_on_progress(
                user=user, subject=subject, enrollment=enrollment or sp.enrollment
            )
        except Exception:  # noqa: BLE001 — never block progress on cert errors
            pass
    return sp


def my_learning_payload(user) -> dict[str, Any]:
    enrollments = list(user_enrollments(user).prefetch_related("class_ref__class_subjects__subject"))
    continue_strip = None
    classes = []
    subjects_cards = []
    seen_subjects: set[str] = set()

    for enr in enrollments:
        class_obj = enr.class_ref
        class_subjects = []
        for link in class_obj.class_subjects.select_related("subject").order_by("order"):
            subject = link.subject
            if subject.status != SubjectStatus.PUBLISHED and not user.is_staff:
                continue
            sp = SubjectProgress.objects.filter(user=user, subject=subject).first()
            percent = sp.percent if sp else 0
            last_sub = sp.last_subtopic_id if sp else None
            card = {
                "subject_id": str(subject.id),
                "subject_slug": subject.slug,
                "title": subject.title,
                "subtitle": subject.subtitle,
                "cover_image_url": subject.cover_image.url if subject.cover_image else None,
                "level": subject.level,
                "class_id": str(class_obj.id),
                "class_name": class_obj.name,
                "cohort_name": enr.cohort.name,
                "percent": percent,
                "continue_subtopic_id": str(last_sub) if last_sub else None,
                "last_accessed_at": sp.last_accessed_at if sp else None,
            }
            class_subjects.append(card)
            if str(subject.id) not in seen_subjects:
                subjects_cards.append(card)
                seen_subjects.add(str(subject.id))
            if sp and sp.last_accessed_at:
                if continue_strip is None or (sp.last_accessed_at > continue_strip["last_accessed_at"]):
                    continue_strip = {
                        **card,
                        "last_accessed_at": sp.last_accessed_at,
                    }
        classes.append(
            {
                "enrollment_id": str(enr.id),
                "class_id": str(class_obj.id),
                "class_name": class_obj.name,
                "cohort_name": enr.cohort.name,
                "status": enr.status,
                "enrolled_at": enr.enrolled_at,
                "subjects": class_subjects,
            }
        )

    subjects_cards.sort(
        key=lambda c: (c["last_accessed_at"] is not None, c["last_accessed_at"] or ""),
        reverse=True,
    )
    return {
        "continue": continue_strip,
        "subjects": subjects_cards,
        "classes": classes,
    }


def subject_landing_payload(*, user, slug: str) -> dict[str, Any]:
    try:
        subject = Subject.objects.prefetch_related("instructors", "topics__subtopics").get(slug=slug)
    except Subject.DoesNotExist as exc:
        raise LearningError("Subject not found.", code="not_found") from exc

    enrollment = None
    try:
        enrollment = assert_subject_access(user=user, subject=subject, allow_preview=True)
        has_access = enrollment is not None or user.is_staff
    except LearningError:
        has_access = False

    sp = SubjectProgress.objects.filter(user=user, subject=subject).first()
    topics = []
    for topic in subject.topics.filter(is_published=True).order_by("order"):
        subs = []
        for sub in topic.subtopics.filter(is_published=True).order_by("order"):
            ip = ItemProgress.objects.filter(user=user, subtopic=sub).first()
            subs.append(
                {
                    "id": str(sub.id),
                    "title": sub.title,
                    "kind": sub.kind,
                    "estimated_time_s": sub.estimated_time_s,
                    "is_free_preview": sub.is_free_preview,
                    "content_type": getattr(getattr(sub, "content", None), "content_type", None),
                    "completed": bool(ip and ip.status == ProgressStatus.COMPLETED),
                }
            )
        topics.append(
            {
                "id": str(topic.id),
                "title": topic.title,
                "objective_text": topic.objective_text,
                "subtopic_count": len(subs),
                "total_time_s": sum(s["estimated_time_s"] for s in subs),
                "subtopics": subs,
            }
        )

    continue_id = None
    if sp and sp.last_subtopic_id:
        continue_id = str(sp.last_subtopic_id)
    elif topics and topics[0]["subtopics"]:
        continue_id = topics[0]["subtopics"][0]["id"]

    return {
        "id": str(subject.id),
        "slug": subject.slug,
        "title": subject.title,
        "subtitle": subject.subtitle,
        "description_json": subject.description_json,
        "language": subject.language,
        "level": subject.level,
        "category": subject.category,
        "intended_learners": subject.intended_learners or {},
        "promo_video": subject.promo_video,
        "cover_image_url": subject.cover_image.url if subject.cover_image else None,
        "instructors": [
            {"id": str(u.id), "name": f"{u.first_name} {u.last_name}".strip() or u.email, "email": u.email}
            for u in subject.instructors.all()
        ],
        "has_access": has_access,
        "percent": sp.percent if sp else 0,
        "continue_subtopic_id": continue_id,
        "curriculum": topics,
        "updated_at": subject.updated_at,
    }


def player_outline(*, user, subject_id: str) -> dict[str, Any]:
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist as exc:
        raise LearningError("Subject not found.", code="not_found") from exc
    enrollment = assert_subject_access(user=user, subject=subject, allow_preview=True)
    sp = recompute_subject_progress(user=user, subject=subject, enrollment=enrollment)
    topics = []
    for topic in subject.topics.filter(is_published=True).order_by("order"):
        rows = []
        for sub in topic.subtopics.filter(is_published=True).order_by("order"):
            ip = ItemProgress.objects.filter(user=user, subtopic=sub).first()
            locked = False
            lock_reason = ""
            if not enrollment and not sub.is_free_preview and not user.is_staff:
                locked = True
                lock_reason = "Enroll to unlock"
            rows.append(
                {
                    "id": str(sub.id),
                    "title": sub.title,
                    "kind": sub.kind,
                    "estimated_time_s": sub.estimated_time_s,
                    "min_time_s": sub.min_time_s,
                    "content_type": getattr(getattr(sub, "content", None), "content_type", None),
                    "completed": bool(ip and ip.status == ProgressStatus.COMPLETED),
                    "time_spent_s": ip.time_spent_s if ip else 0,
                    "locked": locked,
                    "lock_reason": lock_reason,
                    "is_free_preview": sub.is_free_preview,
                    "resource_count": sub.resources.count(),
                }
            )
        done = sum(1 for r in rows if r["completed"])
        topics.append(
            {
                "id": str(topic.id),
                "title": topic.title,
                "completed_count": done,
                "total_count": len(rows),
                "total_time_s": sum(r["estimated_time_s"] for r in rows),
                "subtopics": rows,
            }
        )
    return {
        "subject_id": str(subject.id),
        "title": subject.title,
        "percent": sp.percent,
        "completed_count": sp.completed_count,
        "total_count": sp.total_count,
        "topics": topics,
    }


def viewer_payload(*, user, subtopic_id: str) -> dict[str, Any]:
    try:
        subtopic = Subtopic.objects.select_related(
            "topic__subject", "content", "content__video_asset"
        ).prefetch_related("resources").get(id=subtopic_id)
    except Subtopic.DoesNotExist as exc:
        raise LearningError("Subtopic not found.", code="not_found") from exc

    enrollment = assert_subtopic_access(user=user, subtopic=subtopic)
    subject = subtopic.topic.subject
    now = timezone.now()
    ip, _ = ItemProgress.objects.get_or_create(
        user=user,
        subtopic=subtopic,
        defaults={
            "enrollment": enrollment,
            "status": ProgressStatus.IN_PROGRESS,
            "first_opened_at": now,
            "last_active_at": now,
        },
    )
    if not ip.first_opened_at:
        ip.first_opened_at = now
    ip.last_active_at = now
    if ip.status == ProgressStatus.AVAILABLE:
        ip.status = ProgressStatus.IN_PROGRESS
    ip.enrollment = enrollment or ip.enrollment
    ip.save()

    sp, _ = SubjectProgress.objects.get_or_create(user=user, subject=subject)
    sp.last_subtopic = subtopic
    sp.last_accessed_at = now
    sp.enrollment = enrollment or sp.enrollment
    sp.save(update_fields=["last_subtopic", "last_accessed_at", "enrollment", "updated_at"])

    content = getattr(subtopic, "content", None)
    payload: dict[str, Any] = {
        "subtopic": {
            "id": str(subtopic.id),
            "title": subtopic.title,
            "kind": subtopic.kind,
            "description_json": subtopic.description_json,
            "estimated_time_s": subtopic.estimated_time_s,
            "min_time_s": subtopic.min_time_s,
            "require_full_watch": subtopic.require_full_watch,
            "is_free_preview": subtopic.is_free_preview,
        },
        "subject": {
            "id": str(subject.id),
            "title": subject.title,
            "slug": subject.slug,
            "description_json": subject.description_json,
        },
        "progress": {
            "status": ip.status,
            "percent": ip.percent,
            "time_spent_s": ip.time_spent_s,
            "completed": ip.status == ProgressStatus.COMPLETED,
            "min_time_s": subtopic.min_time_s,
            "can_complete": ip.time_spent_s >= subtopic.min_time_s
            or ip.status == ProgressStatus.COMPLETED,
        },
        "content": None,
        "resources": [
            {
                "id": str(r.id),
                "title": r.title,
                "kind": r.kind,
                "url": r.url,
                "file_url": r.file.url if r.file else None,
                "download_allowed": r.download_allowed,
            }
            for r in subtopic.resources.all()
        ],
        "video_progress": None,
    }

    if content:
        block: dict[str, Any] = {
            "content_type": content.content_type,
            "title": content.title,
            "body_json": content.body_json,
            "external_url": content.external_url,
            "processing_status": content.processing_status,
            "duration_s": content.duration_s,
            "mime_type": content.mime_type,
            "metadata": content.metadata or {},
            "file_url": None,
            "preview_url": None,
            "playback": None,
        }
        object_key = (content.metadata or {}).get("object_key")
        preview_key = (content.metadata or {}).get("preview_object_key")
        try:
            if content.file:
                block["file_url"] = content.file.url
            elif object_key:
                block["file_url"] = storage.create_presigned_get(object_key=object_key)
            if content.preview_file:
                block["preview_url"] = content.preview_file.url
            elif preview_key:
                block["preview_url"] = storage.create_presigned_get(object_key=preview_key)
        except Exception:  # noqa: BLE001
            pass

        if content.content_type in {ContentType.VIDEO, ContentType.VIDEO_SLIDES} and content.video_asset:
            asset = content.video_asset
            playback = {"playback_id": asset.playback_id, "token": None, "status": asset.status}
            if asset.playback_id:
                try:
                    playback["token"] = mux.sign_playback_id(asset.playback_id)
                except MuxError:
                    # public policy or missing signing keys — still return playback_id
                    playback["token"] = asset.playback_id
            block["playback"] = playback
            block["video_asset_id"] = str(asset.id)
            vp = VideoProgress.objects.filter(user=user, subtopic=subtopic).first()
            if vp:
                resume = max(0, vp.last_position_s - 3) if vp.watched_pct < 98 else 0
                payload["video_progress"] = {
                    "last_position_s": vp.last_position_s,
                    "resume_position_s": resume,
                    "furthest_position_s": vp.furthest_position_s,
                    "watched_pct": vp.watched_pct,
                    "playback_rate": vp.playback_rate,
                }
        payload["content"] = block

    # neighbors
    ordered = list(
        Subtopic.objects.filter(topic__subject=subject, is_published=True)
        .order_by("topic__order", "order")
        .values_list("id", flat=True)
    )
    ids = [str(x) for x in ordered]
    idx = ids.index(str(subtopic.id)) if str(subtopic.id) in ids else -1
    payload["prev_subtopic_id"] = ids[idx - 1] if idx > 0 else None
    payload["next_subtopic_id"] = ids[idx + 1] if 0 <= idx < len(ids) - 1 else None
    return payload


@transaction.atomic
def heartbeat(*, user, subtopic_id: str, delta_s: int = 5, position_s: int | None = None) -> ItemProgress:
    try:
        subtopic = Subtopic.objects.select_related("topic__subject").get(id=subtopic_id)
    except Subtopic.DoesNotExist as exc:
        raise LearningError("Subtopic not found.", code="not_found") from exc
    enrollment = assert_subtopic_access(user=user, subtopic=subtopic)
    delta = max(0, min(int(delta_s), 30))  # clamp burst
    ip, _ = ItemProgress.objects.select_for_update().get_or_create(
        user=user, subtopic=subtopic, defaults={"enrollment": enrollment}
    )
    ip.time_spent_s += delta
    ip.last_active_at = timezone.now()
    if ip.status not in {ProgressStatus.COMPLETED}:
        ip.status = ProgressStatus.IN_PROGRESS
    ip.save()

    if position_s is not None and hasattr(subtopic, "content") and subtopic.content:
        content = subtopic.content
        if content.content_type in {ContentType.VIDEO, ContentType.VIDEO_SLIDES}:
            vp, _ = VideoProgress.objects.get_or_create(user=user, subtopic=subtopic)
            pos = max(0, int(position_s))
            if pos >= vp.last_position_s or True:
                # last-write for position; furthest is monotonic
                vp.last_position_s = pos
                vp.furthest_position_s = max(vp.furthest_position_s, pos)
                duration = content.duration_s or (content.video_asset.duration_s if content.video_asset_id else 0)
                if duration:
                    vp.watched_pct = min(100, int(round((vp.furthest_position_s / duration) * 100)))
                vp.save()
                # auto-complete on watch threshold
                if (
                    subtopic.require_full_watch
                    and vp.watched_pct >= WATCH_COMPLETE_PCT
                    and ip.time_spent_s >= subtopic.min_time_s
                ):
                    try:
                        complete_subtopic(user=user, subtopic_id=str(subtopic.id), force=False)
                        ip.refresh_from_db()
                    except LearningError:
                        pass
    recompute_subject_progress(user=user, subject=subtopic.topic.subject, enrollment=enrollment)
    return ip


@transaction.atomic
def upsert_video_progress(
    *,
    user,
    subtopic_id: str,
    position_s: int,
    duration_s: int = 0,
    rate: float = 1.0,
    segments: list | None = None,
    device_id: str = "",
    client_ts: int = 0,
) -> VideoProgress:
    try:
        subtopic = Subtopic.objects.select_related("topic__subject", "content").get(id=subtopic_id)
    except Subtopic.DoesNotExist as exc:
        raise LearningError("Subtopic not found.", code="not_found") from exc
    assert_subtopic_access(user=user, subtopic=subtopic)
    vp, _ = VideoProgress.objects.select_for_update().get_or_create(user=user, subtopic=subtopic)
    if client_ts and vp.client_ts and client_ts < vp.client_ts:
        return vp
    pos = max(0, int(position_s))
    vp.last_position_s = pos
    vp.furthest_position_s = max(vp.furthest_position_s, pos)
    vp.playback_rate = float(rate or 1.0)
    vp.device_id = device_id or vp.device_id
    vp.client_ts = client_ts or vp.client_ts
    if segments:
        vp.watched_segments = segments
    dur = duration_s or (
        subtopic.content.duration_s
        if hasattr(subtopic, "content") and subtopic.content
        else 0
    )
    if dur:
        vp.watched_pct = min(100, int(round((vp.furthest_position_s / dur) * 100)))
    if hasattr(subtopic, "content") and subtopic.content and subtopic.content.video_asset_id:
        vp.video_asset_id = subtopic.content.video_asset_id
    vp.save()
    return vp


@transaction.atomic
def complete_subtopic(*, user, subtopic_id: str, force: bool = False) -> ItemProgress:
    try:
        subtopic = Subtopic.objects.select_related("topic__subject").get(id=subtopic_id)
    except Subtopic.DoesNotExist as exc:
        raise LearningError("Subtopic not found.", code="not_found") from exc
    enrollment = assert_subtopic_access(user=user, subtopic=subtopic)
    ip, _ = ItemProgress.objects.select_for_update().get_or_create(
        user=user, subtopic=subtopic, defaults={"enrollment": enrollment}
    )
    if ip.status == ProgressStatus.COMPLETED:
        return ip
    if not force and ip.time_spent_s < subtopic.min_time_s:
        raise LearningError(
            f"Minimum study time not met ({ip.time_spent_s}/{subtopic.min_time_s}s).",
            code="study_time_gate",
        )
    if subtopic.require_full_watch and not force:
        vp = VideoProgress.objects.filter(user=user, subtopic=subtopic).first()
        if not vp or vp.watched_pct < WATCH_COMPLETE_PCT:
            raise LearningError(
                "Watch at least 90% of the video before completing.",
                code="watch_gate",
            )
    ip.status = ProgressStatus.COMPLETED
    ip.percent = 100
    ip.completed_at = timezone.now()
    ip.last_active_at = timezone.now()
    ip.save()
    recompute_subject_progress(user=user, subject=subtopic.topic.subject, enrollment=enrollment)
    try:
        from apps.certificates.services import try_auto_issue_for_subject

        try_auto_issue_for_subject(user=user, subject=subtopic.topic.subject)
    except Exception:  # noqa: BLE001
        pass
    return ip


def list_questions(*, subject_id: str, subtopic_id: str | None = None, q: str = ""):
    qs = Question.objects.filter(subject_id=subject_id).select_related("author").prefetch_related("answers__author")
    if subtopic_id:
        qs = qs.filter(Q(subtopic_id=subtopic_id) | Q(subtopic__isnull=True))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
    return qs


def create_question(*, user, subject: Subject, title: str, body: str, subtopic: Subtopic | None = None) -> Question:
    assert_subject_access(user=user, subject=subject)
    return Question.objects.create(
        subject=subject, subtopic=subtopic, author=user, title=title, body=body
    )


def create_answer(*, user, question: Question, body: str) -> Answer:
    assert_subject_access(user=user, subject=question.subject)
    is_instructor = question.subject.instructors.filter(id=user.id).exists() or user.is_staff
    answer = Answer.objects.create(
        question=question, author=user, body=body, is_instructor=is_instructor
    )
    if is_instructor:
        question.is_resolved = True
        question.save(update_fields=["is_resolved", "updated_at"])
    return answer


def list_notes(*, user, subtopic_id: str):
    assert_subtopic_access(user=user, subtopic=Subtopic.objects.get(id=subtopic_id))
    return Note.objects.filter(user=user, subtopic_id=subtopic_id)


def upsert_note(*, user, subtopic_id: str, body: str, timestamp_s: int | None = None, note_id: str | None = None) -> Note:
    subtopic = Subtopic.objects.get(id=subtopic_id)
    assert_subtopic_access(user=user, subtopic=subtopic)
    if note_id:
        note = Note.objects.get(id=note_id, user=user)
        note.body = body
        note.timestamp_s = timestamp_s
        note.save()
        return note
    return Note.objects.create(user=user, subtopic=subtopic, body=body, timestamp_s=timestamp_s)


def delete_note(*, user, note_id: str) -> None:
    Note.objects.filter(id=note_id, user=user).delete()
