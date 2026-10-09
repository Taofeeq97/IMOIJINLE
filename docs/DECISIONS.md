# Architecture Decisions Log

Format: Context → Options → Decision → Consequences.

---

## D-001 — Package managers

**Context:** Spec allows uv or poetry for Python; pnpm for frontend.

**Options:** (a) poetry + pnpm (b) uv + pnpm

**Decision:** **uv** for backend, **pnpm** for frontend.

**Consequences:** Faster installs; `uv sync` / `uv run` in Makefile; record in README.

---

## D-002 — URL architecture

**Context:** Client undecided on subdomain vs subfolder.

**Options:** (a) `learn.imoijinle.com` (b) `imoijinle.com/learn`

**Decision:** Default **subdomain** `learn.imoijinle.com`. `BASE_URL`, `COOKIE_DOMAIN`, `CORS_ALLOWED_ORIGINS` are env-driven so either layout works without code changes.

**Consequences:** Cookie domain and CORS must be set per environment; no hard-coded hostnames in app code.

---

## D-003 — Brand assets

**Context:** Logo/palette not yet supplied.

**Options:** (a) invent a permanent brand (b) use file 06 tokens as placeholders via BrandSettings

**Decision:** Placeholder tokens from `06-DESIGN_SYSTEM.md` + player ink from file 10 §7. All colors/logo come from `BrandSettings` (DB + CSS variable injection).

**Consequences:** Swap branding without redeploying frontend code; seed default BrandSettings in `seed_demo`.

---

## D-004 — Display typeface

**Context:** Spec lists Fraunces or Cormorant Garamond.

**Decision:** **Fraunces** (variable) for display/hero; **Inter** for UI; **JetBrains Mono** for code.

**Consequences:** Loaded via `next/font` with subsetting; serif only on landing/hero titles.

---

## D-005 — Subject ↔ Course terminology

**Context:** Client wrote ambiguous mapping ("subject, course → topic…").

**Decision:** **Subject = Udemy Course**; Topic = Section; Subtopic = Lecture. Labels admin-renamable later via Terminology settings.

**Consequences:** UI copy uses Subject/Topic/Subtopic; internal docs note Course synonym.

---

## D-006 — App shells

**Context:** Frontend spec lists `(public)(auth)(student)(staff)(admin)`; agent prompt lists public/student/learning/staff-admin.

**Decision:** Four visual shells — **public**, **student**, **learning** (player), **staff/admin** — plus an `(auth)` route group without chrome. Staff and admin share one shell with role-gated nav.

**Consequences:** Learning shell is distraction-free with player-ink chrome; admin course-manage uses two-column checklist layout (M3).

---

## D-007 — TOTP 2FA timing

**Context:** Security spec requires TOTP for admin/finance; M0 exit is “login/roles work”.

**Decision:** M0 ships email/password + Google + JWT refresh rotation + throttling + Argon2. **TOTP deferred to M8** (hardening) with hooks reserved on User (`totp_secret` nullable).

**Consequences:** Admin/finance 2FA not enforced until M8; documented as known gap.

---

## D-008 — AuditLog shape

**Context:** Spec requires immutable audit with actor/action/object/before/after/ip/request_id; exact fields underspecified.

**Decision:**
```
AuditLog(id UUID, actor FK nullable, action str, content_type+object_id,
         object_repr, before JSON, after JSON, ip, user_agent, request_id,
         created_at)  # append-only; no update/delete
```

**Consequences:** GenericFK for object; middleware attaches request_id; helpers `audit.log(...)`.

---

## D-009 — Primary keys

**Context:** Spec mentions UUIDv7.

**Decision:** UUID primary keys via `uuid6`/`uuid_utils` UUIDv7 where available; fallback `uuid.uuid4` if library unavailable in env. Field type `UUIDField`.

**Consequences:** Time-sortable IDs preferred; migrations use UUID PKs from day one.

---

## D-010 — Local Python version

**Context:** Spec locks Python 3.12; host machine currently has 3.11.9.

**Decision:** Docker images use **python:3.12**. Local `requires-python = ">=3.11"` so host 3.11 can run tests; CI and Compose enforce 3.12.

**Consequences:** Prefer `make dev` via Compose for parity; document 3.12 requirement for production.

---

## D-011 — Money & timezone

**Context:** Locked in brief.

**Decision:** Money = `BigIntegerField` kobo + ISO currency code. Store UTC; default display `Africa/Lagos`.

**Consequences:** No floats for money anywhere; frontend formats with kobo→naira helpers.

---

## D-012 — Spec inconsistencies resolved for M0

| Conflict | Resolution |
|----------|------------|
| File 09 Session/Item vs file 10 Subject/Topic/Subtopic | File 10 wins post-M0; M0 has no content hierarchy |
| Enrollment unique(user,cohort) vs (user,class) | File 10: `(user, class)`; implement in M1/M2 |
| Application statuses PRD vs file 10 | File 10 statuses; M2 |
| Permissions matrix omits Applicant | Include Applicant role in M0 RBAC |
| Magic-link in auth list | Keep `/auth/magic-link` in M0 surface |

---

## D-013 — Seed demo credentials

**Decision:** Stable local passwords for all 8 FR-J-1 roles (documented in README). Pattern: `{role}@imoijinle.local` / `DemoPass123!`. Never use in production.

**Consequences:** `manage.py seed_demo` creates these users + RoleAssignments + default BrandSettings.

---

## D-016 — Cohort is the root (no Program)

**Context:** Earlier drafts had Program › Cohort. Client clarification: Cohort is the base container and behaves like an academic session; there is no Program concept.

**Decision:** Hierarchy is **Cohort › Class › Subject › Topic › Subtopic**. Admin UX and seed data create Cohorts directly. Legacy `Program` model/API retained only for migration compatibility and is not used in product flows.

**Consequences:** `/admin/cohorts` is the staff entry point; `/admin/programs` and `/programs` redirect; fee/certificate snapshots that still expose a `program` key carry the cohort name.

---

## D-014 — M1 Class slug + UniqueConstraint

**Context:** DRF auto-adds UniqueTogetherValidator for `UniqueConstraint(cohort, slug)`, which forces `slug` required even when `required=False`.

**Decision:** Disable serializer-level validators on `ClassSerializer` (`validators = []`); model `save()` still auto-generates slug; DB UniqueConstraint remains.

**Consequences:** Uniqueness enforced at DB/model layer, not DRF unique-together validator.

---

## D-015 — Payment secret storage (M1 shell)

**Decision:** Store Paystack secret via `django.core.signing` in `secret_key_encrypted`. GET `/settings/payments/gateway` returns only masked public key + `secret_key_set` boolean — never raw secret.
