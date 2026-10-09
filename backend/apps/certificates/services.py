from __future__ import annotations

import hashlib
import html
import re
import secrets
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.admissions.models import Enrollment
from apps.audit.services import log_audit
from apps.certificates.models import (
    Certificate,
    CertificateIssueRule,
    CertificateStatus,
    CertificateTemplate,
    CertificateTemplateVersion,
    CertificateVerificationLog,
    TemplateStatus,
)
from apps.learning.models import SubjectProgress
from apps.payments.models import Invoice, InvoiceStatus

PLACEHOLDER_KEYS = {
    "student.full_name",
    "student.first_name",
    "program.title",
    "class.title",
    "subject.title",
    "cohort.name",
    "cohort.start_date",
    "cohort.end_date",
    "completion.date",
    "grade.percent",
    "grade.letter",
    "grade.honours",
    "certificate.code",
    "certificate.verify_url",
    "certificate.issue_date",
    "org.name",
    "signatory.name",
    "signatory.title",
}

_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)(?:\|([a-zA-Z]+)(?::\"([^\"]*)\")?)?\s*\}\}")


class CertificateError(Exception):
    def __init__(self, message: str, code: str = "certificate_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def default_design(*, orientation: str = "landscape", page_size: str = "A4") -> dict[str, Any]:
    width, height = (1123, 794) if orientation == "landscape" else (794, 1123)
    return {
        "schema_version": 1,
        "page": {
            "size": page_size,
            "orientation": orientation,
            "width_px": width,
            "height_px": height,
            "bg": {"type": "color", "value": "#faf7f0"},
        },
        "elements": [
            {
                "id": "e_title",
                "type": "text",
                "x": 80,
                "y": 80,
                "w": width - 160,
                "h": 60,
                "rotation": 0,
                "z": 2,
                "text": "Certificate of Completion",
                "font": {
                    "family": "Georgia, serif",
                    "size": 42,
                    "weight": 600,
                    "italic": False,
                    "color": "#1b2a41",
                    "align": "center",
                    "lineHeight": 1.1,
                    "letterSpacing": 0.5,
                },
                "visible": True,
            },
            {
                "id": "e_name",
                "type": "text",
                "x": 80,
                "y": 220,
                "w": width - 160,
                "h": 80,
                "rotation": 0,
                "z": 3,
                "text": "{{student.full_name}}",
                "font": {
                    "family": "Georgia, serif",
                    "size": 48,
                    "weight": 600,
                    "italic": False,
                    "color": "#1b2a41",
                    "align": "center",
                    "lineHeight": 1.1,
                    "letterSpacing": 0.5,
                },
                "visible": True,
            },
            {
                "id": "e_body",
                "type": "text",
                "x": 120,
                "y": 340,
                "w": width - 240,
                "h": 100,
                "rotation": 0,
                "z": 2,
                "text": "has successfully completed {{class.title}} — {{subject.title|default}}",
                "font": {
                    "family": "system-ui, sans-serif",
                    "size": 20,
                    "weight": 400,
                    "italic": False,
                    "color": "#334155",
                    "align": "center",
                    "lineHeight": 1.4,
                    "letterSpacing": 0,
                },
                "visible": True,
            },
            {
                "id": "e_border",
                "type": "shape",
                "shape": "rect",
                "x": 24,
                "y": 24,
                "w": width - 48,
                "h": height - 48,
                "rotation": 0,
                "z": 1,
                "fill": "transparent",
                "stroke": "#C8943A",
                "strokeWidth": 4,
                "radius": 8,
                "visible": True,
            },
            {
                "id": "e_code",
                "type": "text",
                "x": 80,
                "y": height - 100,
                "w": 400,
                "h": 40,
                "rotation": 0,
                "z": 3,
                "text": "Code: {{certificate.code}}",
                "font": {
                    "family": "monospace",
                    "size": 14,
                    "weight": 500,
                    "italic": False,
                    "color": "#64748b",
                    "align": "left",
                    "lineHeight": 1.2,
                    "letterSpacing": 0,
                },
                "visible": True,
            },
            {
                "id": "e_qr",
                "type": "qr",
                "x": width - 180,
                "y": height - 170,
                "size": 110,
                "data": "{{certificate.verify_url}}",
                "fg": "#000",
                "bg": "#fff",
                "z": 4,
                "visible": True,
            },
        ],
    }


def generate_certificate_code(length: int = 10) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def unique_certificate_code() -> str:
    for _ in range(20):
        code = generate_certificate_code()
        if not Certificate.objects.filter(code=code).exists():
            return code
    raise CertificateError("Could not allocate certificate code.", code="code_alloc_failed")


def verify_url_for_code(code: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000").rstrip("/")
    return f"{base}/verify/{code}"


def sample_placeholder_data() -> dict[str, Any]:
    code = "SAMPLECODE1"
    return {
        "student": {"full_name": "Ada Lovelace", "first_name": "Ada"},
        "program": {"title": "Foundations Program"},
        "class": {"title": "Foundation Class"},
        "subject": {"title": "Spirit Foundations"},
        "cohort": {
            "name": "Cohort Alpha",
            "start_date": "01 January 2026",
            "end_date": "30 June 2026",
        },
        "completion": {"date": "06 October 2026"},
        "grade": {"percent": "95", "letter": "A", "honours": "Distinction"},
        "certificate": {
            "code": code,
            "verify_url": verify_url_for_code(code),
            "issue_date": "06 October 2026",
        },
        "org": {"name": "Imo Ijinle Academy"},
        "signatory": {"name": "Director", "title": "Director, Imo Ijinle Academy"},
    }


def _nested_get(data: dict[str, Any], dotted: str) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _apply_filter(value: Any, filt: str | None, arg: str | None) -> str:
    text = "" if value is None else str(value)
    if not filt:
        return text
    if filt == "upper":
        return text.upper()
    if filt == "title":
        return text.title()
    if filt in {"date", "default"}:
        return text
    return text


def render_placeholders(text: str, data: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        filt = match.group(2)
        arg = match.group(3)
        allowed = key in PLACEHOLDER_KEYS or key == "subject.title"
        if not allowed:
            warnings.append(f"Unknown placeholder: {key}")
            return ""
        raw = _nested_get(data, key)
        if raw is None or raw == "":
            warnings.append(f"{key} is empty for this student")
            return ""
        return _apply_filter(raw, filt, arg)

    return _PLACEHOLDER_RE.sub(repl, text or ""), warnings


def build_enrollment_data(
    *,
    enrollment: Enrollment,
    code: str = "PREVIEW",
    subject=None,
    issued_at=None,
) -> dict[str, Any]:
    user = enrollment.user
    full_name = f"{user.first_name} {user.last_name}".strip() or user.email
    klass = enrollment.class_ref
    cohort = enrollment.cohort
    when = issued_at or timezone.now()
    date_fmt = when.strftime("%d %B %Y")
    subject_title = getattr(subject, "title", "") if subject else ""
    sp = None
    if subject:
        sp = SubjectProgress.objects.filter(user=user, subject=subject).first()
    return {
        "student": {"full_name": full_name, "first_name": user.first_name or full_name.split()[0]},
        # Legacy template key `program.title` now carries the cohort (academic session) name.
        "program": {"title": cohort.name},
        "class": {"title": klass.name},
        "subject": {"title": subject_title},
        "cohort": {
            "name": cohort.name,
            "start_date": cohort.start_date.strftime("%d %B %Y") if cohort.start_date else "",
            "end_date": cohort.end_date.strftime("%d %B %Y") if cohort.end_date else "",
        },
        "completion": {
            "date": (sp.completed_at.strftime("%d %B %Y") if sp and sp.completed_at else date_fmt)
        },
        "grade": {"percent": "", "letter": "", "honours": ""},
        "certificate": {
            "code": code,
            "verify_url": verify_url_for_code(code),
            "issue_date": date_fmt,
        },
        "org": {"name": "Imo Ijinle Academy"},
        "signatory": {"name": "Director", "title": "Director, Imo Ijinle Academy"},
    }


def _bg_css(bg: dict[str, Any] | None) -> str:
    bg = bg or {"type": "color", "value": "#ffffff"}
    btype = bg.get("type") or "color"
    value = bg.get("value") or "#ffffff"
    if btype == "gradient":
        return f"background:{html.escape(str(value))};"
    if btype == "image":
        src = str(value)
        if src.startswith("http://") or src.startswith("https://"):
            return "background:#ffffff;"
        return f"background-image:url('{html.escape(src)}');background-size:cover;"
    return f"background:{html.escape(str(value))};"


def render_html(design: dict[str, Any], data: dict[str, Any]) -> tuple[str, list[str]]:
    """Render design JSON + placeholder data into an HTML document string."""
    return design_to_html(design, data)


def design_to_html(design: dict[str, Any], data: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    page = design.get("page") or {}
    width = int(page.get("width_px") or 1123)
    height = int(page.get("height_px") or 794)
    elements = sorted(design.get("elements") or [], key=lambda e: int(e.get("z") or 0))

    parts: list[str] = []
    for el in elements:
        if el.get("visible") is False:
            continue
        etype = el.get("type")
        if etype == "text":
            rendered, w = render_placeholders(str(el.get("text") or ""), data)
            warnings.extend(w)
            font = el.get("font") or {}
            style = (
                f"position:absolute;left:{int(el.get('x') or 0)}px;top:{int(el.get('y') or 0)}px;"
                f"width:{int(el.get('w') or 100)}px;height:{int(el.get('h') or 40)}px;"
                f"font-family:{html.escape(str(font.get('family') or 'serif'))};"
                f"font-size:{int(font.get('size') or 16)}px;"
                f"font-weight:{int(font.get('weight') or 400)};"
                f"font-style:{'italic' if font.get('italic') else 'normal'};"
                f"color:{html.escape(str(font.get('color') or '#000'))};"
                f"text-align:{html.escape(str(font.get('align') or 'left'))};"
                f"line-height:{font.get('lineHeight') or 1.2};"
                f"letter-spacing:{font.get('letterSpacing') or 0}px;"
                f"transform:rotate({int(el.get('rotation') or 0)}deg);"
                f"overflow:hidden;z-index:{int(el.get('z') or 1)};"
            )
            parts.append(f'<div style="{style}">{html.escape(rendered)}</div>')
        elif etype == "shape":
            shape = el.get("shape") or "rect"
            fill = el.get("fill") or "transparent"
            stroke = el.get("stroke") or "#000"
            sw = int(el.get("strokeWidth") or 1)
            radius = int(el.get("radius") or 0)
            style = (
                f"position:absolute;left:{int(el.get('x') or 0)}px;top:{int(el.get('y') or 0)}px;"
                f"width:{int(el.get('w') or 100)}px;height:{int(el.get('h') or 40)}px;"
                f"background:{html.escape(str(fill))};border:{sw}px solid {html.escape(str(stroke))};"
                f"border-radius:{radius}px;box-sizing:border-box;"
                f"z-index:{int(el.get('z') or 1)};"
            )
            if shape == "ellipse":
                style += "border-radius:50%;"
            parts.append(f'<div style="{style}"></div>')
        elif etype == "qr":
            raw_data = str(el.get("data") or "{{certificate.verify_url}}")
            rendered, w = render_placeholders(raw_data, data)
            warnings.extend(w)
            size = int(el.get("size") or el.get("w") or 110)
            fg = html.escape(str(el.get("fg") or "#000"))
            bg = html.escape(str(el.get("bg") or "#fff"))
            style = (
                f"position:absolute;left:{int(el.get('x') or 0)}px;top:{int(el.get('y') or 0)}px;"
                f"width:{size}px;height:{size}px;background:{bg};border:2px solid {fg};"
                f"display:flex;align-items:center;justify-content:center;text-align:center;"
                f"font-size:9px;color:{fg};padding:4px;box-sizing:border-box;"
                f"word-break:break-all;z-index:{int(el.get('z') or 1)};"
            )
            parts.append(
                f'<div style="{style}" title="{html.escape(rendered)}">'
                f"<div>QR</div><div>{html.escape(rendered[:48])}</div></div>"
            )
        elif etype == "image":
            src = str(el.get("src") or "")
            if src.startswith("http://") or src.startswith("https://"):
                warnings.append("Remote image URLs are blocked; upload assets instead.")
                continue
            style = (
                f"position:absolute;left:{int(el.get('x') or 0)}px;top:{int(el.get('y') or 0)}px;"
                f"width:{int(el.get('w') or 100)}px;height:{int(el.get('h') or 100)}px;"
                f"object-fit:{html.escape(str(el.get('fit') or 'contain'))};"
                f"opacity:{el.get('opacity') if el.get('opacity') is not None else 1};"
                f"z-index:{int(el.get('z') or 1)};"
            )
            parts.append(f'<img src="{html.escape(src)}" alt="" style="{style}" />')
        elif etype == "signature":
            caption = str(el.get("caption") or "")
            rendered, w = render_placeholders(caption, data)
            warnings.extend(w)
            style = (
                f"position:absolute;left:{int(el.get('x') or 0)}px;top:{int(el.get('y') or 0)}px;"
                f"width:{int(el.get('w') or 200)}px;text-align:center;"
                f"font-size:12px;color:#334155;z-index:{int(el.get('z') or 1)};"
            )
            parts.append(f'<div style="{style}">{html.escape(rendered)}</div>')

    page_style = (
        f"position:relative;width:{width}px;height:{height}px;{_bg_css(page.get('bg'))}"
        f"overflow:hidden;margin:0 auto;"
    )
    body = "\n".join(parts)
    doc = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>Certificate</title></head><body style='margin:0;padding:24px;background:#e2e8f0;'>"
        f"<div class='certificate-page' style=\"{page_style}\">{body}</div>"
        "</body></html>"
    )
    seen: set[str] = set()
    uniq: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    return doc, uniq


def preview_template(
    *,
    template: CertificateTemplate,
    design: dict[str, Any] | None = None,
    data_source: str = "sample",
    enrollment_id: str | None = None,
    subject_id: str | None = None,
    actor=None,
    request=None,
) -> dict[str, Any]:
    design_json = design
    if design_json is None:
        version = template.current_version or template.versions.order_by("-version_no").first()
        if not version:
            design_json = default_design(
                orientation=template.orientation, page_size=template.page_size
            )
        else:
            design_json = version.design

    if data_source == "enrollment" and enrollment_id:
        try:
            enrollment = Enrollment.objects.select_related(
                "user", "class_ref", "cohort", "cohort__program"
            ).get(id=enrollment_id)
        except Enrollment.DoesNotExist as exc:
            raise CertificateError("Enrollment not found.", code="not_found") from exc
        subject = None
        if subject_id:
            from apps.courses.models import Subject

            subject = Subject.objects.filter(id=subject_id).first()
        data = build_enrollment_data(enrollment=enrollment, code="PREVIEW", subject=subject)
    else:
        data = sample_placeholder_data()

    html_doc, warnings = render_html(design_json, data)
    design_hash = hashlib.sha256(
        str(design_json).encode("utf-8") + str(data).encode("utf-8")
    ).hexdigest()
    template.last_previewed_at = timezone.now()
    template.last_preview_hash = design_hash
    template.save(update_fields=["last_previewed_at", "last_preview_hash", "updated_at"])
    log_audit(
        action="certificate.preview",
        actor=actor,
        obj=template,
        after={"hash": design_hash, "warnings": warnings},
        request=request,
    )
    return {
        "html": html_doc,
        "warnings": warnings,
        "data": data,
        "preview_hash": design_hash,
        "blocking": [w for w in warnings if "Unknown placeholder" in w],
    }


def create_template(
    *,
    name: str,
    orientation: str = "landscape",
    page_size: str = "A4",
    design: dict[str, Any] | None = None,
    actor=None,
    request=None,
) -> CertificateTemplate:
    template = CertificateTemplate.objects.create(
        name=name,
        orientation=orientation,
        page_size=page_size,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    version = CertificateTemplateVersion.objects.create(
        template=template,
        version_no=1,
        design=design or default_design(orientation=orientation, page_size=page_size),
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        note="Initial draft",
    )
    template.current_version = version
    template.save(update_fields=["current_version", "updated_at"])
    log_audit(
        action="certificate.template.create",
        actor=actor,
        obj=template,
        after={"name": name, "version_no": 1},
        request=request,
    )
    return template


def save_design(
    *,
    template: CertificateTemplate,
    design: dict[str, Any],
    note: str = "",
    actor=None,
    request=None,
) -> CertificateTemplateVersion:
    current = template.current_version
    if current and not current.is_published and template.status == TemplateStatus.DRAFT:
        current.design = design
        if note:
            current.note = note
        current.save()
        log_audit(
            action="certificate.template.design_save",
            actor=actor,
            obj=template,
            after={"version_no": current.version_no},
            request=request,
        )
        return current

    next_no = (current.version_no + 1) if current else 1
    version = CertificateTemplateVersion.objects.create(
        template=template,
        version_no=next_no,
        design=design,
        note=note or f"Draft v{next_no}",
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        is_published=False,
    )
    template.current_version = version
    if template.status == TemplateStatus.PUBLISHED:
        template.status = TemplateStatus.DRAFT
    template.save(update_fields=["current_version", "status", "updated_at"])
    log_audit(
        action="certificate.template.design_save",
        actor=actor,
        obj=template,
        after={"version_no": version.version_no},
        request=request,
    )
    return version


def publish_template(
    *,
    template: CertificateTemplate,
    actor=None,
    request=None,
    require_preview: bool = True,
) -> CertificateTemplateVersion:
    version = template.current_version
    if not version:
        raise CertificateError("No version to publish.", code="no_version")
    if require_preview and not template.last_previewed_at:
        raise CertificateError(
            "Preview the current design before publishing.", code="preview_required"
        )
    version.is_published = True
    version.save(update_fields=["is_published", "updated_at"])
    template.status = TemplateStatus.PUBLISHED
    template.save(update_fields=["status", "updated_at"])
    log_audit(
        action="certificate.template.publish",
        actor=actor,
        obj=template,
        after={"version_no": version.version_no},
        request=request,
    )
    return version


def _fees_cleared(enrollment: Enrollment) -> bool:
    open_statuses = {InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.DRAFT}
    unpaid = Invoice.objects.filter(status__in=open_statuses).filter(
        Q(enrollment=enrollment)
        | Q(user=enrollment.user, metadata__class_id=str(enrollment.class_ref_id))
    )
    return not unpaid.exists()


def evaluate_eligibility(
    *, enrollment: Enrollment, rule: CertificateIssueRule, subject=None
) -> dict[str, Any]:
    criteria = rule.criteria or {}
    reasons: list[str] = []
    min_pct = int(criteria.get("min_completion_pct") or 100)
    fees_required = bool(criteria.get("fees_cleared"))

    if rule.subject_id:
        subject = subject or rule.subject
        sp = SubjectProgress.objects.filter(user=enrollment.user, subject=subject).first()
        pct = sp.percent if sp else 0
        if pct < min_pct:
            reasons.append(f"Subject completion {pct}% < {min_pct}%")
    elif rule.class_ref_id:
        from apps.programs.models import ClassSubject

        links = ClassSubject.objects.filter(class_ref=rule.class_ref).select_related("subject")
        if not links.exists():
            reasons.append("Class has no subjects")
        else:
            percents = []
            for link in links:
                sp = SubjectProgress.objects.filter(
                    user=enrollment.user, subject=link.subject
                ).first()
                percents.append(sp.percent if sp else 0)
            avg = int(round(sum(percents) / len(percents))) if percents else 0
            if avg < min_pct:
                reasons.append(f"Class completion {avg}% < {min_pct}%")

    if fees_required and not _fees_cleared(enrollment):
        reasons.append("Outstanding fees")

    if criteria.get("manual_approval"):
        reasons.append("Manual approval required")

    return {"eligible": len(reasons) == 0, "reasons": reasons}


@transaction.atomic
def issue_certificate(
    *,
    enrollment: Enrollment,
    rule: CertificateIssueRule | None = None,
    template: CertificateTemplate | None = None,
    subject=None,
    actor=None,
    request=None,
    force: bool = False,
) -> Certificate:
    if rule:
        template = rule.template
        subject = subject or rule.subject
        if not force:
            result = evaluate_eligibility(enrollment=enrollment, rule=rule, subject=subject)
            if not result["eligible"]:
                raise CertificateError(
                    "Not eligible: " + "; ".join(result["reasons"]),
                    code="not_eligible",
                )
    if not template:
        raise CertificateError("Template required.", code="template_required")
    if template.status != TemplateStatus.PUBLISHED or not template.current_version:
        raise CertificateError("Template must be published.", code="template_not_published")
    version = template.current_version
    if not version.is_published:
        version = (
            template.versions.filter(is_published=True).order_by("-version_no").first() or version
        )

    existing_qs = Certificate.objects.filter(
        enrollment=enrollment,
        status=CertificateStatus.ISSUED,
    )
    if rule:
        existing_qs = existing_qs.filter(issue_rule=rule)
    elif subject:
        existing_qs = existing_qs.filter(subject=subject)
    existing = existing_qs.first()
    if existing:
        return existing

    code = unique_certificate_code()
    data = build_enrollment_data(
        enrollment=enrollment, code=code, subject=subject, issued_at=timezone.now()
    )
    html_doc, _warnings = render_html(version.design, data)
    expires_at = None
    if rule and rule.valid_for_days:
        expires_at = timezone.now() + timedelta(days=rule.valid_for_days)

    cert = Certificate.objects.create(
        code=code,
        enrollment=enrollment,
        template_version=version,
        issue_rule=rule,
        subject=subject,
        issued_by=actor if getattr(actor, "is_authenticated", False) else None,
        status=CertificateStatus.ISSUED,
        html_snapshot=html_doc,
        data_snapshot=data,
        expires_at=expires_at,
    )
    log_audit(
        action="certificate.issue",
        actor=actor,
        obj=cert,
        after={"code": code, "enrollment_id": str(enrollment.id)},
        request=request,
    )
    return cert


@transaction.atomic
def revoke_certificate(
    *,
    certificate: Certificate,
    reason: str = "",
    actor=None,
    request=None,
) -> Certificate:
    if certificate.status == CertificateStatus.REVOKED:
        return certificate
    before = {"status": certificate.status}
    certificate.status = CertificateStatus.REVOKED
    certificate.revoked_reason = reason
    certificate.revoked_at = timezone.now()
    certificate.save(update_fields=["status", "revoked_reason", "revoked_at", "updated_at"])
    log_audit(
        action="certificate.revoke",
        actor=actor,
        obj=certificate,
        before=before,
        after={"status": certificate.status, "reason": reason},
        request=request,
    )
    return certificate


def verify_certificate(*, code: str, request=None) -> dict[str, Any]:
    try:
        cert = Certificate.objects.select_related(
            "enrollment__user",
            "enrollment__class_ref",
            "enrollment__cohort",
            "enrollment__cohort__program",
            "subject",
            "template_version__template",
        ).get(code__iexact=code)
    except Certificate.DoesNotExist as exc:
        raise CertificateError("Certificate not found.", code="not_found") from exc

    ip = ""
    ua = ""
    if request is not None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR") or ""
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]
    ip_hash = hashlib.sha256(ip.encode("utf-8")).hexdigest() if ip else ""
    CertificateVerificationLog.objects.create(certificate=cert, ip_hash=ip_hash, user_agent=ua)

    snap = cert.data_snapshot or {}
    student = snap.get("student") or {}
    program = snap.get("program") or {}
    cohort = snap.get("cohort") or {}
    klass = snap.get("class") or {}
    now = timezone.now()
    status = cert.status
    public_status = "valid"
    if status == CertificateStatus.REVOKED:
        public_status = "revoked"
    elif cert.expires_at and cert.expires_at < now:
        public_status = "expired"
    elif status == CertificateStatus.REISSUED:
        public_status = "reissued"

    cohort_title = cohort.get("name") or program.get("title") or ""
    return {
        "code": cert.code,
        "status": public_status,
        "holder_name": student.get("full_name") or "",
        "cohort_title": cohort_title,
        "program_title": cohort_title,  # alias for older clients
        "class_title": klass.get("title") or "",
        "subject_title": (snap.get("subject") or {}).get("title")
        or (cert.subject.title if cert.subject_id else ""),
        "issue_date": (snap.get("certificate") or {}).get("issue_date")
        or (cert.issued_at.strftime("%d %B %Y") if cert.issued_at else ""),
        "org_name": (snap.get("org") or {}).get("name") or "Imo Ijinle Academy",
        "revoked_reason": cert.revoked_reason if public_status == "revoked" else "",
        "verify_url": verify_url_for_code(cert.code),
        "json_ld": {
            "@context": "https://schema.org",
            "@type": "EducationalOccupationalCredential",
            "name": f"Certificate — {klass.get('title') or ''}",
            "credentialCategory": "Certificate of Completion",
            "recognizedBy": {"@type": "Organization", "name": "Imo Ijinle Academy"},
            "identifier": cert.code,
        },
    }


def maybe_auto_issue_on_progress(*, user, subject, enrollment=None) -> list[Certificate]:
    sp = SubjectProgress.objects.filter(user=user, subject=subject).first()
    if not sp or sp.percent < 100:
        return []

    if enrollment is None:
        enrollment = (
            Enrollment.objects.filter(
                user=user,
                status="active",
                class_ref__class_subjects__subject=subject,
            )
            .select_related("class_ref", "cohort", "cohort__program", "user")
            .first()
        )
    if not enrollment:
        return []

    issued: list[Certificate] = []
    rules = (
        CertificateIssueRule.objects.filter(is_active=True, auto_issue=True)
        .filter(
            Q(subject_id=subject.id) | Q(class_ref_id=enrollment.class_ref_id, subject__isnull=True)
        )
        .select_related("template", "subject", "class_ref")
    )
    for rule in rules:
        try:
            cert = issue_certificate(
                enrollment=enrollment, rule=rule, subject=subject, actor=None, force=False
            )
            issued.append(cert)
        except CertificateError:
            continue
    return issued
