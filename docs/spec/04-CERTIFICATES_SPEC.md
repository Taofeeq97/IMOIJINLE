# 04 — Certificates Specification

## 1. Goals
Admins design certificates visually, **preview with sample or real student data before saving**, version them, bind them to programs/classes via issue rules, auto/manual issue, and publicly verify.

## 2. Data model
- `CertificateTemplate(name, slug, status[draft|published|archived], current_version FK, orientation[landscape|portrait], page_size[A4|Letter|custom{w,h,unit}], created_by)`
- `CertificateTemplateVersion(template, version_no, design JSON, thumbnail, created_by, created_at, note)` — immutable once published; edits create a new version.
- `CertificateIssueRule(program|class, template, criteria JSON{min_completion_pct, min_grade_pct, required_items[], min_attendance_pct, fees_cleared bool, manual_approval bool}, auto_issue bool, valid_for_days?, numbering_pattern "IMO-{program_code}-{yyyy}-{seq:5}")`
- `Certificate(code unique [short, unambiguous, e.g. 10 chars base32 no 0/O/1/I], enrollment, template_version, issued_at, issued_by|system, status[issued|revoked|reissued], revoked_reason, pdf_file, png_file, data_snapshot JSON, expires_at?)` — **snapshot** ensures later name/grade edits don't silently alter an issued certificate (reissue creates a new record linked by `supersedes`).
- `CertificateVerificationLog(certificate, ip_hash, viewed_at)`.

## 3. Design JSON (renderer-agnostic, versioned `schema_version: 1`)
```json
{
  "schema_version": 1,
  "page": {"size":"A4","orientation":"landscape","width_px":1123,"height_px":794,"bg":{"type":"color|image|gradient","value":"..."}},
  "elements": [
    {"id":"e1","type":"text","x":120,"y":220,"w":880,"h":80,"rotation":0,"z":3,
     "text":"{{student.full_name}}","font":{"family":"Cormorant Garamond","size":54,"weight":600,"italic":false,"color":"#1b2a41","align":"center","lineHeight":1.1,"letterSpacing":0.5,"autoFit":true},"locked":false,"visible":true},
    {"id":"e2","type":"image","src":"asset_id","x":..,"fit":"contain","opacity":1},
    {"id":"e3","type":"shape","shape":"rect|line|ellipse|border-ornament","fill":"","stroke":"","strokeWidth":2,"radius":0},
    {"id":"e4","type":"qr","data":"{{certificate.verify_url}}","size":110,"fg":"#000","bg":"#fff"},
    {"id":"e5","type":"signature","asset_id":"...","caption":"Director, Imo Ijinle Academy"}
  ]
}
```
Placeholders (Mustache-style, allow-listed): `student.full_name`, `student.first_name`, `program.title`, `class.title`, `cohort.name`, `cohort.start_date`, `cohort.end_date`, `completion.date`, `grade.percent`, `grade.letter`, `grade.honours`, `certificate.code`, `certificate.verify_url`, `certificate.issue_date`, `org.name`, `signatory.name`, `signatory.title`, plus date formatting filters (`|date:"DD MMMM YYYY"`) and `|upper`, `|title`.
Missing-data behavior: placeholder renders as empty with a warning in preview ("grade.letter is empty for this student").

## 4. Designer UI (admin) — see UI_SCREENS S-A14
- Canvas editor (Konva.js via `react-konva`, or Fabric.js) with: select/move/resize/rotate, snap-to-grid/guides, align/distribute, layer panel (reorder, lock, hide), zoom/pan, undo/redo (≥ 100 steps), duplicate, keyboard nudge, copy/paste, group.
- Left panel: **Elements** (text, heading, placeholder chips, image, shape, line, border frames, QR, signature), **Templates** (3–4 starter designs: Classic Gold-Border, Modern Minimal, Spiritual Lotus, Academic Seal), **Uploads** (logos, seals, backgrounds, signatures; PNG/SVG/JPG, ≤ 5 MB), **Background**.
- Right panel (contextual): typography (Google Fonts curated list + bundled fonts for PDF parity), color picker with brand swatches, alignment, spacing, opacity, shadow, placeholder inserter.
- Top bar: template name, page setup, **Preview** button, Save draft, **Publish**, version history, export test PDF.
- **Preview modal (mandatory before publish)**: choose data source — Sample data (editable fields) / Real student (search by name, cohort) / Random completed student; shows exact server-rendered output (not just the canvas) with page-size toggle, zoom, download PDF, "Send test to my email". Publish is disabled until a preview of the current version has been generated and no blocking warnings exist (overflowing text, missing required placeholders such as `certificate.code`/QR, low-res images < 150 dpi equivalent, fonts not embeddable).
- Autosave drafts every 5 s (draft versions); unsaved-changes guard.

## 5. Rendering pipeline
- **Single source of truth**: render server-side so preview == final. Convert design JSON → HTML/CSS (absolute positioning in pixels at 96 dpi) → PDF with **Playwright Chromium (preferred)** or WeasyPrint; fonts self-hosted and embedded. PNG via screenshot. Cache by `(version_id, data_hash)`.
- Endpoints: `POST /certificate-templates/{id}/preview {version?, design?, data_source}` (returns signed temp URL for PDF + PNG + warnings; rate-limited; uses unsaved design JSON for live preview), `POST /certificate-templates/{id}/publish`, `POST /certificates/issue {enrollment_ids[], rule_id?}`, `POST /certificates/{id}/revoke|reissue`, `GET /me/certificates`, `GET /certificates/{id}/download?format=pdf|png`.
- Rendering runs in Celery queue `media`; preview uses a short sync path with 10 s timeout & progress state.
- Security: sanitize text, whitelist placeholder keys, block remote URLs in design (assets must be uploaded), sandboxed renderer without network.

## 6. Issuance
- Triggers: grade/completion events, payment cleared, or manual admin action. `evaluate_eligibility(enrollment, rule)` returns `{eligible, reasons[]}` shown to admin ("Missing: Final Quiz ≥ 60 %").
- Modes: auto-issue, queue for approval (admin "Pending certificates" inbox with bulk approve), manual single/bulk.
- Email with PDF link; in-app notification; student "My certificates" wallet with download, share (LinkedIn "Add to profile" URL, copy link), QR.
- Revoke with reason (public page shows "Revoked"). Reissue after name correction.

## 7. Public verification
`/verify/[code]` (no login): shows certificate holder name, program/class, issue date, status (Valid / Revoked / Expired), issuing org, and a thumbnail; machine-readable JSON-LD (`EducationalOccupationalCredential`) and Open Graph image; `GET /public/certificates/verify/{code}` throttled; no PII beyond name & credential.

## 8. Acceptance
1. Admin builds a design, preview with real student renders pixel-identical to issued PDF.
2. Cannot publish without preview; warnings block when blocking.
3. Editing a published template creates v2; already-issued certificates keep v1 snapshot.
4. Bulk issue 500 certificates completes asynchronously with progress and per-row failures reported.
5. QR scans resolve to the verify page; revoked certificate shows revoked.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
