# 01 — Product Requirements Document: Imo Ijinle Academy LMS

Version 1.0 · Doc IMO-2026-LMS-PRD · Source context: IMO-2026-SPEC (Spirit Science → Educational Portal: "online academy, student portal, webinars, certification programs").

## 1. Vision
A calm, premium, highly configurable learning platform where the Imo Ijinle community applies publicly, pays, learns in structured cohorts, and earns verifiable certificates, while tutors and admins get deep visibility into progress. The experience should feel contemplative and unhurried (meditation is the ecosystem's apex) yet be rigorous operationally.

## 2. Goals / Non-goals
**Goals**: end-to-end lifecycle (apply → admit → pay → learn → assess → certify → alumni); configurable without developers; resumable streaming; flexible payments; auditable grading; excellent mobile experience (majority of Nigerian learners are mobile-first, often on constrained bandwidth).
**Non-goals (v1)**: native mobile apps (PWA instead), live-video hosting (embed Zoom/Meet/YouTube Live links with schedule + reminders), marketplace of third-party tutors, multi-tenant SaaS (single organization, but schema keeps `organization` out of scope deliberately).

## 3. Personas
| Persona | Needs |
|---|---|
| Applicant | Discover open cohorts, apply on a public URL without an account, track status, pay admission/tuition |
| Student | Dashboard, resume learning, watch/read, submit assignments, take tests, see grades/progress, pay balances, download certificate |
| Tutor/Facilitator | Manage assigned classes, author content, grade, give feedback, see cohort progress, announce, flag at-risk students |
| Program Admin | Create programs/cohorts/classes/sessions, open/close applications, review applicants, set fees, manage groups |
| Finance Admin | Fee structures, custom invoices, discounts/waivers/scholarships, reconciliation, refunds, reports |
| Super Admin | Roles, branding, certificate templates, global settings, audit logs |
| Observer (optional) | Read-only progress for a sponsor/parent/mentor linked to students |
| Verifier (public) | Confirm a certificate's authenticity via URL/QR |

## 4. Domain hierarchy (core concept)
```
Program (e.g. "Spirit Science Foundation")
 └─ Cohort / Intake (e.g. "Jan 2027 Cohort", dates, capacity, application window, fees)
     └─ Class (a.k.a. Course instance: "Class 1 — Foundations", ordered, may be gated)
         └─ Session (week/lesson unit: "Session 1", scheduled/self-paced, ordered, gated)
             └─ Items: Lesson (video/text/file/embed), Live Meeting, Quiz/Test, Assignment, Survey
```
Reusable **Course Templates** (Course → Modules/Sessions → Items) can be attached to a Cohort as a Class, copying content (versioned) so edits to the template do not corrupt running cohorts. Cohort→Class order defines "moving from one class to the next"; Class completion rules + gating rules control advancement.

## 5. Functional requirements

### FR-A Public application & admissions
- A-1 Public, SEO-friendly pages: `/programs`, `/programs/[slug]`, `/apply/[cohortSlug]` (no login). Only cohorts with status `applications_open` and within window accept submissions.
- A-2 Admin builds the **application form** per program/cohort with a form builder (field types: short/long text, email, phone, select, multi-select, radio, checkbox, date, country, file upload, consent checkbox; conditional visibility; required rules; sections). Fixed core fields: full name, email, phone.
- A-3 Applicant can save draft (magic-link resume via email), upload documents (virus scanned), submit. Duplicate detection by email+cohort.
- A-4 Optional application fee collected via Paystack at submit (configurable per cohort; can be zero).
- A-5 Status pipeline: `draft → submitted → under_review → shortlisted → interview → admitted | waitlisted | rejected | withdrawn`. Bulk actions, reviewer assignment, scoring rubric, internal notes, email templates per status.
- A-6 On `admitted`: auto-create user (invite email, set password), enrollment in cohort with `pending_payment` or `active` depending on cohort rule; generate fee invoices from the fee structure; offer acceptance deadline optional.
- A-7 Applicant status tracker page via magic link `/apply/status/[token]`.
- A-8 Capacity & waitlist: auto-promote waitlist when seat freed (configurable manual/auto).

### FR-B Program, cohort, class, session setup (admin/tutor)
- B-1 CRUD + ordering (drag & drop) for programs, cohorts, classes, sessions, items; archive/duplicate/clone cohort (with structure, optionally with fee rules).
- B-2 Scheduling: each class/session has `opens_at`, `due_at`, `closes_at`, or "self-paced" with drip rules (open N days after previous session / after cohort start / on date).
- B-3 **Progression rules** (per class and session): sequential lock, prerequisite completion, minimum score to unlock next, minimum attendance, "must be paid up to date" gate, manual unlock by tutor/admin per student.
- B-4 Tutor assignment per class (primary + assistants), and **groups** (sub-cohorts) with their own tutor, schedule overrides, fees.
- B-5 Draft/Published states with preview-as-student; scheduled publishing; versioning of content with restore.
- B-6 Bulk import students (CSV) and enrollment moves (transfer cohort, defer, withdraw, re-admit).

### FR-C Content authoring & materials
- C-1 WYSIWYG (Tiptap) block editor: headings, rich text, lists, tables, callouts, code, math (KaTeX), images, embeds (YouTube/Vimeo/Zoom), file attachments, accordion/tabs, quote blocks, audio, divider. Slash-command menu, drag handles, autosave with revision history, image paste/upload.
- C-2 Video upload (resumable, large file, direct-to-Mux), captions/transcripts, chapters, downloadable resources, thumbnails.
- C-3 Materials library: PDFs, slides, audio, links; per-item "required/optional"; download permission toggle.
- C-4 Reusable content bank (question bank, media library, snippets) with tags and search.
- C-5 Discussion thread per session (threaded comments, tutor-highlighted answers, mentions, moderation).

### FR-D Learning experience (student)
- D-1 Dashboard: "Continue where you left off" card (exact item + timestamp), upcoming deadlines/live sessions, progress rings, announcements, payment status banner.
- D-2 Class player layout: left outline (sessions/items with completion state & lock icons), main content, right panel (notes, discussion, resources); mobile bottom-sheet outline.
- D-3 **Resumable streaming**: position saved every 10 s and on pause/seek/visibilitychange/unload (beacon), resumes at last watched position (minus 3 s rewind), cross-device sync, playback speed memory, caption preference memory, "watched ≥ 90 % (configurable)" marks complete, forward-seek restriction optional per item, tracks unique watched segments (not just position).
- D-4 Completion rules per item: viewed, watched %, marked-complete button, passed quiz, graded assignment.
- D-5 Personal notes with timestamp links; bookmarks; search within course.
- D-6 Offline-friendly: PWA install, cached text content, download resources.
- D-7 Calendar: month/agenda view, ICS feed, reminders (email + in-app, optional WhatsApp/SMS adapters later).

### FR-E Assessments
- E-1 **Quizzes/Tests** with question types: single/multi choice, true/false, short answer (auto-match patterns), long answer (manual), fill-in-blank, matching, ordering, numeric, file upload, with rich-text/image in stem and options. Question banks, random draw, shuffling, per-question points, partial credit, negative marking (optional).
- E-2 Settings: time limit, open/close window, attempts allowed, attempt-score policy (highest/last/average/first), pass mark, show answers (never/after submit/after close), lockdown options (one question per page, no back navigation), autosave answers, resume after disconnect, grace period, access code, accommodations (extra time per student).
- E-3 **Assignments**: instructions (rich text), attachments, submission types (text, files, link, audio/video upload), due date, late policy (penalty %/day, hard cutoff), resubmission rules, group submissions, plagiarism hook (interface only), rubric-based grading, inline comments, feedback files, grade release scheduling.
- E-4 Grading: manual & auto, rubrics (criteria × levels), grade overrides with reason (audited), regrade requests, grade scales (percent, letter, GPA, pass/fail) configured per program, weighted categories (e.g. Quizzes 30 %, Assignments 40 %, Final 30 %), drop-lowest, extra credit.
- E-5 Gradebook: matrix (students × items) with filters, inline edit, export CSV/XLSX, student-level grade report.
- E-6 Attendance: live sessions (join clicks / manual / CSV import) feeding progression & certificate eligibility.

### FR-F Progress, analytics & oversight
- F-1 Student progress view: per class and per session completion %, scores, attempts history, time spent, last active, streak.
- F-2 Tutor view: class roster with progress bars, at-risk flags (inactive N days, behind schedule, low scores, overdue payment), submission/grading queue, per-student drill-down timeline (events: watched, submitted, scored, paid).
- F-3 Admin analytics: funnel (applications → admitted → enrolled → completed), completion rate by cohort/class, average scores, question difficulty/discrimination, video drop-off heatmap, revenue vs outstanding, tutor grading turnaround.
- F-4 Observer/sponsor read-only progress links (opt-in by student).
- F-5 Exports (CSV/XLSX/PDF) for every table; scheduled email reports.

### FR-G Payments (Paystack) — detail in file 03
- G-1 Admin-defined **Fee Items** and **Fee Rules** applying to: program, cohort, class, group, individual student, or all; types: one-off, installment plan, recurring, optional add-on (e.g. retreat, materials), late fee, application fee.
- G-2 **Custom charges** at any granularity: "create payment for [cohort | class | group | selected students | one student]" with amount, description, due date, mandatory/optional, gating effect.
- G-3 Discounts, scholarships, waivers, coupons (percent/fixed, limits, expiry, scope), sponsor-paid invoices.
- G-4 Student pays via Paystack (card, bank transfer, USSD, mobile money where available); partial payments if allowed; installments; saved authorization for auto-charge of scheduled installments (with consent).
- G-5 Webhook-driven confirmation + verify fallback; receipts (PDF + email); ledger per student; refunds; reconciliation dashboard; Paystack settlement/split support (subaccounts for revenue sharing with partners/tutors).
- G-6 Payment gating: configurable per fee item to block access to cohort/class/session until paid, with grace days and admin override.
- G-7 Dunning: reminders at configurable offsets (T-7, T-1, due, +3, +7), then suspend access per rule.

### FR-H Certificates — detail in file 04
- H-1 Admin certificate **designer** (drag/drop canvas, fonts, images, dynamic placeholders, QR, signatures, backgrounds, orientation, page size), **live preview with sample or real student data before saving**, versioned templates, publish/draft.
- H-2 Issue rules per program/class: completion %, minimum grade, attendance, fees cleared, manual approval. Auto or manual issuance, bulk issue, revoke/reissue.
- H-3 Unique certificate IDs + public verification page + QR; PDF (A4/Letter) and PNG; share to LinkedIn; student wallet.

### FR-I Communication
- I-1 Announcements (cohort/class/group/individual), email templates (HTML, editable, variable-aware), in-app notification center, preferences, digest option.
- I-2 Direct messaging student↔tutor (v1.1 optional; v1 = discussion threads + feedback comments).
- I-3 Transactional email via provider adapter (Resend/SES/Postmark) with logs and retry.

### FR-J Administration & configuration
- J-1 RBAC: Super Admin, Program Admin, Finance Admin, Tutor, Teaching Assistant, Student, Observer, Applicant. Object-level scoping (a tutor sees only assigned classes).
- J-2 BrandSettings (logo, colors, fonts, footer, social), site pages (about, FAQ, terms) with the same WYSIWYG editor, email sender identity.
- J-3 Audit log viewer, data export (GDPR/NDPA style), data deletion workflow honoring the Nigeria Data Protection Act (NDPA 2023) principles.
- J-4 Impersonation ("view as student") with banner and audit.
- J-5 Webhooks/API tokens for integration with other Imo Ijinle portals; SSO (OIDC) in Phase 4; search index feed.

## 6. Non-functional requirements
- Performance: p95 API < 400 ms (non-report endpoints); LCP < 2.5 s on 4G mid-range Android; video start < 3 s.
- Scalability target v1: 5,000 concurrent learners; design stateless web tier, Redis cache, Celery for heavy work.
- Availability 99.9 %; daily backups, PITR; RPO 15 min, RTO 2 h.
- Accessibility WCAG 2.2 AA; i18n-ready (English first; Yoruba-ready strings and font coverage).
- Security: OWASP ASVS L2; see file 09.
- Privacy: NDPA-aligned consent, retention policies, PII encryption at rest for sensitive fields.

## 7. Success metrics
Application→admitted conversion, admitted→paid conversion, weekly active learners, median days-behind-schedule, cohort completion rate ≥ 70 %, assignment turnaround < 5 days, payment collection rate ≥ 90 % by due date, NPS ≥ 50, support tickets per 100 students.

## 8. Release scoping
- **MVP (M1–M6)**: A, B, C, D, E (quiz+assignment+gradebook), F-1/F-2, G core, H, I-1/I-3, J-1/J-2.
- **v1.1**: Discussions advanced, DMs, observers, analytics F-3 depth, coupons, split settlements, PWA offline.
- **v1.2**: SSO/unified search integration, live-class attendance auto-capture, plagiarism provider, WhatsApp notifications.

## 9. Acceptance (top-level)
1. Admin can, with zero code, create a program, open a cohort, publish an application form, and receive an application from an unauthenticated visitor.
2. Admitted applicant gets invoice, pays via Paystack test mode, webhook marks paid, access unlocks.
3. Student watches a video, closes browser, reopens on another device, playback resumes within 5 s of the last position.
4. Tutor sees live progress and grades an assignment with rubric; student sees score and feedback after release.
5. Admin designs a certificate, previews with a real student's data, saves; completion triggers issuance; public URL verifies it.
6. Custom charge can be created for a single student, a group, a class, and a cohort; each yields the right invoices and gating.

---
# ADDENDUM v1.1 (supersedes conflicting text above)

## FR-K Minimum study time ("time-on-task" gate)
- K-1 Tutor/admin sets per item: `estimated_time_s` (shown to students, "~25 min") and `min_time_s` (required engaged time before completion is allowed). Defaults: 0 (off). Also settable as a class-level default that items inherit, with per-item override. Optional per-session total minimum.
- K-2 A student **cannot mark an item done** (button disabled, with live "Stay 08:42 more to complete" countdown) until engaged time ≥ `min_time_s`. The server enforces it; the UI is only a mirror. Auto-completion rules (watch %, quiz pass) must also satisfy `min_time_s` when it is set.
- K-3 Engaged time counts only **active** time: tab visible and focused, with recent interaction (scroll, click, key, video playing). Idle > 90 s (configurable) pauses the timer with a gentle "Still reading?" prompt. Video time counts only while playing at ≤ 2× speed (time is credited at media-time/rate so speeding through doesn't shortcut it).
- K-4 Timer persists across sessions/devices (cumulative per item), survives refresh, and never resets. Revisits add to the total.
- K-5 Accommodations: per-student time multiplier (e.g. 0.75× required time) and manual tutor/admin override ("Mark complete anyway", reason required, audited).
- K-6 Visible to staff: per-item average/median time spent, per-student time spent vs required, "completed suspiciously fast" flag (below 40 % of estimate with minimum disabled), time-on-task report export.
- K-7 Honest limitation: client-side activity cannot be made tamper-proof; the design makes shortcutting inconvenient and visible (server-credited heartbeats, rate limits, anomaly flags), not impossible.

## FR-L Responsive & multi-device support
Every screen must work from **320 px phones through tablets (portrait/landscape, split-screen) to 4K desktops**, with touch, keyboard and mouse. See 06 §12 and 08 "Responsive matrix". Students are assumed to be mostly on mid-range Android phones and tablets over variable networks.

## FR-G additions (finance) — see 03 addendum
- G-8 Payment deadlines are **optional** on fee rules, custom charges, installments and invoices. No deadline = no overdue state, no dunning by date; gating (if any) then applies until paid.
- G-9 Fully configurable payment notifications (events × channels × recipients × timing × templates) at global, program, cohort, fee-item and charge level.
- G-10 Finance analytics suite: revenue trends, collection rate, aging, **payment attempts vs successful payments** (conversion/abandonment/failure reasons), channel mix, cohort/class/fee-item breakdowns, forecast of expected inflows, per-student ledger, refunds and reconciliation, scheduled and ad-hoc exports.

## Acceptance additions
7. A tutor sets a 20-minute minimum on a reading item; a student cannot complete it before 20 active minutes (UI and direct API call both refused); after refresh and on another device the accumulated time is preserved.
8. A charge with no deadline never goes overdue; one with a deadline sends the configured reminders and respects the grace/gating rules.
9. The finance dashboard shows attempts vs paid for any date range/cohort/fee item and drills down to individual attempts with Paystack failure reasons.
10. All primary flows pass on 360×640, 768×1024, 1024×768 and 1440×900 viewports.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
