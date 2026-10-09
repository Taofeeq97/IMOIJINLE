from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit
from apps.courses.models import (
    ContentType,
    ProcessingStatus,
    Subject,
    SubjectPreviewToken,
    SubjectStatus,
    Subtopic,
    SubtopicContent,
    SubtopicKind,
    SubtopicResource,
    Topic,
    UploadSession,
    VideoAsset,
)

# Soft quality bar (warn, do not block publish unless org requires)
QUALITY_BAR = {
    "min_topics": 1,
    "min_subtopics": 1,
    "min_learn_objectives": 4,
    "min_video_minutes": 0,
}

SIZE_LIMITS = {
    ContentType.VIDEO: 4 * 1024 * 1024 * 1024,
    ContentType.VIDEO_SLIDES: 4 * 1024 * 1024 * 1024,
    ContentType.PDF: 100 * 1024 * 1024,
    ContentType.SPREADSHEET: 100 * 1024 * 1024,
    ContentType.DOCUMENT: 100 * 1024 * 1024,
    ContentType.PRESENTATION: 100 * 1024 * 1024,
    ContentType.AUDIO: 500 * 1024 * 1024,
    ContentType.IMAGE: 20 * 1024 * 1024,
}


class CourseError(Exception):
    def __init__(self, message: str, code: str = "course_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def subject_checklist(subject: Subject) -> dict[str, Any]:
    learners = subject.intended_learners or {}
    learn = learners.get("learn") or []
    requirements = learners.get("requirements") or []
    audience = learners.get("audience") or []
    topics = list(subject.topics.prefetch_related("subtopics__content", "subtopics__resources"))
    subtopics = [s for t in topics for s in t.subtopics.all()]
    with_content = [
        s
        for s in subtopics
        if hasattr(s, "content")
        and s.content
        and s.content.processing_status in {ProcessingStatus.READY, ProcessingStatus.CONVERTED}
    ]
    video_seconds = sum(
        (s.content.duration_s or 0)
        for s in with_content
        if s.content.content_type in {ContentType.VIDEO, ContentType.VIDEO_SLIDES}
    )
    desc = subject.description_json or {}
    has_description = bool(desc.get("html") or desc.get("text") or desc.get("type"))
    pricing = subject.pricing or {}
    pricing_ok = bool(pricing.get("mode"))
    messages_ok = bool(subject.welcome_message.strip()) and bool(subject.completion_message.strip())
    landing_ok = bool(subject.title) and bool(subject.subtitle) and has_description

    items = {
        "intended_learners": len(learn) >= QUALITY_BAR["min_learn_objectives"]
        and len(requirements) >= 1
        and len(audience) >= 1,
        "subject_structure": len(topics) >= QUALITY_BAR["min_topics"]
        and len(subtopics) >= QUALITY_BAR["min_subtopics"],
        "setup_test_video": any(
            hasattr(s, "content")
            and s.content
            and s.content.content_type in {ContentType.VIDEO, ContentType.VIDEO_SLIDES}
            for s in subtopics
        ),
        "film_edit": len(with_content) > 0,
        "curriculum": len(topics) >= 1 and all(t.subtopics.exists() for t in topics),
        "captions": True,  # optional
        "accessibility": True,  # optional soft
        "landing_page": landing_ok,
        "pricing": pricing_ok or True,  # default free allowed
        "promotions": True,  # optional
        "messages": messages_ok,
        "settings": bool(subject.settings is not None),
    }
    required = [
        "subject_structure",
        "curriculum",
    ]
    missing = [k for k in required if not items.get(k)]
    warnings = []
    if not items["intended_learners"]:
        warnings.append(
            f"Add at least {QUALITY_BAR['min_learn_objectives']} learning objectives plus requirements and audience."
        )
    if not items["landing_page"]:
        warnings.append("Complete landing page title, subtitle, and description before go-live.")
    if len(with_content) < len([s for s in subtopics if s.kind == SubtopicKind.SUBTOPIC]):
        warnings.append("Some lesson subtopics are missing content.")
    if video_seconds // 60 < QUALITY_BAR["min_video_minutes"]:
        warnings.append("Video minutes below quality bar (warning only).")

    completed = sum(1 for v in items.values() if v)
    return {
        "status": subject.status,
        "items": items,
        "required": required,
        "missing": missing,
        "warnings": warnings,
        "progress": {"completed": completed, "total": len(items)},
        "stats": {
            "topics": len(topics),
            "subtopics": len(subtopics),
            "with_content": len(with_content),
            "video_minutes": video_seconds // 60,
        },
        "can_publish": len(missing) == 0,
    }


@transaction.atomic
def publish_subject(*, subject: Subject, actor, request=None, force: bool = False) -> Subject:
    checklist = subject_checklist(subject)
    if not checklist["can_publish"] and not force:
        raise CourseError(
            "Publish checklist incomplete: " + ", ".join(checklist["missing"]),
            code="checklist_incomplete",
        )
    before = {"status": subject.status}
    subject.status = SubjectStatus.PUBLISHED
    subject.version = (subject.version or 1) + 1
    subject.save(update_fields=["status", "version", "updated_at"])
    # Publish curriculum tree
    for topic in subject.topics.all():
        topic.is_published = True
        topic.save(update_fields=["is_published", "updated_at"])
        for sub in topic.subtopics.all():
            sub.is_published = True
            sub.save(update_fields=["is_published", "updated_at"])
    log_audit(
        actor=actor,
        action="subject.publish",
        obj=subject,
        before=before,
        after={"status": subject.status, "checklist": checklist["items"]},
        request=request,
    )
    return subject


def create_preview_token(*, subject: Subject, actor, request=None) -> tuple[str, SubjectPreviewToken]:
    raw = secrets.token_urlsafe(32)
    token = SubjectPreviewToken.objects.create(
        subject=subject,
        token_hash=_hash_token(raw),
        created_by=actor,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    log_audit(actor=actor, action="subject.preview_token", obj=subject, request=request)
    return raw, token


def resolve_preview_token(*, token: str, subject_id: str) -> Subject:
    try:
        row = SubjectPreviewToken.objects.select_related("subject").get(
            subject_id=subject_id, token_hash=_hash_token(token)
        )
    except SubjectPreviewToken.DoesNotExist as exc:
        raise CourseError("Invalid preview token.", code="invalid_token") from exc
    if row.expires_at < timezone.now():
        raise CourseError("Preview token expired.", code="expired")
    return row.subject


def create_upload_session(
    *,
    user,
    purpose: str,
    filename: str,
    mime_type: str = "",
    size_bytes: int = 0,
    subtopic: Subtopic | None = None,
) -> dict[str, Any]:
    from apps.integrations import storage
    from apps.integrations.storage import StorageError

    key = f"uploads/{user.id}/{uuid.uuid4().hex}_{filename}"
    session = UploadSession.objects.create(
        user=user,
        purpose=purpose,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        object_key=key,
        subtopic=subtopic,
        status=ProcessingStatus.UPLOADING,
    )
    try:
        presign = storage.create_presigned_put(
            object_key=key,
            content_type=mime_type or "application/octet-stream",
            expires_in=3600,
            max_bytes=size_bytes or None,
        )
    except StorageError as exc:
        session.status = ProcessingStatus.ERRORED
        session.error_message = exc.message
        session.save(update_fields=["status", "error_message", "updated_at"])
        raise CourseError(exc.message, code=exc.code) from exc

    return {
        "upload_id": str(session.id),
        "object_key": key,
        "upload_url": presign["upload_url"],
        "method": presign["method"],
        "headers": presign["headers"],
        "expires_in": presign["expires_in"],
        "bucket": presign["bucket"],
    }


def complete_upload(*, session: UploadSession, actor=None, request=None) -> UploadSession:
    """Confirm the client finished the S3/MinIO PUT for this session."""
    from apps.integrations import storage
    from apps.integrations.storage import StorageError

    if session.status == ProcessingStatus.READY:
        return session
    try:
        meta = storage.head_object(object_key=session.object_key)
    except StorageError as exc:
        raise CourseError(exc.message, code=exc.code) from exc
    except Exception as exc:  # noqa: BLE001
        raise CourseError(
            "Upload not found in object storage. Complete the PUT to the presigned URL first.",
            code="upload_missing",
        ) from exc

    session.size_bytes = int(meta.get("ContentLength") or session.size_bytes or 0)
    session.mime_type = meta.get("ContentType") or session.mime_type
    session.status = ProcessingStatus.READY
    session.metadata = {**(session.metadata or {}), "etag": meta.get("ETag"), "storage": "s3"}
    session.save()
    log_audit(
        actor=actor or session.user,
        action="upload.complete",
        obj=session,
        after={"filename": session.filename, "size_bytes": session.size_bytes, "object_key": session.object_key},
        request=request,
    )
    return session


def create_mux_direct_upload(
    *,
    subtopic: Subtopic,
    actor,
    cors_origin: str,
    request=None,
) -> dict[str, Any]:
    from apps.integrations import mux
    from apps.integrations.mux import MuxError

    try:
        data = mux.create_direct_upload(
            cors_origin=cors_origin,
            passthrough=str(subtopic.id),
        )
    except MuxError as exc:
        raise CourseError(exc.message, code=exc.code) from exc

    asset = VideoAsset.objects.create(
        provider="mux",
        provider_asset_id="",
        playback_id="",
        status=ProcessingStatus.UPLOADING,
        raw={"upload": data},
    )
    content, _ = SubtopicContent.objects.get_or_create(
        subtopic=subtopic,
        defaults={"content_type": ContentType.VIDEO},
    )
    content.content_type = ContentType.VIDEO
    content.video_asset = asset
    content.processing_status = ProcessingStatus.UPLOADING
    content.metadata = {
        **(content.metadata or {}),
        "mux_upload_id": data.get("id"),
    }
    content.save()
    log_audit(
        actor=actor,
        action="subtopic.mux_upload.create",
        obj=subtopic,
        after={"upload_id": data.get("id")},
        request=request,
    )
    return {
        "upload_id": data.get("id"),
        "upload_url": data.get("url"),
        "video_asset_id": str(asset.id),
        "content_id": str(content.id),
        "status": data.get("status"),
    }


def queue_document_conversion(content: SubtopicContent) -> None:
    from apps.integrations.tasks import convert_subtopic_content_task

    content.processing_status = ProcessingStatus.PROCESSING
    content.save(update_fields=["processing_status", "updated_at"])
    convert_subtopic_content_task.delay(str(content.id))


@transaction.atomic
def set_subtopic_content(
    *,
    subtopic: Subtopic,
    content_type: str,
    actor,
    title: str = "",
    body_json: dict | None = None,
    external_url: str = "",
    upload_id: str | None = None,
    mux_upload_id: str | None = None,
    video_asset_id: str | None = None,
    duration_s: int = 0,
    metadata: dict | None = None,
    request=None,
) -> SubtopicContent:
    if content_type not in ContentType.values:
        raise CourseError("Unsupported content type.", code="invalid_type")

    upload: UploadSession | None = None
    if upload_id:
        try:
            upload = UploadSession.objects.get(id=upload_id, status=ProcessingStatus.READY)
        except UploadSession.DoesNotExist as exc:
            raise CourseError("Upload not found or not ready.", code="upload_missing") from exc
        limit = SIZE_LIMITS.get(content_type)
        if limit and upload.size_bytes > limit:
            raise CourseError("File exceeds size limit for this type.", code="size_limit")

    content, _created = SubtopicContent.objects.get_or_create(
        subtopic=subtopic,
        defaults={"content_type": content_type},
    )
    content.content_type = content_type
    content.title = title or content.title
    content.body_json = body_json if body_json is not None else content.body_json
    content.external_url = external_url or content.external_url
    content.duration_s = duration_s or content.duration_s
    content.metadata = {**(content.metadata or {}), **(metadata or {})}
    content.processing_status = ProcessingStatus.READY

    if upload:
        content.mime_type = upload.mime_type
        content.size_bytes = upload.size_bytes
        content.metadata = {**(content.metadata or {}), "object_key": upload.object_key}
        upload.subtopic = subtopic
        upload.save(update_fields=["subtopic", "updated_at"])
        # Keep a Django FileField reference via storage key when using S3 default storage
        if upload.file:
            content.file = upload.file

    if content_type in {ContentType.VIDEO, ContentType.VIDEO_SLIDES}:
        asset = None
        if video_asset_id:
            asset = VideoAsset.objects.filter(id=video_asset_id).first()
        if asset is None and content.video_asset_id:
            asset = content.video_asset
        if asset is None:
            asset = VideoAsset.objects.create(
                provider="mux",
                status=ProcessingStatus.UPLOADING if mux_upload_id else ProcessingStatus.PROCESSING,
                raw={"mux_upload_id": mux_upload_id} if mux_upload_id else {},
            )
        if mux_upload_id:
            asset.raw = {**(asset.raw or {}), "mux_upload_id": mux_upload_id}
            asset.status = ProcessingStatus.UPLOADING
            asset.provider = "mux"
            asset.save()
            content.processing_status = ProcessingStatus.UPLOADING
            content.metadata = {**(content.metadata or {}), "mux_upload_id": mux_upload_id}
        content.video_asset = asset
        if duration_s:
            asset.duration_s = duration_s
            asset.save(update_fields=["duration_s", "updated_at"])
            content.duration_s = duration_s
        if not subtopic.estimated_time_s and content.duration_s:
            subtopic.estimated_time_s = content.duration_s
            subtopic.save(update_fields=["estimated_time_s", "updated_at"])

    if content_type == ContentType.ARTICLE and not content.body_json:
        content.body_json = {"type": "doc", "html": "<p></p>"}

    if content_type == ContentType.LINK and not content.external_url:
        raise CourseError("Link content requires external_url.", code="validation_error")

    if content_type == ContentType.LIVE:
        content.metadata = {
            **(content.metadata or {}),
            "join_url": external_url or content.external_url,
        }

    content.save()

    if content_type in {
        ContentType.DOCUMENT,
        ContentType.PRESENTATION,
        ContentType.SPREADSHEET,
        ContentType.PDF,
    }:
        queue_document_conversion(content)

    log_audit(
        actor=actor,
        action="subtopic.content.set",
        obj=subtopic,
        after={"content_type": content_type, "status": content.processing_status},
        request=request,
    )
    return content


def add_resource(
    *,
    subtopic: Subtopic,
    kind: str,
    title: str,
    actor,
    url: str = "",
    upload_id: str | None = None,
    request=None,
) -> SubtopicResource:
    upload = None
    if upload_id:
        try:
            upload = UploadSession.objects.get(id=upload_id, status=ProcessingStatus.READY)
        except UploadSession.DoesNotExist as exc:
            raise CourseError("Upload not found or not ready.", code="upload_missing") from exc
    order = subtopic.resources.count()
    resource = SubtopicResource.objects.create(
        subtopic=subtopic,
        kind=kind,
        title=title,
        url=url,
        order=order,
    )
    if upload and upload.file:
        resource.file = upload.file
        resource.save(update_fields=["file", "updated_at"])
    log_audit(actor=actor, action="subtopic.resource.add", obj=resource, request=request)
    return resource


@transaction.atomic
def duplicate_topic(*, topic: Topic, actor=None, request=None) -> Topic:
    subject = topic.subject
    clone = Topic.objects.create(
        subject=subject,
        title=f"{topic.title} (copy)",
        objective_text=topic.objective_text,
        order=subject.topics.count(),
        is_published=False,
    )
    for sub in topic.subtopics.all():
        duplicate_subtopic(subtopic=sub, target_topic=clone, actor=actor, request=request)
    log_audit(actor=actor, action="topic.duplicate", obj=clone, after={"source": str(topic.id)}, request=request)
    return clone


@transaction.atomic
def duplicate_subtopic(
    *, subtopic: Subtopic, target_topic: Topic | None = None, actor=None, request=None
) -> Subtopic:
    topic = target_topic or subtopic.topic
    clone = Subtopic.objects.create(
        topic=topic,
        title=f"{subtopic.title} (copy)",
        order=topic.subtopics.count(),
        kind=subtopic.kind,
        is_published=False,
        is_free_preview=subtopic.is_free_preview,
        estimated_time_s=subtopic.estimated_time_s,
        min_time_s=subtopic.min_time_s,
        description_json=subtopic.description_json,
        drip_rule=subtopic.drip_rule,
        unlock_rule=subtopic.unlock_rule,
        require_full_watch=subtopic.require_full_watch,
    )
    if hasattr(subtopic, "content") and subtopic.content:
        src = subtopic.content
        SubtopicContent.objects.create(
            subtopic=clone,
            content_type=src.content_type,
            title=src.title,
            body_json=src.body_json,
            file=src.file,
            preview_file=src.preview_file,
            external_url=src.external_url,
            mime_type=src.mime_type,
            size_bytes=src.size_bytes,
            processing_status=src.processing_status,
            video_asset=src.video_asset,
            duration_s=src.duration_s,
            thumbnail_url=src.thumbnail_url,
            metadata=src.metadata,
        )
    for res in subtopic.resources.all():
        SubtopicResource.objects.create(
            subtopic=clone,
            kind=res.kind,
            title=res.title,
            file=res.file,
            url=res.url,
            order=res.order,
            download_allowed=res.download_allowed,
        )
    log_audit(actor=actor, action="subtopic.duplicate", obj=clone, after={"source": str(subtopic.id)}, request=request)
    return clone


def curriculum_tree(subject: Subject) -> list[dict[str, Any]]:
    tree = []
    for topic in subject.topics.prefetch_related("subtopics__content", "subtopics__resources"):
        subs = []
        for sub in topic.subtopics.all():
            content = getattr(sub, "content", None)
            subs.append(
                {
                    "id": str(sub.id),
                    "title": sub.title,
                    "order": sub.order,
                    "kind": sub.kind,
                    "is_published": sub.is_published,
                    "is_free_preview": sub.is_free_preview,
                    "estimated_time_s": sub.estimated_time_s,
                    "min_time_s": sub.min_time_s,
                    "require_full_watch": sub.require_full_watch,
                    "has_content": bool(content),
                    "content_type": content.content_type if content else None,
                    "content_status": content.processing_status if content else None,
                    "resource_count": sub.resources.count(),
                }
            )
        tree.append(
            {
                "id": str(topic.id),
                "title": topic.title,
                "objective_text": topic.objective_text,
                "order": topic.order,
                "is_published": topic.is_published,
                "subtopics": subs,
            }
        )
    return tree
