# 09 — Delivery Plan, QA, Security & DevOps

## 1. Milestones (agent build order; each ends green: tests + lint + typecheck + seed + docs)
| M | Scope | Exit criteria |
|---|---|---|
| M0 | Monorepo scaffold, Docker Compose (Postgres, Redis, MinIO, Mailpit), CI, settings, auth, RBAC, audit, OpenAPI → TS client, design tokens, shadcn base, app shells | Login/roles work; CI green |
| M1 | Programs/Cohorts/Classes/Sessions/Items CRUD, ordering, templates clone, brand settings | Admin builds structure in UI |
| M2 | Admissions: form builder/renderer, public apply, review pipeline, admit→enroll, emails | PRD acceptance #1 |
| M3 | Content: Tiptap editor, Mux upload/playback, resources, resumable progress, outline/gating engine | Acceptance #3 |
| M4 | Payments: fee rules, invoices, Paystack initialize/verify/webhook, receipts, gating, custom charges, installments, refunds | Acceptance #2 and #6 (Paystack test mode) |
| M5 | Assessments: quizzes, assignments, rubrics, gradebook, speed-grader, progress dashboards for tutors | Acceptance #4 |
| M6 | Certificates designer, preview, issuance, verification | Acceptance #5 |
| M7 | Comms (announcements, notifications, discussions), calendar/ICS, analytics, risk flags | |
| M8 | Hardening: a11y, performance, security review, load test, PWA, docs, runbooks, UAT fixes | NFR targets met |
| M9 (later) | SSO/OIDC + unified search integration with other Imo Ijinle portals | Phase 4 of client roadmap |

## 2. Testing strategy
Pyramid: unit (services, rules engines, grade math, fee resolution) → API/contract → component → E2E. Required E2E (Playwright, run against seeded stack): apply→admit→pay→learn→resume→quiz→assignment→certificate→verify. Load tests (k6): 5k concurrent learners, progress PUT rate, quiz start spikes, webhook bursts. Security tests: authz matrix tests (every endpoint × role), IDOR checks, upload abuse. Accessibility: axe in CI + manual screen-reader pass on player/quiz/forms. Cross-browser: Chrome, Safari iOS, Android Chrome, Firefox, Edge; low-end Android profile throttling.

## 3. Security requirements (OWASP ASVS L2)
- AuthN: Argon2 hashing, breached-password check, throttling, optional TOTP 2FA (required for admin/finance roles), session/device list, refresh rotation + reuse detection.
- AuthZ: deny-by-default; object-level checks via policy layer; tests per role.
- Input/Output: DRF validation, HTML sanitization (nh3) for rich text, CSP (no inline scripts except nonce), CSRF for cookie flows, strict CORS, secure headers, rate limiting (DRF throttles + Redis) esp. public apply, auth, payments, verify.
- Uploads: signed URLs, MIME/extension allowlist, size limits, ClamAV scan, private buckets with time-limited signed GETs, no direct public serving of submissions.
- Video: signed Mux playback tokens bound to user entitlement, short TTL, domain restriction; optional watermark overlay with student email (anti-leak) as configurable setting.
- Payments: see 03 §7. Webhook HMAC verification on raw body.
- Secrets: env/secret manager, rotation, no secrets in repo; dependency scanning (pip-audit, npm audit, Dependabot), SAST (Bandit, Semgrep), container scan (Trivy).
- Privacy: NDPA-aligned consent capture, data minimization, retention schedule, export/delete requests, PII access logged, encryption at rest (DB volume + field-level for authorization codes/IDs), TLS everywhere.
- Audit: immutable AuditLog (actor, action, object, before/after diff, ip, request_id) for grades, payments, enrollments, certificates, roles, settings, impersonation.

## 4. DevOps & infrastructure
- Containers: Docker multi-stage; `docker-compose.yml` for dev.
- Environments: dev, staging (Paystack test, Mux dev), prod. Env parity via `.env.example`.
- Suggested hosting: AWS (ECS Fargate or EC2/ASG) af-south-1 (Cape Town) or eu-west-1 with CloudFront; RDS PostgreSQL (multi-AZ in prod, PITR), ElastiCache Redis, S3 (+ lifecycle), SES/Resend for email, Sentry, Grafana/Prometheus or CloudWatch dashboards. Frontend on Vercel or containerized Next.js behind CloudFront. (Choose based on client budget; record in DECISIONS.md.)
- CI/CD: GitHub Actions — lint, typecheck, unit, integration, build images, migrations check (`makemigrations --check`), E2E on staging, manual prod approval, blue/green or rolling deploy, auto rollback on health check failure.
- Observability: structured JSON logs with request_id, OpenTelemetry traces, metrics (queue depth, webhook lag, payment success rate, p95), alerting (webhook failures, queue backlog, 5xx, reconciliation mismatch, Mux errors), uptime checks, status page.
- Backups: nightly + PITR, quarterly restore drill, S3 versioning.
- Cost control: Mux minutes budget alerts, CDN caching, image optimization, Celery autoscale.

## 5. Documentation deliverables
README (setup in ≤ 10 min), `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` (ADR log), `docs/RUNBOOK.md` (webhook replay, stuck video, failed payment investigation, restore), `docs/ADMIN_GUIDE.md` (screenshots later), `docs/API.md` (generated), `docs/SECURITY.md`, Storybook for components, seed data guide.

## 6. Risks & mitigations
| Risk | Mitigation |
|---|---|
| Unclear brand/URL architecture | Env-driven domains; BrandSettings tokens |
| Video cost/size | Mux budget alerts, data-saver mode, provider abstraction |
| Payment edge cases (double webhook, bank transfer delays) | Idempotent settle, verify fallback, reconciliation job |
| Rule-engine complexity (fees, unlocks) | Rule JSON schemas, exhaustive unit tests, "explain why" API (`/access/explain`) |
| Low bandwidth/mobile majority | PWA, adaptive streaming, skeletons, small bundles |
| Scope creep | MVP list in PRD §8; DECISIONS.md |

## 7. Definition of Done (per feature)
Code + tests + OpenAPI + a11y check + empty/loading/error states + audit logging (where applicable) + permission tests + docs updated + demo seed data + reviewed against UI spec.

---
# ADDENDUM v1.1 — Plan changes
- **M0**: add responsive foundations (breakpoints, container queries, ResponsiveTable, sheet/dialog adaptive primitives, Playwright device matrix in CI).
- **M3**: add time-on-task engine (heartbeat endpoint, `useStudyTimer`, CompleteButton, tutor pacing controls, anomaly flags).
- **M4**: add nullable deadlines, notification configs, attempt/event tracking.
- **M7**: finance analytics suite, rollups, scheduled reports (move forward if the client prioritizes finance visibility; payments data capture from M4 is required regardless so history is complete).
- **QA**: device-matrix E2E for the 10 acceptance flows; heartbeat tamper tests; rollup-vs-raw reconciliation tests; real-device passes (low-end Android, iPad, iPhone SE) before UAT.
- **Security/Privacy**: heartbeat and finance analytics contain behavioral data — apply retention (heartbeats 30 days raw), role-limit finance amounts, audit exports.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
