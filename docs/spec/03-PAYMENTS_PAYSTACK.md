# 03 — Payments Specification (Paystack)

Gateway: **Paystack** (REST at `https://api.paystack.co`). All amounts are integers in **kobo** (NGN × 100). Secret key lives only on the backend; the frontend never calls Paystack's API with the secret key. Use Paystack **Popup/Inline JS or redirect checkout** on the frontend with a backend-initialized transaction.

## 1. Design principles
1. **Invoice-first**: every payment pays one or more Invoice lines. Money in = Payment rows; money owed = Invoice; truth = double-entry-ish `LedgerEntry`.
2. **Server decides amounts**. The client never supplies amount; backend computes from invoice balance (or an allowed partial amount within rules).
3. **Webhook is source of truth, verify is the fallback.** Both paths funnel into one idempotent `settle_payment(reference)` service.
4. **Always verify amount, currency, and reference ownership** before crediting (Paystack guidance: confirm the amount matches what you are delivering).
5. **Everything flexible = data**: fee rules in DB, editable in admin UI.

## 2. Data model
- `FeeItem(name, code, kind[tuition|application|addon|materials|late_fee|custom], amount_minor, currency, taxable, description, active, refundable_policy JSON)`
- `FeeRule(fee_item, scope_type[all|program|cohort|class|group|enrollment|user], scope_id, mode[mandatory|optional], billing[one_off|installments|recurring], plan JSON, due_rule JSON, gate_rule JSON, priority, starts_at, ends_at)`
  - `plan` e.g. `{installments:[{pct:50,due:"on_admission"},{pct:30,due:"+30d"},{pct:20,due:"cohort_start+60d"}]}` or `{count:4,interval:"monthly",first_due:"cohort_start"}`.
  - `gate_rule` e.g. `{block:"cohort_access"|"class:ID"|"session:ID"|"none", grace_days:7}`.
  - Resolution: collect all matching rules for an enrollment, narrower scope wins (`user > enrollment > group > class > cohort > program > all`), ties by `priority`; `exclusive` flag stops fall-through.
- `CustomCharge(title, description, amount_minor, target_type[cohort|class|group|enrollments|user], target_ids[], mandatory, due_at, gate_rule, created_by, notify)` → service `create_custom_charge` fan-outs into `Invoice`s (one per recipient) inside a transaction + Celery email job. Preview endpoint returns recipient count & total before confirm.
- `Invoice(number [IMO-2027-000123], enrollment|application|user, status[draft|issued|partially_paid|paid|overdue|void|refunded], currency, subtotal, discount_total, tax_total, total, amount_paid, due_at, issued_at, source[rule|custom|application], meta)`; `InvoiceLine(invoice, fee_item?, description, qty, unit_amount, discount_minor, installment_no, due_at)`.
- `Discount(kind[percent|fixed], value, scope, reason, created_by)`, `Coupon(code, discount, max_redemptions, per_user_limit, valid_from/to, scope)`, `Waiver/Scholarship(enrollment, invoice_lines|percent, sponsor, approved_by)`, `SponsorPayer(name,email)` for third-party pay links.
- `Payment(invoice(s) via PaymentAllocation, amount_minor, currency, provider='paystack', reference unique, status[initiated|pending|success|failed|abandoned|reversed|refunded], channel, authorization_code, customer_code, paystack_id, paid_at, fees_minor, raw JSON, idempotency_key)`; `PaymentAllocation(payment, invoice_line, amount_minor)`.
- `PaymentAttempt(invoice, user, reference, access_code, authorization_url, expires_at)`.
- `SavedAuthorization(user, authorization_code(encrypted), last4, bank, brand, reusable, consent_at, signature)` — only if student consents; used for scheduled auto-charge.
- `Refund(payment, amount_minor, reason, status, paystack_refund_id, requested_by, approved_by)`.
- `LedgerEntry(account, debit/credit, amount_minor, ref_type, ref_id, occurred_at)` — accounts: receivables, cash/paystack_clearing, revenue, discounts, refunds, waivers.
- `PaystackWebhookEvent(event_id/hash, type, payload, signature_valid, received_at, processed_at, status, error)` unique on payload hash for dedup.

## 3. Flows

### 3.1 Standard checkout
1. Student opens Invoice → "Pay now" (full balance, or partial/installment line if allowed).
2. `POST /payments/initiate {invoice_id|line_ids[], amount_minor?}` with `Idempotency-Key`. Backend validates ownership, balance, min/max partial rules, creates `Payment(initiated)` with a unique **reference** (`IMO-{uuid}`) and calls Paystack `POST /transaction/initialize` with `email, amount, currency, reference, callback_url, metadata{invoice_id, enrollment_id, payment_id, env}, channels?` (+ `subaccount`/`split_code` when revenue sharing applies). Returns `{authorization_url, access_code, reference}`.
3. Frontend opens Paystack Popup (`access_code`) or redirects. Callback page `/payments/callback?reference=` calls `GET /payments/{reference}/status`; the backend calls Paystack **verify** (`GET /transaction/verify/:reference`) if still pending.
4. `settle_payment(reference)` (idempotent, `select_for_update`): checks `status==success`, `amount==expected`, `currency`, `reference` belongs to Payment; creates allocations, updates invoice status/balance, writes ledger, emits `payment.succeeded` signal → unlock gates, receipt PDF/email, notification, progress/risk updates.

### 3.2 Webhook (`POST /api/v1/webhooks/paystack`)
- Read **raw body bytes**; compute HMAC-SHA512 with the Paystack secret key; compare in constant time to `x-paystack-signature`. Reject otherwise (401). Optionally enforce Paystack source IP allowlist (configurable).
- Persist `PaystackWebhookEvent` first, return 200 fast, process in Celery (queue `payments`). Dedup via payload hash/event id.
- Handle events: `charge.success`, `charge.failed`?, `transfer.*` (if payouts used), `refund.processed|failed|pending`, `subscription.*` / `invoice.*` (if Paystack Plans are used), `paymentrequest.success`.
- Always re-verify via API before crediting on `charge.success` when metadata is ambiguous.
- Webhook handler must be safe to replay (admin action "replay event").

### 3.3 Installments & recurring
Two supported strategies (configurable per FeeRule):
- **Scheduled invoices (default)**: system creates one invoice line per installment with due dates; student pays each manually or opts into **auto-charge** — after first successful card payment with `reusable` authorization and explicit consent, Celery `payments.autocharge_due` calls Paystack `POST /transaction/charge_authorization` on the due date (amount from the line, new reference). Failure → retries (T+1, T+3), notify, then dunning.
- **Paystack Plans/Subscriptions** for truly fixed recurring fees: create Paystack Plan via API, subscribe customer; sync via `subscription.*`/`invoice.*` webhooks into Invoice/Payment. Offer only if admin enables; default is the scheduled-invoice strategy (more control over gating, discounts, custom amounts).

### 3.4 Bank transfer / USSD / mobile money
Enabled via Paystack channels list; pending states handled by webhook; invoice shows "awaiting confirmation" with polling + manual "I've paid" refresh (verify). Optional **offline payment record** by Finance Admin (cash/bank deposit) with proof upload, approval, audit.

### 3.5 Application fee
Public applicants have no account: `POST /public/applications/{token}/pay` creates a Payment tied to Application (email from form). On success, application flips `draft→submitted` (or stays submitted and flagged `fee_paid`).

### 3.6 Refunds
Admin requests → approver confirms → backend calls Paystack `POST /refund {transaction: reference|id, amount?}` → status updated via `refund.*` webhook; ledger + invoice adjusted; enrollment gating re-evaluated; student notified.

### 3.7 Revenue sharing (optional, configurable)
Paystack **Subaccounts** and **Transaction Splits** let one payment divide between main account and partners. Support: `SubaccountConfig(name, paystack_code, percentage|flat, bearer)` and a `SplitRule` (per FeeItem/Cohort); initialize passes `subaccount`/`split_code` (static split) or inline dynamic split. Admin UI to create/list subaccounts via backend proxy.

## 4. Gating & dunning
- `gate_rule` evaluated by `access.can_access(enrollment, target)`; cached per enrollment 60 s, invalidated on payment/waiver/override.
- States: `current → due_soon → overdue(grace) → blocked`. Student sees a non-judgmental banner with "Pay now"; blocked content shows a paywall card, never a 500.
- Admin override: grant temporary access until date with reason (audited). Finance can extend due dates or waive.
- Dunning schedule configurable (default T-7, T-1, due, +3, +7), via email + in-app; stop upon payment.

## 5. Admin UI requirements
Fee catalog; rule builder with scope picker & "who is affected" live preview; custom charge wizard (choose target → amount → due → mandatory/gating → preview recipients → confirm); invoice list with filters; student ledger drawer; coupons; waivers/scholarships; refunds queue; reconciliation (Paystack transactions vs local, mismatch report, CSV import of settlement); revenue dashboards (collected, outstanding, overdue aging, by cohort/class/fee item); exports.

## 6. Student UI requirements
"My payments" page: outstanding, upcoming, history, receipts; pay by invoice or selected lines; coupon entry; saved cards management; clear status chips; receipts as PDF; failure recovery ("try again", "use another method"); success page with next step.

## 7. Security & compliance
Never log PANs (Paystack hosts card entry). Store only reference/last4/brand. Encrypt `authorization_code`. Separate test/live keys via env; visible TEST MODE banner for admins in non-prod. Rate-limit initiate endpoint. Reject amounts mismatching server calc. Currency locked per invoice. Reconciliation job alerts Sentry on mismatch. Keep payment tables append-mostly; no deletes.

## 8. Config (env)
`PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY`, `PAYSTACK_BASE_URL`, `PAYSTACK_WEBHOOK_IP_ALLOWLIST` (optional), `PAYMENTS_DEFAULT_CURRENCY=NGN`, `PAYMENT_CALLBACK_URL`.

## 9. Tests
Unit: fee resolution precedence, installment generation, partial payments, discounts stacking, rounding (largest-remainder to kobo). Integration with Paystack mocked (`responses`/`respx`): initialize, verify, webhook valid/invalid signature, duplicate webhook, amount mismatch, failed charge, refund. Concurrency: simultaneous webhook + callback verify settle once. E2E in Paystack **test mode** with test cards.

---
# ADDENDUM v1.1 — Optional deadlines, notifications, and finance analytics

## 1. Optional deadlines
- `due_at` / `due_rule` are **nullable** on `FeeRule`, `CustomCharge`, `InstallmentPlan` lines, `Invoice` and `InvoiceLine`. Admin UI: "Set a payment deadline" toggle; when off, no date appears anywhere.
- Semantics when `due_at IS NULL`: invoice status is never `overdue`; no date-based reminders; invoice shows "Pay any time"; the gate rule (if any) applies from creation until paid (e.g. "block Class 2 until paid"); a per-rule **optional "soft nudge"** may send a periodic reminder every N days (off by default).
- Deadline types: fixed date, relative (`+14d` from issue / admission / cohort start / class open), per-installment dates. Optional **grace_days** and **late_fee** (fixed/percent, once or recurring, cap) only when a deadline exists.
- Admins/finance can add, extend, move or remove a deadline on an existing invoice (reason, audited; student notified if configured). Bulk-edit deadlines for a charge/cohort.

## 2. Configurable payment notifications
`PaymentNotificationConfig(scope_type[global|program|cohort|fee_item|custom_charge], scope_id, event, enabled, channels[email|in_app|sms?|whatsapp?], recipients[student|sponsor|finance_team|program_admin|tutor|custom_emails], offsets JSON, template FK, quiet_hours, send_digest)`; most specific scope wins, falling back to global defaults.
Events:
`invoice_issued`, `invoice_updated`, `invoice_voided`, `payment_initiated` (internal), `payment_succeeded` (receipt), `payment_failed`, `payment_abandoned` (nudge after N hours), `payment_pending_confirmation` (bank transfer), `partial_payment_received`, `installment_due_soon` (offsets e.g. -7d,-1d), `due_today`, `overdue` (offsets +1d,+3d,+7d), `access_suspended`, `access_restored`, `autocharge_upcoming`, `autocharge_failed`, `refund_requested|processed|failed`, `waiver_applied`, `coupon_applied`, `deadline_changed`, `credit_balance_available`; staff-only: `large_payment_received` (threshold), `webhook_failure`, `reconciliation_mismatch`, `daily_finance_summary`, `weekly_finance_report`.
Rules: critical notices (receipts, failures, security) cannot be disabled by the student; marketing-style nudges respect student preferences; no sends in quiet hours (default 21:00–07:00 WAT) except receipts; per-event rate limits; delivery log with status and resend; test-send button; variables preview. Templates editable (WYSIWYG) with variables like `{{student.first_name}}`, `{{invoice.number}}`, `{{amount_due}}`, `{{due_date|default:"no deadline"}}`, `{{pay_link}}`, `{{receipt_link}}`.

## 3. Attempt tracking (for "attempts vs paid")
- `PaymentAttempt` is created on every initiate (`initiated`) and updated through lifecycle: `opened` (popup/redirect shown, from client event) → `pending` → `success | failed | abandoned | expired`. Store `channel`, `failure_code/message` (from Paystack `gateway_response`), `device_type`, `attempt_no` per invoice, `time_to_complete_s`, `retry_of`.
- `PaymentEvent(attempt|payment, type, payload, occurred_at)` append-only timeline (client events, webhooks, verify results).
- Abandonment sweeper: attempts `initiated/opened` with no success after 30 min → `abandoned` (verify with Paystack first), triggers optional nudge.

## 4. Finance analytics (data + endpoints)
`FinanceDailyRollup(date, cohort?, class?, fee_item?, channel?, invoiced_minor, collected_minor, refunded_minor, discounts_minor, waived_minor, outstanding_minor, overdue_minor, attempts, successes, failures, abandoned, fees_minor)` built nightly + incrementally on events; reports read rollups (fast) with drill-down to raw rows.
Endpoints (all filter by date range, cohort, program, class, group, fee item, channel, status, currency):
`GET /finance/overview`, `/finance/trends?granularity=day|week|month`, `/finance/attempts-vs-paid`, `/finance/failure-reasons`, `/finance/channel-mix`, `/finance/aging`, `/finance/collection-by-cohort`, `/finance/fee-item-performance`, `/finance/forecast`, `/finance/students/{id}/ledger`, `/finance/outstanding` (list), `/finance/reconciliation`, `/finance/exports` (async CSV/XLSX/PDF), `POST /finance/scheduled-reports`.
**Metrics**: total invoiced/collected/outstanding/overdue; collection rate (collected ÷ due-to-date); average days-to-pay; revenue trend & MoM growth; by cohort/class/fee item/group; installment adherence; discounts/waivers/scholarship totals; refund rate; Paystack fees paid and net settlement; payment-method mix; **attempts vs successful payments**: total attempts, unique payers, success rate, first-attempt success rate, avg attempts per paid invoice, abandonment rate, top failure reasons (insufficient funds, declined, timeout, bank unavailable, 3DS failure), best/worst channel, time-of-day heatmap, retry recovery rate (failed → later paid), funnel `invoice viewed → pay clicked → checkout opened → success`; **forecast**: expected inflows by due date for upcoming 30/60/90 days, weighted by historical collection rate; at-risk receivables (overdue aging buckets 1–7, 8–30, 31–60, 60+).

## 5. Finance UI (admin) — S-A12 expanded
- **Overview dashboard**: KPI row (Collected, Outstanding, Overdue, Collection rate, Success rate, Refunds) with deltas vs previous period; revenue trend (area/line, compare-to-previous toggle); collected vs invoiced by cohort (bar); aging stacked bar; channel mix donut; **Attempts vs Paid funnel + trend** (stacked: successes, failures, abandoned, with success-rate line); failure-reasons ranked list; forecast chart; top outstanding students (with quick "remind" action).
- **Transactions explorer**: table of payments and attempts (toggle), columns: reference, student, invoice, fee item, amount, channel, status, attempt #, failure reason, created/paid time; filters + saved views; row drawer with full event timeline, Paystack payload, actions (verify now, replay webhook, refund, send receipt, mark offline).
- **Student ledger drawer**: invoices, payments, attempts, credits, waivers, notes, timeline; actions (extend/remove deadline, waive, adjust, send reminder).
- **Charge/deadline manager**: list of charges with recipients paid/unpaid progress bars; bulk reminders; bulk deadline edit.
- **Notifications settings**: matrix of events × channels with scope selector, template editor, delivery log, test send.
- **Reports**: scheduled email reports (daily/weekly/monthly) to chosen finance recipients; exports.
- Tutors see only payment **status chips** for their students (paid/due/overdue), never amounts, unless granted.
- Mobile: KPI cards stack, charts become swipeable, tables become card lists, filters in a bottom sheet.

## 6. Student UI additions
Invoice shows "No deadline" or "Due 12 Jan" with countdown; installment timeline; clear attempt history ("Attempt 1 failed — insufficient funds. Try again") with a retry button; notification preferences for non-critical payment messages.

## 7. Extra tests
Null-deadline invoice never transitions to overdue; relative-deadline calculation; deadline removal re-evaluates gates; notification scope precedence; quiet hours; rollup totals equal raw-sum (property test); attempts-vs-paid math with retries; abandoned sweeper verifies with Paystack before marking.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
