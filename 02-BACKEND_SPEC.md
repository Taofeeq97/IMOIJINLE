# 02 — Backend Specification (Django)

## 1. Architecture
Modular monolith. One Django project, domain apps with explicit service layers. Business logic in `services.py` / `selectors.py` (not in views or serializers); views stay thin.

```
backend/
  config/ (settings/base|dev|prod, urls, celery.py, asgi.py)
  apps/
    accounts/      users, auth, roles, profiles, invitations, impersonation
    orgsettings/   BrandSettings, SiteSettings, EmailTemplates, FeatureFlags
    programs/      Program, Cohort, Group, Enrollment, Class(ClassInstance), Session, SessionItem, schedules, progression rules
    courses/       CourseTemplate, Module, TemplateItem (+ clone-into-cohort service), content versions
    content/       Lesson, ContentBlock (Tiptap JSON), Asset, VideoAsset, Resource, MediaLibrary
    admissions/    ApplicationForm(schema), Application, Answer, Review, StatusHistory, Waitlist
    assessments/   Quiz, QuestionBank, Question, Attempt, Response, Assignment, Submission, Rubric, Grade, GradeCategory, GradeScale
    progress/      ProgressEvent, ItemProgress, VideoProgress, ClassProgress, Attendance, RiskFlag
    payments/      FeeItem, FeeRule, Invoice, InvoiceLine, Payment, PaymentAttempt, Coupon, Waiver, Refund, LedgerEntry, PaystackWebhookEvent, InstallmentPlan
    certificates/  CertificateTemplate(+Version), IssueRule, Certificate, VerificationLog
    comms/         Announcement, Notification, NotificationPreference, EmailLog, Discussion (Thread, Post)
    analytics/     materialized views / rollups, report endpoints
    audit/         AuditLog (generic), middleware, decorators
    search/        indexing hooks (Postgres FTS now, OpenSearch adapter later)
    integrations/  VideoProvider(Mux), StorageProvider, EmailProvider, PaystackClient, OIDC provider hooks
  tests/ (pytest, factory_boy, freezegun)
```
Libraries: DRF, drf-spectacular, django-filter, django-cors-headers, django-storages, celery, django-celery-beat, django-redis, djangorestframework-simplejwt, django-allauth (Google), django-ses/anymail, weasyprint or Playwright (PDF), Pillow, bleach/nh3 (HTML sanitizing), django-simple-history (selected models), django-import-export, sentry-sdk, pytest-django, ruff, mypy (django-stubs).

## 2. Cross-cutting conventions
- UUIDv7 primary keys (`id`), `created_at`, `updated_at`, soft-delete (`deleted_at`) on user-facing content.
- API versioned `/api/v1/`. Cursor pagination for feeds, page-number for admin tables. Consistent error envelope `{code, message, fields{}, request_id}`.
- Permissions: `RolePermission` + `ObjectScopePermission` (tutor→assigned classes, student→own enrollments). Central `policies.py` with `can(user, action, obj)` used by views, serializers and Celery tasks.
- Idempotency: `Idempotency-Key` header on payment initiation, submission, attempt-start.
- Rich text: Tiptap JSON stored (`JSONField`) + server-rendered sanitized HTML cache. Sanitize with allowlist.
- Files: pre-signed direct S3 uploads (`/uploads/presign`), virus scan task (ClamAV), MIME sniffing, size limits per type.
- Time: UTC; schedule fields are timestamptz; cohort has `timezone` for display.
- Config in env (12-factor); secrets via env/secret manager. Feature flags in DB.

## 3. Data model (key fields; add indexes on FKs + status + dates)

### accounts
- `User(email unique, password, first_name, last_name, phone, avatar, is_active, email_verified_at, last_seen_at, locale, timezone)`
- `Role` enum on `RoleAssignment(user, role, scope_type[global|program|cohort|class], scope_id)` → scoped RBAC.
- `Profile(user, bio, country, state, gender?, dob?, occupation, social_links, consent_flags)`; sensitive fields optional.
- `Invitation(email, role, scope, token, expires_at, accepted_at)`; `ObserverLink(student, observer_user|email, permissions, expires_at)`.

### programs
- `Program(title, slug, summary, description_rich, cover, status[draft|published|archived], category, grading_scheme FK, certificate_rule FK?, default_currency)`
- `Cohort(program, name, slug, start_date, end_date, timezone, capacity, status[planned|applications_open|applications_closed|running|completed|archived], application_opens_at, application_closes_at, application_form FK, application_fee_item FK?, auto_admit_to_enrollment, acceptance_deadline_days, waitlist_enabled, waitlist_auto_promote)`
- `Group(cohort, name, tutor FK?, capacity)`; `GroupMember(group, enrollment)`.
- `Enrollment(user, cohort, group?, status[pending_payment|active|paused|completed|withdrawn|dropped|deferred|suspended], enrolled_at, completed_at, access_override_until, notes)` unique(user, cohort).
- `ClassInstance(cohort, template? , title, code, order, description, status[draft|scheduled|open|closed], opens_at, closes_at, unlock_rule JSON, completion_rule JSON, weight_for_program)`  — "Class 1, Class 2…"
- `ClassTutor(class, user, role[lead|assistant])`
- `Session(class, title, order, kind[self_paced|live|hybrid], opens_at, due_at, closes_at, drip_rule JSON, unlock_rule JSON, status, summary)`
- `SessionItem(session, order, type[lesson|video|resource|live_meeting|quiz|assignment|survey|discussion], ref_type, ref_id, required bool, points, completion_rule JSON, visible_from, visible_to, status)` — polymorphic reference to content/assessment objects.
- **Rule JSON schemas** (validate with pydantic): `unlock_rule = {all:[{type:"previous_complete"},{type:"min_score",item_id,pct},{type:"date",at},{type:"payment_cleared",fee_item_ids[]},{type:"manual"}]}`; `completion_rule = {type:"watch_pct",pct:90}|{type:"viewed"}|{type:"passed_quiz"}|{type:"graded"}|{type:"all_required_items"}`.
- `UnlockOverride(enrollment, target_type, target_id, granted_by, reason, expires_at)`.

### courses (templates)
- `CourseTemplate(title, slug, version, status)`, `TemplateModule`, `TemplateItem` mirror Class/Session/Item. Service `clone_template_into_cohort(template, cohort, order)` deep-copies including content, assessments, rubrics; stores `source_template_version`. A `ContentRevision(content_type, object_id, data, author, created_at)` table gives restore/history.

### content
- `Lesson(title, body_json, body_html, estimated_minutes)`; `VideoAsset(provider, provider_asset_id, playback_id, policy[signed|public], duration_s, status[uploading|processing|ready|errored], captions[], chapters JSON, thumbnail_time, downloadable)`; `Resource(file, kind, size, download_allowed)`; `MediaAsset` for the library with tags.
- Mux webhooks (`video.asset.ready`, `video.asset.errored`, `video.upload.cancelled`) update status via `integrations/mux`.

### admissions
- `ApplicationForm(program|cohort, version, schema JSON, is_active)`; schema = ordered sections→fields `{id,type,label,help,required,options,visibility{when,eq}}` validated server-side with a dynamic serializer builder.
- `Application(cohort, applicant_email, applicant_name, phone, data JSON, status, submitted_at, reviewer FK, score, resume_token_hash, user FK?, application_payment FK?)`; `ApplicationFile`; `ApplicationReview(application, reviewer, rubric_scores JSON, comment, decision)`; `ApplicationStatusHistory`.
- `AdmissionOffer(application, issued_at, expires_at, accepted_at)`.
- Service `admit_application(app)`: create/attach user, send invite, create Enrollment, run `fees.generate_invoices(enrollment)`.

### assessments
- `GradeScheme(name, type[percent|letter|gpa|pass_fail], bands JSON, pass_mark)`; `GradeCategory(class|program, name, weight, drop_lowest)`.
- `QuestionBank(name, tags)`, `Question(bank, type, stem_json, options JSON, answer_key JSON, points, difficulty, tags, explanation_json)`.
- `Quiz(class/session, title, instructions_json, settings JSON{time_limit_s, attempts, score_policy, shuffle, one_per_page, backtrack, show_answers, access_code, open_at, close_at, pass_pct, grace_s}, category FK, points_total)`; `QuizQuestion(quiz, question|draw_rule, order, points)`.
- `Attempt(quiz, enrollment, number, started_at, deadline_at, submitted_at, status[in_progress|submitted|graded|expired], score, auto_score, manual_score, extra_time_s, ip, user_agent_hash, seed)`; `Response(attempt, question, answer JSON, autosaved_at, score, feedback_json, graded_by)`.
- Server is authoritative for time: `deadline_at` computed on start; submission after deadline+grace is rejected/auto-submitted by Celery beat.
- `Assignment(session, title, instructions_json, submission_types[], max_files, max_size, due_at, late_policy JSON, allow_resubmit, max_resubmits, group_mode, rubric FK?, points, category, release_grades_at)`; `Submission(assignment, enrollment|group, version, text_json, files, link, submitted_at, late_by_s, status[draft|submitted|graded|returned|resubmit_requested])`; `Rubric(criteria[{id,title,levels[{label,points,desc}]}])`; `SubmissionGrade(submission, rubric_scores JSON, raw_score, penalty, final_score, feedback_json, feedback_files, graded_by, released_at, overridden_reason)`.
- `GradeEntry(enrollment, item_ref, score, max, source[auto|manual|override], released)` is the **single gradebook source of truth** produced by services; `compute_class_grade(enrollment, class)` and `compute_program_grade` apply weights/drop-lowest/extra-credit with unit tests.
- `RegradeRequest(entry, reason, status, resolved_by)`.

### progress
- `ProgressEvent(enrollment, item, type[open|play|pause|seek|complete|submit|score|login], payload JSON, occurred_at)` — append-only, partition by month, feeds analytics & timelines.
- `ItemProgress(enrollment, item, status[locked|available|in_progress|completed], percent, first_opened_at, completed_at, time_spent_s, last_active_at)` unique(enrollment,item).
- `VideoProgress(enrollment, video, last_position_s, furthest_position_s, watched_segments JSON (merged intervals), watched_pct, playback_rate, caption_lang, updated_at, device_id)`.
- `ClassProgress` / `CohortProgress` denormalized rollups updated by Celery on events (debounced) + nightly full recompute.
- `Attendance(enrollment, session, status[present|late|absent|excused], source[manual|join_click|import], joined_at, duration_s)`.
- `RiskFlag(enrollment, kind[inactive|behind|low_score|overdue_payment], since, severity, resolved_at)`.

### comms
- `Announcement(scope_type, scope_id, title, body_json, publish_at, send_email, pinned)`; `Notification(user, kind, payload, read_at)`; `NotificationPreference`; `EmailTemplate(key, subject, body_json/mjml, variables)`; `EmailLog(to, template, status, provider_id, error)`.
- `Thread(session|item, title, locked)`, `Post(thread, author, parent, body_json, is_answer, edited_at)`, moderation flags.

(payments + certificates data models: files 03 and 04.)

## 4. API surface (v1) — representative, implement all with OpenAPI
**Auth**: `POST /auth/register|login|refresh|logout|password/forgot|password/reset|verify-email`, `GET /auth/me`, `POST /auth/google`, `POST /auth/magic-link`.
**Public**: `GET /public/programs`, `/public/programs/{slug}`, `/public/cohorts/{slug}` (+form schema & fee preview), `POST /public/applications` (draft/submit; throttled + captcha), `GET/PATCH /public/applications/{token}`, `POST /public/applications/{token}/files`, `GET /public/certificates/verify/{code}`.
**Admin setup**: REST resources for `programs, cohorts, groups, classes, sessions, items, templates, forms, rubrics, questionbanks, quizzes, assignments, grade-schemes, certificate-templates, email-templates, brand`, with `POST .../reorder` (bulk order payload), `.../duplicate`, `.../publish`, `.../preview-as-student`.
**Admissions admin**: `GET /applications` (filters: cohort,status,score,date), `POST /applications/bulk-transition`, `POST /applications/{id}/review`, `POST /applications/{id}/admit`, `POST /cohorts/{id}/open-applications|close-applications`.
**Enrollment**: `GET/POST /enrollments`, `POST /enrollments/import-csv`, `POST /enrollments/{id}/transfer|pause|withdraw|reinstate`, `POST /unlock-overrides`.
**Learning (student)**: `GET /me/dashboard`, `GET /me/enrollments`, `GET /classes/{id}/outline` (items with computed lock/progress state), `GET /items/{id}` (content payload), `POST /items/{id}/complete`, `POST /video/{id}/playback-token` (signed Mux JWT, short TTL, checks access), `PUT /video/{id}/progress` (batched; also accepts `sendBeacon`), `GET /video/{id}/progress`.
**Assessments**: `POST /quizzes/{id}/attempts` (start; idempotent), `PUT /attempts/{id}/responses` (autosave), `POST /attempts/{id}/submit`, `GET /attempts/{id}/review`; `POST /assignments/{id}/submissions`, `PATCH .../submissions/{id}`; grader: `GET /grading/queue`, `PUT /submissions/{id}/grade`, `POST /grades/release`, `POST /attempts/{id}/manual-grade`.
**Progress**: `GET /classes/{id}/roster-progress`, `GET /enrollments/{id}/timeline`, `GET /cohorts/{id}/gradebook`, `GET /gradebook/export`.
**Payments/Certificates/Comms/Analytics**: see 03 and 04; analytics: `/analytics/funnel`, `/analytics/completion`, `/analytics/revenue`, `/analytics/video-dropoff/{video}`, `/analytics/questions/{quiz}`.
**Realtime** (optional v1.1): Django Channels/SSE for notification badge and grading queue; fallback to polling 30 s.

## 5. Background jobs (Celery)
Queues: `default`, `mail`, `media`, `payments`, `reports`.
- Email send/retry; application status emails; announcement fan-out.
- Mux webhook processing; virus scan; thumbnail/OG generation.
- Quiz auto-submit at deadline (ETA tasks + beat sweeper every minute).
- Progress rollups (debounced per enrollment), nightly recompute, risk-flag evaluation.
- Payments: verify-after-callback fallback, installment due scanner, dunning, auto-charge, reconciliation (daily), invoice expiry.
- Certificates: eligibility evaluation on completion/grade events, PDF render, email delivery.
- Reports/exports (async with download link), data retention jobs, waitlist promotion, unlock-by-drip evaluator (beat every 5 min).

## 6. Resumable video progress (server contract)
`PUT /video/{id}/progress` body: `{position_s, duration_s, rate, segments:[[start,end]...], device_id, client_ts, event}`. Server: validates enrollment access, clamps values, merges `watched_segments`, recomputes `watched_pct`, upserts `VideoProgress`, enqueues `ItemProgress` completion when threshold met, writes sampled `ProgressEvent`. Last-write-wins by `client_ts` with monotonic `furthest_position_s`. Rate-limit to 1 req/5 s/video/user (beacon exempt). `GET` returns `resume_position_s = max(0, last_position_s - 3)` or 0 if watched ≥ 98 % (restart finished videos).

## 7. Permissions matrix (summary)
| Action | Super | ProgAdmin | Finance | Tutor | TA | Student | Observer |
|---|---|---|---|---|---|---|---|
| Manage programs/cohorts | ✔ | ✔ | – | – | – | – | – |
| Author class content | ✔ | ✔ | – | assigned | assigned (draft only) | – | – |
| Grade | ✔ | ✔ | – | assigned | assigned | – | – |
| View all payments | ✔ | – | ✔ | – | – | own | – |
| Create custom charge | ✔ | request | ✔ | – | – | – | – |
| Design certificates | ✔ | ✔ | – | – | – | – | – |
| View progress | ✔ | ✔ | summary | assigned | assigned | own | linked |

## 8. Admin (Django Admin as safety net)
Register all models with search/filters/readonly audit fields; custom admin actions: resend invitation, re-run progress rollup, reissue certificate, replay Paystack webhook. Primary admin UX lives in Next.js.

## 9. Testing requirements
pytest with ≥ 85 % coverage on services; property tests for grade computation; contract tests against OpenAPI schema; webhook signature tests; concurrency tests (double submit, double webhook); factory fixtures; seed command `manage.py seed_demo` creating a program, 2 cohorts, classes, sessions, quiz, assignment, students, invoices.

---
# ADDENDUM v1.1

## A. Minimum study time (time-on-task)
**Fields**
- `SessionItem.estimated_time_s` (int, nullable), `SessionItem.min_time_s` (int, default 0), inherited from `ClassInstance.default_min_time_s` / `default_estimated_time_s` when the item value is null. `Session.min_total_time_s` optional. `ClassInstance.idle_timeout_s` (default 90), `time_credit_rules JSON` (e.g. `{"video_rate_cap":2.0,"count_background_tab":false}`).
- `ItemProgress.active_time_s` (cumulative, server-credited), `ItemProgress.last_heartbeat_at`, `ItemProgress.time_requirement_met_at`.
- `Enrollment.time_multiplier` (decimal, default 1.0; e.g. 0.75 accommodation). Effective requirement = `ceil(min_time_s * multiplier)`.
- `TimeOverride(enrollment, item, granted_by, reason, created_at)`.
- `ActivityHeartbeat(enrollment, item, session_token, seq, active_ms, client_ts, received_at)` — keep 30 days, then roll up into `ItemProgress`.

**Endpoint** `POST /items/{id}/heartbeat` body `{session_token, seq, active_ms, state:"active|idle", video:{position_s, rate, playing}}` sent every 15 s while active (and via `sendBeacon` on unload).
Server rules: (1) credit `min(active_ms, interval_since_last_heartbeat + 2 s tolerance)` so a client cannot claim more time than wall-clock elapsed; (2) require `seq` monotonic, one live `session_token` per enrollment+item (second device pauses the first's credit—no double-counting); (3) cap credit rate at 1.0× wall-clock; (4) video credit = `min(wall_clock, media_delta / max(rate,1))`; (5) reject if enrollment lacks access (gates). Response `{active_time_s, required_s, remaining_s, can_complete}`.
**Completion** `POST /items/{id}/complete` returns `409 {code:"MIN_TIME_NOT_MET", remaining_s}` unless requirement met or a `TimeOverride` exists. All auto-completion paths (watch %, quiz pass, graded) call the same `can_complete()` service. Tutor/admin `POST /enrollments/{id}/items/{item}/complete-override {reason}`.
**Analytics** nightly rollup: per-item median/p90 time, fast-completion flags (`active_time_s < 0.4 * estimated_time_s`), time-on-task by student/class. Emit `RiskFlag(kind="rushing")` optionally.
**Tests**: heartbeat tampering (inflated active_ms, replay, out-of-order seq, two devices), multiplier rounding, override audit, completion-rule matrix with/without min time.

## B. Finance & payments addendum (data)
See 03 addendum for models: nullable deadlines, `PaymentNotificationConfig`, `PaymentEvent`, `FinanceDailyRollup`, attempt tracking, and analytics endpoints.
**Notification dispatch**: `payments.notifications.dispatch(event, invoice|payment)` resolves the most specific `PaymentNotificationConfig`, builds the recipient list, renders templates, enqueues email/in-app jobs, writes `EmailLog`/`Notification`, and is idempotent per `(event, object, recipient, channel, offset)`.

## C. Responsive-related API notes
Provide lightweight variants for mobile: `?fields=` sparse fieldsets on list endpoints, `?view=compact` for roster/gradebook, ETag/If-None-Match on outline and dashboard, gzip/brotli, image rendition URLs (`thumb`, `sm`, `md`, `lg`) from the storage layer, and cursor pagination everywhere on student-facing feeds.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
