# 08 — UI Screen Specifications

Notation: **Layout** (regions) · **Components** · **Data** · **States** · **Responsive**. IDs are referenced by other docs. Use shadcn components + design tokens (06).

## PUBLIC

### S-P1 Academy landing `/`
Layout: hero (serif headline, subcopy, primary "Explore programs", secondary "Verify a certificate"), concentric-ring motif background; "Open for applications" strip listing open cohorts with deadline countdown; Programs grid (cards: cover, title, duration, next cohort, fee-from); "How it works" 4-step (Apply → Admission → Learn → Certify); Learning experience highlights (resume anywhere, mentors, certificates); Tutors; Testimonials; FAQ accordion; footer with ecosystem links.
Responsive: single column, sticky bottom "Apply" bar on mobile.

### S-P2 Program detail `/programs/[slug]`
Hero + sticky right card (next cohort dates, fee, capacity left, **Apply now**). Tabs/sections: Overview, Syllabus (classes → sessions accordion, durations), Outcomes, Tutors, Fees & payment options (installments), Certificate sample preview, FAQ. States: no open cohort → "Notify me" email capture.

### S-P3 Application `/apply/[cohortSlug]`
Stepper header (progress %, save status), form card (max-width 720), sticky footer actions (Back / Save & continue), review step with edit links, success page with reference number, next steps, status link. Inline validation; file dropzone with scan status. Fee step shows summary + Paystack button.

### S-P4 Application status `/apply/status/[token]`
Pipeline stepper, current status card with message, outstanding actions (upload doc, pay fee, accept offer), timeline of updates.

### S-P5 Certificate verify `/verify/[code]`
Centered card: big status badge (Valid ✓ / Revoked / Not found), holder name, program, issue date, issuer, certificate thumbnail, "Report an issue".

## AUTH
### S-AU1 Login/Register/Forgot/Invite
Split layout (form left, calm image right on desktop). Google button, magic link option, password rules meter, clear errors, rate-limit message.

## STUDENT
### S-S1 Dashboard
Top: greeting + payment banner (if due). Row 1: **Resume card** (large) + "Up next" list (deadlines/live sessions). Row 2: Progress overview (rings per class), Streak/time this week, Announcements. Row 3: Grades snapshot, Certificates. Skeletons per card.

### S-S2 My classes (cohort map)
Vertical **journey map**: Class 1 → Class 2 → … nodes with states (completed ✓, current, locked 🔒 with reason, upcoming date). Click expands sessions list with progress bars.

### S-S3 Learning player
Layout (desktop): top bar (breadcrumb, progress bar, prev/next), left **outline** (collapsible, 320 px: session groups, item icons by type, completion checks, lock icons, durations, current highlighted, "Mark complete" for read items), center content (video 16:9 with custom controls, title, tabs below: Overview · Transcript · Notes · Resources · Discussion), right slim rail toggles (Notes, Discussion). Mobile: video top sticky, tabs below, outline as bottom sheet, swipe prev/next.
Item variants: Lesson (reading width 68ch, TOC), Video, Resource list, Live session (join button, countdown, add to calendar, recording later), Quiz intro, Assignment brief, Discussion.
States: locked (explain + remedy), paywall, loading, error, completed (confetti-lite, next CTA).

### S-S4 Quiz taker
Header with title/timer (pill, turns amber <5 min), question card (rich content, options as large tappable cards), side navigator grid (answered/flagged/unanswered), footer Prev/Next/Flag/Submit. Submit dialog with unanswered summary. Result screen: score ring, pass/fail, per-section breakdown, review button.

### S-S5 Assignment page
Left: brief + rubric + attachments; right: submission panel (status chip, due countdown, uploader, text editor, link, submit) ; below: feedback & grade card after release; version history drawer.

### S-S6 Grades
Class selector → table of items with score, weight, status, feedback link; summary header (current %, grade letter, pass-eligibility); chart of trend; "what-if" calculator (optional v1.1).

### S-S7 Payments
Tabs: Outstanding · Upcoming · History · Saved cards. Invoice cards with line items, due dates, status chips, Pay button, installment schedule visual. Invoice detail: lines, discounts, coupon entry, payment history, receipt download. Callback page: animated states (processing → success/failure) with next steps.

### S-S8 Calendar
Month/week/agenda toggle; events colored by type; click → drawer; "Subscribe (ICS)" button.

### S-S9 Certificates
Gallery cards (thumbnail, program, date, code); detail modal with PDF viewer, Download PDF/PNG, Copy verify link, Add to LinkedIn; empty state shows eligibility progress meter.

### S-S10 Profile/Settings/Notifications
Avatar upload, personal info, timezone, notification preferences matrix, saved cards, password/sessions (active devices, sign out all), data export/delete request.

## TUTOR
### S-T1 Tutor dashboard
KPIs (to grade, at-risk, upcoming sessions, avg progress), class cards, grading queue preview, activity feed.
### S-T2 Class workspace (tabs)
Overview · Content (builder) · Roster (table: name, progress bar, last active, avg score, flags; filters; bulk message) · Gradebook (matrix, inline edit, color-coded, export) · Attendance (grid) · Announcements.
### S-T3 Grading queue & speed-grader
Queue table (assignment, student, submitted, late badge). Speed-grader per 05 §5.5.
### S-T4 Student 360°
Header (student, cohort, status), tabs: Progress (per session bars), Activity timeline, Scores & attempts, Submissions, Payments summary, Notes. Quick actions toolbar.

## ADMIN
### S-A1 Admin dashboard
KPI cards (open applications, enrolled, revenue collected, outstanding), funnel chart, cohort health table, alerts (webhook failures, pending certificates, overdue spikes), recent activity.
### S-A2 Programs list & Program detail (tabs per 05 route map).
### S-A3 Cohort wizard & Cohort workspace
Wizard stepper (F1). Workspace tabs listed in 05; header shows status chip, dates, seats `42/60`, big **Open/Close applications** control, public link + QR.
### S-A4 Application form builder
Three-pane (palette / canvas / inspector) + preview toggle.
### S-A5 Applications inbox
Table + right drawer detail, bulk bar, saved views, rubric scoring, templated decisions, export.
### S-A6 Course builder
Per 05 §5.3; includes timeline view and publish checklist.
### S-A7 Lesson editor (WYSIWYG)
Full-width editor, floating toolbar, slash menu, side panel (settings, revisions, a11y checks), preview-as-student.
### S-A8 Video manager
Upload (resumable, progress, pause), processing status, captions upload/auto-generate hook, chapters editor, thumbnail picker, usage list.
### S-A9 Quiz builder & question banks
Question list with types, drag order, points, bank import, random draw rules, settings drawer (time, attempts, policy, shuffle, answer visibility), preview-as-student, analytics tab (difficulty/discrimination).
### S-A10 Assignment builder + rubric builder (grid editor with criteria/levels).
### S-A11 Students & enrollments
Table with filters; student detail (profile, enrollments, invoices, progress, certificates, audit); actions: transfer, pause, withdraw, impersonate, unlock, reset progress (confirm + audit).
### S-A12 Finance: Fee catalog · Rule builder · Custom charge wizard · Invoices · Payments · Coupons · Waivers · Refunds · Reconciliation · Reports (per 03 §5).
### S-A13 Grading config
Grade schemes, categories & weights editor with live example calculation.
### S-A14 Certificate designer
Layout: top bar, left tool tabs, center canvas (checkerboard, rulers, zoom), right inspector, bottom layers/versions drawer. Preview modal (04 §4). Template gallery page with thumbnails, status, usage.
### S-A15 Communications
Announcement composer (audience picker w/ recipient count), email template editor (WYSIWYG + variable chips + test send), logs.
### S-A16 Settings
Brand (live preview of tokens), site pages editor, roles & permissions, integrations (Paystack keys status/test, Mux, email provider, storage), feature flags, audit log viewer with filters, data retention.
### S-A17 Analytics
Funnel, completion, revenue, engagement heatmap, video drop-off, question analytics; date/cohort filters; export.

## Global components
Command palette, notification center, toasts, confirm dialogs (type-to-confirm for destructive/bulk), keyboard shortcut help (`?`), error pages (403/404/500) with calm illustration and request ID, maintenance page, cookie/consent banner.

---
# ADDENDUM v1.1

## Responsive matrix (applies to every screen above)
| Area | Phone 320–639 | Tablet 640–1023 | Laptop/Desktop ≥1024 |
|---|---|---|---|
| Student nav | Bottom tabs (Home, Learn, Calendar, Pay, Me) | Collapsed rail + top bar | Full left rail |
| Dashboard | Single column; Resume card first | 2-col grid | 3-col grid |
| Player | Sticky video, tabs below, outline = bottom sheet | Video + outline drawer (portrait); video + persistent outline (landscape) | Outline + content + optional right rail |
| Quiz | One question per screen, bottom nav bar, navigator in sheet | One/two-col with navigator on right (landscape) | Question + side navigator |
| Tables (roster, invoices, applications) | Card list with key fields + expandable | Compact table, hide low-priority columns | Full table, density toggle |
| Admin builders | List mode with menus, inspector as sheet | Two-pane, touch drag | Three-pane |
| Certificate designer | Read-only preview + notice | Full editor (landscape ≥ 900 px) | Full editor |
| Charts | Swipeable, simplified, table fallback | Full | Full + compare |
| Dialogs | Full-screen sheet | Centered/Sheet | Centered |

## S-S3 additions — study timer
Under the item title: chip `⏱ ~20 min · Stay 08:42 more` (becomes "Ready to complete" in gold). Bottom/sticky action bar holds **Mark as done** with ring countdown (disabled until met) and Next. Outline items show clock badge + partial ring. Idle prompt: non-blocking toast with "I'm here". Locked/waiting copy is gentle, never punitive.

## S-T/S-A (authoring) additions — pacing controls
Class form step "Pacing & time": default Estimated time, default Minimum time, idle timeout (advanced), apply-to-all switch. Item inspector: Estimated time, Minimum time to stay, "Require full video watch" toggle, and a student-preview line. Session header shows totals ("6 items · est. 2h 10m · min. 1h 30m").
Tutor views: Roster column "Time spent / required"; Student 360° per-item time vs required; Class report "Time on task" with fast-completion flags.

## S-A12 expanded — Finance (see 03 addendum §5)
Sub-pages: **Overview**, **Attempts vs Paid**, **Transactions**, **Outstanding & Aging**, **Charges & Deadlines**, **Coupons & Waivers**, **Refunds**, **Reconciliation**, **Notifications**, **Reports**.
- *Overview*: KPI row, revenue trend with compare, collected vs invoiced by cohort, aging, channel mix, forecast.
- *Attempts vs Paid*: funnel (viewed → clicked pay → checkout opened → paid), stacked daily bars (success / failed / abandoned) + success-rate line, failure reasons table, retry-recovery rate, channel and time-of-day breakdown, drill-down to attempts list.
- *Charges & Deadlines*: table of fee rules/charges with scope, amount, deadline (or "None"), paid/unpaid progress, bulk edit deadline, bulk remind.
- *Notifications*: events × channels matrix, scope selector (global/program/cohort/fee item/charge), offsets editor, template picker, quiet hours, delivery log, test send.
All with phone/tablet variants per the matrix above (filters in bottom sheet, KPI carousel, card-list tables).

## S-S7 Student payments additions
Invoice cards show "No deadline" or "Due 12 Jan · 5 days left"; attempt history accordion with friendly failure messages and retry; notification preferences for non-critical alerts.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
