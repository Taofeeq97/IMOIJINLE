# 10 — Udemy-Model Course System & Revised Admissions Flow (v1.2)

**PRECEDENCE: this file overrides every earlier file wherever it conflicts** (hierarchy, admissions flow, course authoring UI, student learning UI). Earlier text about Program › Cohort › Class › Session › Item is replaced by §2. All payments, certificates, finance, study-time, responsive and security rules from earlier files still apply and are re-pointed to the new entities (see §3.4).

**Fidelity note:** replicate Udemy's *information architecture, workflows, layouts and interaction patterns* as closely as possible (this is what the client asked for). Do **not** copy Udemy's logo, trademarks, brand name, copy text, illustrations or proprietary assets. Visual identity stays Imo Ijinle (tokens in file 06); §7 defines the Udemy-style layout and a dark "player ink" surface within our tokens.

---
## 1. Revised end-to-end flow (the product's spine)

| # | Actor | Step | System behaviour |
|---|---|---|---|
| 1 | Admin | Creates a **Cohort**: name, description (WYSIWYG), cover image, slug, application window, application fee (from Payment Settings), capacity | Cohort saved as `draft` |
| 2 | Admin | Clicks **Open applications** | Status → `applications_open`; public URL `/apply/[slug]` live; share link + QR shown |
| 3 | Applicant | Opens public URL, fills **application form** (core: full name, email, phone + admin-configured fields), submits | `Application` created (`submitted`); applicant `User` created in state `invited` (no usable password) |
| 4 | Applicant | Sees **success page**: "Application received. We've sent a link to *you@email.com* to continue." (+ resend link, change-email option, spam-folder hint, countdown for resend) | Email job queued |
| 5 | Applicant | Opens **onboarding email**, clicks "Set up your account" | One-time signed link (72 h, resendable) → set-password page |
| 6 | Applicant | Sets password (this is the "temporary password" step: the link carries a one-time token; no plaintext passwords are ever emailed) and is signed in | User → `active`; lands on **Applicant Portal → My Application** |
| 7 | Applicant | **Pays application fee** via Paystack on the application page | Invoice (kind `application`) + payment; webhook confirms; status → `fee_paid` |
| 8 | Admin | Sees the new paid application in **Applications inbox** (badge "Fee paid"), reviews | Notification + dashboard counters |
| 9 | Admin | **Admits applicant to a Class** (one or more) | Enrollment created; invoices for class fees generated; student role granted; welcome email |
| 10 | Student | Sees **My learning** with the admitted class and its subjects (courses); pays class fees if any; starts learning | Udemy-style learning experience (§6) |

**Application statuses**: `submitted` → `account_pending` (email sent, not yet activated) → `account_active` → `fee_pending` (if a fee applies) → `fee_paid` → `under_review` → `admitted` | `waitlisted` | `rejected` | `withdrawn`. If no application fee is configured the flow skips `fee_pending`. Admin can admit at any point after `account_active` (configurable: "Require paid fee before admit", default on).

**Edge cases to implement**
- Email already has an account → don't reveal; send "continue your application" link to that email; one application per email per cohort (resume existing).
- Link expired/used → friendly page with "Send me a new link" (rate-limited, 3/hour).
- Wrong email typed → success page offers "Wrong email? Fix it" before the link is used (resends to corrected address; old link invalidated).
- Email not arriving → resend with cooldown; admin can "Resend onboarding email" and "Copy setup link".
- Applicant leaves before paying → reminder emails (configurable offsets), status page always resumable via login.
- Paystack pop-up closed / failed / pending bank transfer → states per file 03.
- Cohort closed after submit → applicant can still complete payment if configured ("grace for existing applicants").
- Multiple cohorts → one portal listing all applications.

### 1.1 Applicant Portal (new, simple)
Routes: `/portal` (My applications), `/portal/applications/[id]` (status stepper, outstanding actions: Pay application fee, upload documents, complete extra questions), receipts, profile. After admission the portal becomes the student's **My learning** (same account).

### 1.2 Payment Configuration page (admin) — `/admin/settings/payments`
One page, tabs:
1. **Gateway**: Paystack public/secret key status (masked, stored encrypted), test/live mode switch with banner, webhook URL display + "Send test event", connection test, default currency, supported channels toggles (card, bank, USSD, transfer, mobile money).
2. **Application fees**: default application fee (amount or free), per-cohort override, refundable policy, waive/waiver codes, "fee required before admit" toggle.
3. **Class & subject fees**: fee catalog + fee rules (scope: all/cohort/class/subject/group/student), installments, optional deadlines, gating (per file 03).
4. **Custom charges**: wizard (per file 03/UX F9).
5. **Coupons & discounts**.
6. **Notifications**: payment notification matrix (per file 03 addendum).
7. **Receipts & invoices**: numbering pattern, org details, logo, footer, tax settings.
8. **Reconciliation & payout settings** (subaccounts/splits).
All amounts in naira UI, kobo storage. Every change audited. Mobile layout: tabs become a vertical list → detail pages.

---
## 2. New content hierarchy (replaces Session/Item model)

```
Cohort                      (name, description, application window, capacity)   ← admissions container
 └─ Class                   (e.g. "Foundation Class", "Advanced Class")           ← admin creates; students are admitted to a Class
     └─ Subject             (= a Udemy "Course": has landing page, curriculum, settings)
         └─ Topic           (= a Udemy "Section": ordered group with objective)
             └─ Subtopic    (= a Udemy "Lecture/Module": the atomic learning unit)
                 ├─ Content: video | article (WYSIWYG) | PDF | Excel/spreadsheet | Word | PowerPoint | audio | image | external link/embed | live session link
                 ├─ Resources: downloadable files / external links / source files
                 └─ (sibling curriculum items under a Topic: Quiz, Assignment, Practice test)
```
**Terminology mapping used in UI copy** (Imo Ijinle labels ↔ Udemy concept): Class (grouping/cohort track) · **Subject = Course** · **Topic = Section** · **Subtopic = Lecture** (a.k.a. module). The UI shows "Subject", "Topic", "Subtopic" (admin-renamable labels in Settings → Terminology). **Interpretation recorded in DECISIONS.md:** the client wrote "class → subject, course → topic, topic → subtopic/module"; treated "subject" and "course" as the same level.

Rules: a Subject can be shared across Classes via **Subject Library** (clone-on-attach, or linked live — admin chooses). Ordering by drag-and-drop at every level. Program is now an *optional grouping label* on Cohort/Class (not required).

---
## 3. Data model changes

### 3.1 Replace/rename
| Old (file 02) | New |
|---|---|
| `ClassInstance` | `Class(cohort, name, slug, description, cover, status[draft|published|archived], capacity, starts_at, ends_at, order)` |
| `Session` | `Topic(subject, title, objective_text, order, is_published)` |
| `SessionItem` | `Subtopic(topic, title, order, kind, is_published, is_free_preview, estimated_time_s, min_time_s, description_json, drip/unlock rules)` + `SubtopicContent` |
| `courses/` templates | Subjects live in `Subject Library`; `Class.subjects` via `ClassSubject(class, subject, order, mode[linked|cloned])` |
New: `Subject(title, subtitle, slug, description_json, language, level[beginner|intermediate|advanced|all], category, subcategory, primary_topic_tags[], cover_image, promo_video, intended_learners JSON{learn[], requirements[], audience[]}, welcome_message, completion_message, instructors M2M, status[draft|in_review?|published|archived], settings JSON, version)`.
`SubtopicContent(subtopic, type[video|article|pdf|spreadsheet|document|presentation|audio|image|link|embed|live|quiz|assignment|practice_test], ref/asset FK, body_json, duration_s, page_count, captions[], transcript, download_allowed)`.
`Resource(subtopic, kind[file|external_link|source_code|library_asset], title, asset, url, size)`.
`QA_Question/Answer(subject, subtopic?, author, body, upvotes, is_instructor_answer, status)`, `Note(user, subtopic, timestamp_s, body)`, `Announcement(subject|class|cohort)`, optional `Rating(user, subject, stars, comment, private_to_admin)`.
Applicant: `Application` keeps fields from file 02 plus `account_state`, `onboarding_token_hash`, `onboarding_sent_at`, `fee_invoice FK`, `fee_paid_at`, `admitted_class_ids`. `Admission(application, class, admitted_by, admitted_at, notes)`.
`Enrollment` now targets `(user, class)` with `cohort` derived; progress stored per subtopic.

### 3.2 Progress & learning data (retargeted)
`ItemProgress` → `SubtopicProgress(enrollment, subtopic, status, percent, active_time_s, completed_at, last_position_s)`; `SubjectProgress`, `ClassProgress` rollups (percent = completed required subtopics ÷ required subtopics, weighted by duration optional). Video/study-time/heartbeat rules from file 02 addendum A apply per **Subtopic**.

### 3.3 Prerequisites & gating
Gating works at Class (admission), Subject, Topic and Subtopic level: sequential lock (default **off**, like Udemy's free navigation; admin can enable "sequential"), prerequisite subject, min score, drip date, payment gate (file 03). Free-preview subtopics are viewable by non-enrolled/applicants if enabled.

### 3.4 Re-pointing earlier specs
Fee rule scopes: `class`, `subject`, `cohort`, `group`, `user`. Certificates: issue per Subject and/or per Class (rules over completion of included subjects). Gradebook: columns are quizzes/assignments inside Topics. Finance reports: "by class / by subject". Study-time gate: per Subtopic (class/subject defaults inherited). All earlier "session/item" wording = Topic/Subtopic.

---
## 4. Admin/Instructor course-management experience (Udemy-style)

### 4.1 Where
`/admin/classes` (list, create) → `/admin/classes/[id]` (Overview, Subjects, Students, Applications, Fees, Announcements, Settings) → **Subject management** `/admin/subjects/[id]/manage/...` — the Udemy-like authoring workspace. Tutors reach it via "Teach/My subjects".

### 4.2 Subject management workspace layout
- **Left sidebar** (fixed, ~260 px; becomes a drawer on mobile) with a checklist grouped exactly like Udemy's course management:
  - **Plan your subject**: Intended learners · Subject structure · Setup & test video
  - **Create your content**: Film & edit (upload guidance) · Curriculum · Captions (optional) · Accessibility
  - **Publish your subject**: Subject landing page · Access & pricing (Paystack fees) · Promotions (coupons) · Subject messages
  - Settings (visibility, enrollment, certificate, study-time defaults, Q&A on/off)
  Each item shows a ✓/○ completion indicator; the top shows "Subject status: Draft" and a **Preview** button, and the primary button **Publish** (disabled until required items complete, with a "what's missing" popover) — mirrors Udemy's "submit for review" (here optional admin approval: `in_review` state if the org enables review).
- **Main pane**: one form/page per sidebar item with autosave ("Saved"), page title, helper text, and a right-aligned Save.
- **Header**: back link, subject title, status chip, Preview, Publish, overflow (duplicate, archive, export, delete).

### 4.3 Pages (fields & behaviour)
1. **Intended learners**: "What will students learn" (min 4 objectives, 160-char each, add/remove/reorder), "Requirements/prerequisites" list, "Who this subject is for" list. These render on the landing page.
2. **Subject structure**: guidance cards + checklist (min topics/subtopics/video minutes — configurable "quality bar", warns not blocks).
3. **Setup & test video**: test upload and playback quality check tips.
4. **Curriculum** (the heart — see 4.4).
5. **Captions**: per-video caption upload (.vtt/.srt) and auto-transcript hook; language selector; status.
6. **Subject landing page**: title (≤ 60), subtitle (≤ 120), description (WYSIWYG, min length hint), basic info (language, level, category, subcategory), subject image (upload with crop 750×422, guidance), promotional video (upload/embed), instructor(s) and bio, "Preview landing page" live.
7. **Access & pricing**: free / included in class fee / separate fee (Paystack, kobo), optional deadline, installments, gate rule, links to Payment Configuration.
8. **Promotions**: coupon creation (code, discount, validity, limit), shareable links.
9. **Subject messages**: welcome message (sent on enrollment) and completion message (sent at 100 %).
10. **Settings**: Q&A on/off, announcements, reviews (off / private / public to cohort), download permissions, certificate attach, study-time defaults, language, drip/sequential toggle.

### 4.4 Curriculum editor (replicate Udemy behaviour)
- Vertical list of **Topics** ("Topic 1: Introduction") each with title + "What will students be able to do at the end of this topic?" objective; inside, **Subtopics** ("Subtopic 1: …") with drag handle, title, type icon, status chip (Draft/Published), duration, ✓ content-uploaded indicator, and action menu (edit, preview, delete, move up/down, duplicate).
- **Inline creation**: "+ Topic" button between and under topics; "+ Curriculum item" inside a topic opens a type picker: **Subtopic (lesson)**, **Quiz**, **Assignment**, **Practice test**. Pressing "+ Subtopic" shows an inline title field (Enter to save).
- **Add content** on a subtopic (button expands panel): choose **Video**, **Video + slides**, **Article**, **PDF**, **Spreadsheet (Excel/CSV)**, **Document (Word)**, **Presentation (PowerPoint)**, **Audio**, **Image**, **Link/Embed**, **Live session**. Each shows accepted formats/size limits, drag-drop upload with progress/resume, replace/delete, and (for video) processing status and thumbnail.
- **Add Resources** to a subtopic: Downloadable file · External link · Source/Library asset; multiple allowed.
- **Description** (optional WYSIWYG), **Free preview** toggle, **Estimated time** and **Minimum time to stay** (study-time gate), "Require full watch" toggle, visibility/drip.
- **Bulk tools**: collapse/expand all, multi-select to move/delete/publish, drag between topics, "Import curriculum from CSV/outline", duplicate topic/subtopic, undo.
- **Upload manager** (global tray bottom-right): queue, progress, retry, pause.
- **Validation hints** like Udemy: red dot on incomplete items, "Publish checklist" in the sidebar.
- **Preview as student** opens the Udemy-style player (§6) in preview mode with banner.
- **Document preview pipeline**: PDFs rendered in-browser (pdf.js); Word/PowerPoint/Excel converted server-side (LibreOffice headless in `media` queue) to PDF/HTML for inline viewing, original kept for download if allowed; spreadsheets also offer an interactive grid viewer (SheetJS) for xlsx/csv; virus scan and size caps (video ≤ 4 GB, docs ≤ 100 MB configurable).

### 4.5 Class management
Admin creates **Class** (name, description, cover, capacity, dates, status) inside a cohort → attaches Subjects (from library or "Create new subject") → sets fees via Payment Configuration → publishes. Class page tabs: **Overview** (stats, publish checklist), **Subjects** (ordered cards with status; "Add subject"), **Students** (enrolled, progress), **Applicants admitted**, **Fees**, **Announcements**, **Settings**.

### 4.6 Admitting applicants to a class
Applications inbox → open application (drawer) → **Admit** → modal: choose Class(es) (multi-select with seats left), group (optional), fee handling (generate class fees / waive / scholarship), message template preview, send welcome → confirm. Bulk admit supported. Result: enrollment(s) created, invoices generated per rules, student notified. Shows payment state of application fee ("Paid ₦X on date, ref …").

---
## 5. Public & applicant side (see §1) — additional UI specs
- **Public cohort page** `/apply/[cohortSlug]`: hero with cohort name/description, key dates, fee, classes offered (cards), "Apply now". Application form as multi-step (mobile-friendly), **success page** (illustration, bold email address, "Resend", "Change email", what happens next stepper: Check email → Set password → Pay application fee → Admission).
- **Onboarding email** (template editable): subject "Continue your Imo Ijinle application", button "Set up your account", expiry notice, support contact, plain-text fallback.
- **Set-password page**: password meter, show/hide, success → redirect to portal.
- **My Application page**: stepper (Applied ✓ → Account ✓ → **Pay application fee** → Under review → Admitted), fee card with amount, "Pay now" (Paystack), receipt download, optional deadline, documents/extra questions panel.

---
## 6. Student side — Udemy-style learning experience

### 6.1 My learning (`/learning`)
Top tabs like Udemy: **All subjects · My classes · Announcements · Certificates · Notes**. Grid of **subject cards**: thumbnail (16:9), title, instructor, progress bar + "X% complete", "Start/Continue" on hover (always visible on touch), class badge. Filters (class, progress state), sort (recently accessed, title). Sticky "Continue where you left off" strip. Empty state per Udemy conventions.

### 6.2 Subject landing (internal, `/subjects/[slug]`)
Dark header band: breadcrumb (Class › Subject), title, subtitle, instructor(s), last updated, language, level, student count; right sticky card (for non-enrolled/preview: thumbnail + promo video, access status, CTA; for enrolled: **Continue learning** with progress). Below: **What you'll learn** (bordered 2-col checklist), **Subject content** accordion (Topics with "N subtopics • total length", expand all; subtopic rows with type icons, durations, "Preview" links for free previews), **Requirements**, **Description** (show more), **Who this subject is for**, **Instructors**, (optional) **Ratings & reviews**, announcements.

### 6.3 Learning player (`/learn/[subjectId]/[subtopicId]`)
Layout (desktop ≥ lg):
- **Top bar (dark)**: logo mark → "My learning", subject title, **Your progress** ring (click for popover: "N of M complete" + certificate hint), Share/Menu.
- **Main column**: content viewer (video 16:9 black-letterboxed; or PDF/Excel/Word/PPT viewer; or article reader at 68ch), with player controls: play/pause, ±5/10 s, volume, **playback speed**, captions, quality, theater/expand, fullscreen, keyboard shortcuts; **resume from last position**; autoplay-next with 5 s countdown (toggle).
- **Right sidebar "Subject content"** (~380 px, collapsible): topics as accordions ("Topic 2: …  3/5 | 24min"), subtopic rows with completion checkbox, type icon, duration, **Resources** dropdown (download/links), current highlighted, locked rows show lock + reason; sidebar scrolls to current item and persists collapse state.
- **Below content, tab bar**: **Overview** (subject description, stats) · **Q&A** (search, ask, sort, upvote, instructor-answer badge, filter "this subtopic / all") · **Notes** (timestamped, click to seek, edit/delete, download) · **Announcements** · **Reviews** (if enabled) · **Learning tools** (e.g. downloadable resources, bookmarks).
- **Footer controls**: Previous / Next subtopic; **Mark as complete** checkbox (disabled with ring-countdown until min study time met; auto-completes at watch threshold if allowed).
- Non-video types: PDF (pdf.js with page nav, zoom, download if allowed), Excel (grid viewer + download), Word/PPT (converted viewer), Article (reader), Quiz/Assignment (full-page flows from file 05), Live (join button + countdown).
Mobile/tablet: video sticky top; tabs under it; **Subject content** becomes its own tab/bottom sheet (like Udemy mobile); Mark complete as sticky action; landscape fullscreen; all responsive rules of file 05 addendum A apply.
Completion celebration at subject end: summary, certificate (if eligible), next subject in class.

### 6.4 Other student pages
Certificates, Notes (cross-subject), Wishlist/Archive not required, Account (profile, payments, notifications), Payments (class fees), Calendar (live sessions/deadlines).

---
## 7. Design choices — Udemy-pattern layout within Imo Ijinle tokens
- **Page chrome**: white/warm-paper background, top nav with search, "My learning", notifications, avatar menu (public/learn shell). Course-management pages use a **two-column admin shell** (left checklist sidebar + content), with a **dark header band** on subject landing and player.
- **Player ink**: introduce tokens `--ink` (#14201C), `--ink-2` (#1E2C27), `--ink-foreground` (#F4F2EC) for the player top bar, subject landing hero and video letterbox; progress/active accents in `--accent` (gold) and success green; the sidebar remains light with subtle dividers; active item has a left accent bar and tinted background.
- **Typography**: serif display only on landing/hero titles; UI sans everywhere else; sidebar rows 14 px, 1.4 line-height; bold section headings with counts in muted text.
- **Density**: Udemy-like compact lists in sidebar/curriculum editor (row height 44–48 px), generous card spacing on My learning.
- **Iconography**: lucide: PlayCircle (video), FileText (article), FileType (PDF), Table (spreadsheet), FileText/Word, Presentation, Headphones, Link, HelpCircle (quiz), ClipboardCheck (assignment), Radio (live), Download.
- **Micro-interactions**: checkbox tick animation + progress ring update, accordion expand with chevron, drag handle affordance, inline editing in curriculum, toast "Saved", skeletons, upload progress chips.
- **States**: published/draft/in-review chips, locked/free-preview badges, "Updated" dots when content changes.
- **Accessibility**: keyboard-reorderable curriculum (Move up/down menu), player shortcuts documented, sidebar landmarks, contrast checks on dark surfaces, captions default-on option.
- **Responsive**: curriculum editor usable on tablet (touch drag), phone uses list mode with action sheets; player/sidebar per §6.3.

---
## 8. API additions (all with OpenAPI + permission tests)
Admissions: `POST /public/applications` (creates application+invited user, queues email), `POST /public/applications/{id}/resend-onboarding`, `PATCH /public/applications/{id}/email` (before activation), `POST /auth/onboarding/verify`, `POST /auth/onboarding/set-password`, `GET /portal/applications`, `POST /portal/applications/{id}/pay`, `POST /applications/{id}/admit {class_ids[], group?, fee_handling}`, `POST /applications/bulk-admit`.
Payment config: `GET/PUT /settings/payments/{gateway|application-fees|receipts|notifications}`, `POST /settings/payments/test-webhook`.
Classes/subjects/curriculum: `/classes`, `/classes/{id}/subjects` (attach/reorder/detach), `/subjects` (+ `/intended-learners`, `/landing`, `/pricing`, `/messages`, `/settings`, `/publish`, `/preview-token`), `/subjects/{id}/topics`, `/topics/{id}/subtopics`, `POST /…/reorder`, `POST /subtopics/{id}/content` (type, upload session), `POST /subtopics/{id}/resources`, `POST /uploads/presign`, `GET /subtopics/{id}/viewer` (signed URL(s) per type), `POST /subtopics/{id}/progress|heartbeat|complete`.
Learning: `GET /me/learning`, `GET /subjects/{slug}/landing`, `GET /subjects/{id}/player-outline`, Q&A: `/subjects/{id}/qa`, notes: `/subtopics/{id}/notes`, announcements, ratings.
Provide `POST /subjects/{id}/duplicate` and `POST /classes/{id}/duplicate`.

---
## 9. Acceptance criteria (v1.2 additions)
1. Admin creates a cohort with name + description, opens applications, and the public URL accepts a submission within minutes, with no developer involvement.
2. After submitting, the applicant sees the "link sent to your email" success page; the onboarding email arrives; the link sets a password once and signs in; reuse/expired links are refused gracefully.
3. The applicant lands on their application page, pays the application fee via Paystack (test mode), and the admin sees "Fee paid" without refresh lag > 10 s.
4. Admin admits the applicant into a class; student sees it under **My learning**.
5. Admin builds Class → Subject → Topic → Subtopic with video, PDF, Excel, Word/PPT and article content, resources and a quiz, using the Udemy-style workspace (checklist sidebar, inline curriculum editing, drag-drop reorder, preview-as-student, publish checklist).
6. The student player matches the §6.3 layout: dark top bar with progress, right "Subject content" sidebar with checkboxes and resources, tabs (Overview, Q&A, Notes, Announcements), resumable video, speed control, autoplay next, and responsive mobile layout.
7. Mark-as-complete respects the minimum study time; progress rolls up to subject and class; certificate issues at completion rules.
8. Payment configuration page controls application fee, class/subject fees, optional deadlines and notifications.

## 10. Revised milestone order (replaces file 09 table where different)
M0 foundation (as before) · **M1 Admin core**: cohorts, classes, subjects, topics, subtopics CRUD + payment-configuration shell · **M2 Admissions & portal**: public apply, success page, onboarding email/set-password, applicant portal, application-fee payment (Paystack), admit-to-class · **M3 Course authoring (Udemy workspace)**: sidebar checklist, curriculum editor, upload manager, content types, document conversion, landing page editor, preview · **M4 Learning experience**: My learning, subject landing, player, sidebar, Q&A, notes, progress, resumable video, study-time gate · **M5 Payments full**: fee rules, class/subject fees, custom charges, installments, refunds, gating, notifications, finance analytics · **M6 Assessments & grading** · **M7 Certificates** · **M8 Comms/analytics/hardening** · **M9 SSO/unified search**.
