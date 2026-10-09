# 07 — UX Flows, States & Edge Cases

Each flow lists: trigger → steps → success → failure/edge states. Universal state rules: every data view has **loading (skeleton)**, **empty (explain + CTA)**, **error (retry + request id)**, **partial/stale** and **offline** states. Every destructive action has confirmation + undo where possible. Every form autosaves or warns on leave.

## F1. Admin opens a new cohort
1. Admin → Programs → program → "New cohort" (wizard: Basics → Schedule → Application form → Fees → Capacity/Waitlist → Review).
2. Clone from previous cohort (optional) copies classes/sessions/fees/form.
3. Application form: pick template or build; preview mobile/desktop.
4. Fees: choose existing fee rules or add (live "who pays what" preview).
5. Publish checklist (has form, fees reviewed, open/close dates valid, classes outlined) → **Open applications**. Public URL + QR + share buttons shown immediately (`/apply/[cohortSlug]`).
Edge: overlapping cohorts warn; closing date in past blocks; capacity reached → auto-switch to waitlist-only.

## F2. Applicant applies (public)
1. Land on program page → "Apply" → Step 1 Personal → Step 2 Program-specific questions → Step 3 Documents → Step 4 Review → (Step 5 Pay application fee, if any) → Submit.
2. Email confirmation with magic link to status page; draft resume link sent after step 1 email entered.
3. Status page shows pipeline with human copy ("We're reviewing your application. Typical response: 5 working days").
Edge: cohort closed mid-fill (draft saved, message offers next cohort/notify-me); duplicate application detected → open existing; file too large/type invalid inline; payment failed → application kept as "awaiting fee" with retry; spam → captcha/honeypot/rate-limit; low connectivity → draft autosave + retry queue.

## F3. Admissions review
Inbox with filters/saved views → open application drawer (answers, files, score rubric, notes, history, similar applicants) → decision with email template preview → bulk actions. Admit → confirmation modal summarizing: creates account, sends invite, generates invoices (shows amounts), enrolls into group. Waitlist auto-promotion toasts. Undo window 30 s for accidental rejection emails (email queued with delay).

## F4. Admitted → first login → payment → access
1. Invite email → set password (or Google) → welcome screen with 3-step checklist: Complete profile, Pay tuition (if required), Start Class 1.
2. Payment: invoice summary → choose full or installment → Paystack popup → success screen → "Start Class 1" CTA; receipt emailed.
3. If gating blocks: class shows PaywallCard with exact reason and button; non-gated content (orientation) remains accessible to reduce friction.
Edge: payment pending (bank transfer) → "We're confirming" state + email on confirmation; popup closed → "Payment not completed. Try again"; double-charge prevention; amount mismatch → support flow with reference; expired invoice → regenerate.

## F5. Daily learning loop
Dashboard → **Resume card** (class, item title, thumbnail with progress, "Continue · 12:34") → player. Completing an item shows soft celebration + "Next: Session 2 · Breath Awareness" auto-advance. Locked next item explains why ("Opens Mon 12 Jan" / "Pass Quiz 1 with 60 %" / "Pay balance") with the precise remedy. Session complete → summary (time spent, score, badge), class complete → class summary + unlock of next class + certificate eligibility meter.
Edge: video token expired mid-play → silent refresh; connection drop → buffer message + auto retry; two devices → last-write-wins, no corruption; content updated while viewing → non-blocking "Updated content available" banner.

## F6. Taking a test
Intro (rules, time, attempts left, honesty note, access code) → Start (confirm, timer begins server-side) → answer with autosave → review/flag → submit → result screen (score/pending manual grading) → review per settings.
Edge: refresh/close → resume same attempt with remaining time; network loss → local queue and banner; clock tampering irrelevant (server time); deadline hit → auto-submit with message; attempts exhausted → show best score, "request extra attempt" to tutor; accommodation extra time applied silently.

## F7. Assignment lifecycle
Student: view brief → upload/draft → submit (confirmation w/ receipt) → status tracker (Submitted → In review → Graded) → feedback + rubric; resubmit if allowed. Tutor: queue sorted by due/late → speed-grader → save draft grade → release (immediately or scheduled). Student notified once on release. Late penalties shown transparently with calculation.
Edge: late after hard cutoff → blocked w/ contact tutor; large file resumable; unsupported format; grade changed after release → audited, student notified with reason; regrade request flow.

## F8. Tutor oversight
Tutor dashboard: classes, "needs grading" count, at-risk students, upcoming live sessions. Class → Roster with progress bars and last-active; click student → **360° view**: timeline of events, per-session progress, scores & attempts, payments status (summary only), notes, quick actions (message, unlock item, extend deadline, mark attendance). Bulk message to filtered students ("behind schedule"). Export.

## F9. Admin creates custom payment
Finance → Custom charge → Step 1 target (Cohort | Class | Group | Pick students | One student) with search/multi-select → Step 2 details (title, amount, due, mandatory/optional, gating) → Step 3 **recipient preview** (count, total expected, exclusions already paid/waived) → confirm → invoices created, notifications queued. Result page with progress and link to invoice list filtered to this charge.
Edge: amount edit after issue → creates adjustment not rewrite; student already paid similar → warn; mass-send rate limits; undo = void unpaid invoices from the charge.

## F10. Certificate design → issue
Certificates → Templates → New → choose starter → Designer → Preview (pick student) → fix warnings → Publish → Attach to program rule → students become eligible → pending approvals inbox → bulk issue → emails sent. Student sees celebratory screen + wallet.
Edge: student name has long/diacritic characters → auto-fit; font missing → fallback warning in preview; revoke/reissue.

## F11. Moving between classes/sessions/cohorts
Auto-progression per unlock rules; admin can manually unlock or move a student to another class order, transfer cohort (retains progress for equal content via mapping, otherwise starts fresh with option), defer to next cohort (keeps payments as credit), withdraw (access end date configurable, certificate ineligible), re-admit.

## F12. Notifications
Triggers: admitted, invoice issued, payment received/failed, due soon/overdue, session opens, live reminder (24 h/1 h), assignment due, grade released, announcement, certificate issued, mention in discussion. Channels: in-app, email (WhatsApp/SMS later). Preferences per category; critical (payments, security) not mutable.

## Information architecture & navigation notes
Student nav: Home · My Classes · Calendar · Grades · Payments · Certificates. Tutor adds: Grading · Roster. Admin: grouped sidebar — Overview, Admissions, Programs & Cohorts, Learning Content, People, Finance, Certificates, Communications, Analytics, Settings. Global ⌘K search jumps to students, cohorts, invoices, items.

## Microcopy & empty-state examples
- No applications: "No applications yet. Share your link to start receiving them." [Copy link] [Show QR]
- No classes: "Build your first class. Start from a template or from scratch."
- Locked: "This session opens on Mon 12 Jan, 9:00 AM WAT."

---
# ADDENDUM v1.1

## F13. Tutor sets study time when adding a class/item
In Class creation (step "Pacing") or the item inspector: set **Estimated time** and **Minimum time to stay**; option "apply to all items". Preview shows what the student sees. Defaults can be class-wide with item overrides. Validation: min ≤ estimated × 1.5 (warn, not block); video items default min time to ~90 % of duration if the tutor enables "require watching".

## F14. Student completes an item with a minimum time
Open item → timer chip "Stay ~20 min" and ring-disabled **Mark as done** → reading/watching (timer advances only when active) → idle prompt if inactive → when requirement met: button enables with subtle animation and aria announcement → Mark as done → next item CTA.
Edge states: leaves and returns (time kept); opens on phone then tablet (shared total, only one device credits at a time with notice "Continuing on this device"); offline (timer pauses, resumes on reconnect; heartbeats can't backfill beyond wall-clock); tutor changes requirement mid-course (already completed items stay completed; in-progress use new value); accommodation multiplier applied silently; item has min time but student believes done → helper text explains why; tutor override flow with reason.

## F15. Finance admin investigates "attempts vs paid"
Finance → Overview → funnel widget → click "Failed" slice → Transactions explorer pre-filtered → open attempt drawer (timeline: initiated → opened → failed: insufficient funds) → actions: send retry reminder, offer installment plan, verify with Paystack. Bulk: select all abandoned attempts in range → "Send nudge" with template preview and recipient count.

## F16. Set an optional deadline / configure notifications
Creating a fee rule or custom charge: "Deadline" segmented control (No deadline · Fixed date · Relative · Per installment). Under it, "Reminders" shows the notification schedule inherited from defaults with "Customize". If No deadline: copy explains "Students can pay any time. Access gating (if set) applies until payment." Later, finance can add/extend/remove the deadline from the charge or a single invoice; affected students are previewed, notification optional.

## F17. Using the platform across devices
A student starts a video on phone (portrait), rotates to landscape (fullscreen player), continues later on a tablet or laptop at the same position; layouts reflow without losing state. Quiz in progress survives orientation change and app switching; timer is server-synced.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
