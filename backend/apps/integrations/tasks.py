from __future__ import annotations

import logging

from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, queue="media", max_retries=3, default_retry_delay=30)
def convert_subtopic_content_task(self, content_id: str) -> dict:
    from apps.courses.models import ContentType, ProcessingStatus, SubtopicContent
    from apps.integrations import documents, storage

    try:
        content = SubtopicContent.objects.select_related("subtopic").get(id=content_id)
    except SubtopicContent.DoesNotExist:
        return {"ok": False, "reason": "missing"}

    if content.content_type not in {
        ContentType.DOCUMENT,
        ContentType.PRESENTATION,
        ContentType.SPREADSHEET,
        ContentType.PDF,
    }:
        return {"ok": True, "skipped": True}

    content.processing_status = ProcessingStatus.PROCESSING
    content.save(update_fields=["processing_status", "updated_at"])

    try:
        object_key = (content.metadata or {}).get("object_key") or ""
        if object_key:
            raw = storage.download_bytes(object_key=object_key)
            filename = object_key.rsplit("/", 1)[-1]
        elif content.file:
            content.file.open("rb")
            raw = content.file.read()
            filename = content.file.name.rsplit("/", 1)[-1]
            content.file.close()
        else:
            raise ValueError("No source file for conversion")

        if content.content_type == ContentType.PDF:
            preview_bytes = raw
            viewer = "pdf.js"
        else:
            preview_bytes = documents.convert_office_to_pdf(filename=filename, data=raw)
            viewer = "pdf.js"

        preview_key = f"content/preview/{content.id}.pdf"
        storage.upload_bytes(
            object_key=preview_key, data=preview_bytes, content_type="application/pdf"
        )
        content.preview_file.save(f"{content.id}.pdf", ContentFile(preview_bytes), save=False)
        content.processing_status = ProcessingStatus.CONVERTED
        content.metadata = {
            **(content.metadata or {}),
            "conversion": "gotenberg_libreoffice",
            "viewer": viewer,
            "preview_object_key": preview_key,
        }
        content.save()
        return {"ok": True, "content_id": str(content.id), "preview_key": preview_key}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document conversion failed for %s", content_id)
        content.processing_status = ProcessingStatus.ERRORED
        content.metadata = {**(content.metadata or {}), "conversion_error": str(exc)}
        content.save(update_fields=["processing_status", "metadata", "updated_at"])
        raise self.retry(exc=exc) from exc


@shared_task(queue="media")
def sync_mux_asset_task(video_asset_id: str) -> dict:
    from apps.courses.models import ProcessingStatus, VideoAsset
    from apps.integrations import mux

    asset = VideoAsset.objects.get(id=video_asset_id)
    if not asset.provider_asset_id:
        return {"ok": False, "reason": "no_asset_id"}
    data = mux.get_asset(asset.provider_asset_id)
    status = (data.get("status") or "").lower()
    playback_ids = data.get("playback_ids") or []
    playback_id = ""
    if playback_ids:
        playback_id = playback_ids[0].get("id") or ""
    asset.playback_id = playback_id or asset.playback_id
    asset.duration_s = int(float(data.get("duration") or asset.duration_s or 0))
    asset.raw = data
    if status == "ready":
        asset.status = ProcessingStatus.READY
    elif status in {"errored", "error"}:
        asset.status = ProcessingStatus.ERRORED
    else:
        asset.status = ProcessingStatus.PROCESSING
    asset.save()
    return {"ok": True, "status": asset.status, "playback_id": asset.playback_id}
