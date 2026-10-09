# 05 — Frontend Specification (Next.js + shadcn/ui)

## 1. Stack
Next.js (App Router, React Server Components where useful, TypeScript strict), Tailwind CSS v4, **shadcn/ui** (Radix primitives), `lucide-react`, TanStack Query (server state), TanStack Table (+ virtualization), react-hook-form + zod, **Tiptap** (WYSIWYG), `dnd-kit` (reordering), `react-konva` (certificate designer), Recharts, `date-fns` + `date-fns-tz`, `next-intl`, `nuqs` (URL state), `sonner` (toasts), `cmdk` (command palette), `@mux/mux-player-react` (or `hls.js` + custom controls via Vidstack), `react-pdf` (receipts/preview), Zustand (ephemeral UI state only), Sentry, Playwright, Vitest + Testing Library, MSW (API mocks), Storybook.
Package manager pnpm. ESLint + Prettier + `eslint-plugin-jsx-a11y`. Husky pre-commit (typecheck, lint, test).

## 2. App structure
```
frontend/src/
  app/
    (public)/            landing, programs, programs/[slug], apply/[cohortSlug], apply/status/[token], verify/[code], pages/[slug]
    (auth)/              login, register, forgot, reset, accept-invite/[token], magic/[token]
    (student)/           dashboard, learn/[cohortId]/[classId]/[sessionId]/[itemId], calendar, grades, payments, certificates, notifications, profile
    (staff)/             tutor/...  (classes, roster, grading, announcements)
    (admin)/             admin/... (see §4)
    api/                 only BFF helpers (cookie refresh, Paystack callback relay if needed)
  components/ui/         shadcn primitives (owned code)
  components/            composed (DataTable, PageHeader, EmptyState, ConfirmDialog, RichTextEditor, RichTextView, FileDropzone, VideoPlayer, ProgressRing, StatusChip, MoneyText, DateRange, Stepper, FormBuilder, CertDesigner, ...)
  features/              one folder per domain: api hooks, schemas, components, utils (admissions, programs, learning, assessments, payments, certificates, analytics, comms)
  lib/                   api client (openapi-fetch), auth, query-client, money, dates, rbac, analytics, constants
  styles/                tokens.css, globals.css
  i18n/                  messages/en.json
```
Rules: features never import from other features' internals (use index barrels). All API types from generated `schema.d.ts`. Server components fetch public pages (SEO, ISR with tag revalidation); authenticated areas are client-driven with TanStack Query and prefetch/hydrate on navigation.

## 3. Auth, RBAC, routing
- Access token in memory, refresh via httpOnly cookie; Next middleware redirects unauthenticated users to `/login?next=`; role-based layout guards; `<Can action="grade" on={class}>` component using permissions returned by `/auth/me` (`permissions` list + scoped ids). 403 page and 404 page designed.
- Impersonation banner ("Viewing as Ada O. — Exit") persistent top bar.

## 4. Route map
**Public**: `/` (academy landing: hero, programs, how it works, testimonials, FAQ, "Apply now"), `/programs`, `/programs/[slug]` (syllabus accordion, cohorts open, fees preview, tutors, FAQs, sticky Apply CTA), `/apply/[cohortSlug]` (multi-step form), `/apply/status/[token]`, `/verify/[code]`.
**Student**: `/dashboard`, `/learn/[cohortId]` (class list with progression map), `/learn/.../[itemId]` (player), `/calendar`, `/grades`, `/payments` + `/payments/[invoiceId]` + `/payments/callback`, `/certificates`, `/notifications`, `/profile`, `/settings`.
**Tutor** `/tutor`: dashboard, `/classes/[id]` (overview, roster+progress, content, gradebook, announcements, attendance), `/grading` (queue), `/grading/[submissionId]` (speed-grader), `/students/[enrollmentId]` (360° view).
**Admin** `/admin`: dashboard; `/programs`, `/programs/[id]` (tabs: Overview, Cohorts, Application form, Fees, Certificate rules, Grading); `/cohorts/[id]` (Overview, Applications, Students, Groups, Classes & Sessions builder, Fees & Invoices, Gradebook, Announcements, Analytics, Settings); `/course-templates`; `/question-banks`; `/applications` (global inbox); `/students`; `/finance` (invoices, payments, custom charges, coupons, refunds, reconciliation, reports); `/certificates` (templates, designer `/certificates/templates/[id]/design`, issued, pending); `/comms` (announcements, email templates); `/settings` (brand, site pages, roles, integrations, audit log).

## 5. Key feature implementations

### 5.1 Resumable video player (critical)
Component `<LessonVideo videoId itemId />`:
1. Fetch `GET /video/{id}/playback-token` → `{playbackId, token, resumePositionS, rate, captionLang, duration}` (token short TTL, refresh before expiry).
2. Initialize player with `startTime=resumePositionS` (Mux Player `start-time`/`currentTime` set on `loadedmetadata`). Show toast "Resumed at 12:34 · Start over".
3. Progress tracker hook `useVideoProgress`: sample `timeupdate` into a local watched-segments set; flush `PUT /video/{id}/progress` every 10 s while playing, immediately on pause/seeked/ended/rate-change, and on `visibilitychange:hidden` / `pagehide` via `navigator.sendBeacon`. Keep a localStorage mirror (`video:{id}`) to resume offline and reconcile on reconnect (take newest `client_ts`).
4. Custom controls (shadcn-styled): play/pause, ±10 s, scrubber with watched-segment shading, speed (0.75–2×), captions, quality auto + manual, picture-in-picture, fullscreen, keyboard shortcuts (space, k, j, l, ←/→, m, f, c, `<`/`>`), chapter markers, theater mode, transcript side panel synced to time with click-to-seek, "Next lesson" auto-advance countdown (cancelable), and optional forward-seek lock.
5. Completion: when server returns `completed`, mark outline item with check and animate progress ring. Handle token expiry/403 (payment gate) with a paywall card.
6. Low-bandwidth: auto-quality, data-saver toggle (cap 480p), audio-only mode for audio-first spirituality lectures.

### 5.2 Content authoring (Tiptap)
Custom extensions: callout, tabs/accordion, embed (YouTube/Vimeo/Zoom link cards), video (Mux asset picker), file attachment, KaTeX, table, column layout, image with caption/alt required, slash menu, bubble menu, drag handle, autosave (debounced 1.5 s, optimistic with status "Saved · 2s ago"), revision history side sheet, read-only `RichTextView` renderer sharing the same schema; paste cleaning (Word/Docs); image upload with compression/WebP; a11y checks (headings order, alt text) surfaced as warnings.

### 5.3 Course/Session builder (admin & tutor)
Three-pane builder: left tree (Program → Cohort → Classes → Sessions → Items) with dnd-kit reorder (keyboard accessible), center editor, right inspector (schedule, drip, unlock rules via visual rule builder, completion rule, visibility, points). "Add item" menu (Lesson, Video, Resource, Quiz, Assignment, Live meeting, Discussion). Bulk schedule shifter ("move all sessions +1 week"), duplicate, preview-as-student toggle, publish checklist ("3 items missing due dates"). Timeline (Gantt-like) view of class schedule.

### 5.4 Quiz taker
One-question or all-on-page modes; sticky timer (server-synced; shows drift-corrected remaining time, warns at 5 min/1 min); question navigator with flagged/answered state; autosave per answer (debounced) with offline queue and visible "Saved" state; confirm-submit dialog listing unanswered; connection-loss banner; resume attempt on reload; keyboard operable; review screen respecting `show_answers`. Auto-submit at deadline.

### 5.5 Assignment submission & grading
Student: instructions, rubric preview, drag-drop uploader with progress/resume (tus or S3 multipart), text editor, link field, draft save, submit confirmation, late warning, version history, feedback view with rubric breakdown and inline comments. Tutor **speed-grader**: split view (submission viewer: PDF/image/doc/audio/video + text; right: rubric clickable grid, score, feedback editor, attach file), prev/next student with keyboard shortcuts, filter (ungraded/late), bulk release, comment bank snippets.

### 5.6 Application form renderer + builder
`FormRenderer` generates zod schema from server schema, supports conditional fields, sections as steps with progress, autosave draft, file uploads, review step, submit, optional pay step. Admin `FormBuilder`: palette → canvas drag/drop, field inspector (label, help, validation, options, visibility rules), live preview pane (mobile/desktop), version tag, templates.

### 5.7 Payments UI
Paystack Popup: dynamic import `@paystack/inline-js`, opened with server `access_code`; fallback redirect to `authorization_url`; callback status page polling `/payments/{ref}/status` (exponential backoff up to 60 s then "We're confirming, you'll get an email"). MoneyText formats kobo → ₦ with `Intl.NumberFormat('en-NG')`. Custom charge wizard + rule builder (see file 03 §5).

### 5.8 Certificate designer
`react-konva` canvas, state in Zustand with command-pattern undo/redo; JSON schema per file 04; server-rendered preview modal; autosave drafts.

### 5.9 Data tables
TanStack Table wrapper: server-side pagination/sort/filter, column visibility, saved views, sticky header, row selection + bulk-action bar, CSV export, density toggle, URL-synced filters (`nuqs`), skeleton rows, empty state.

### 5.10 Notifications & realtime
Bell with unread count, popover list, mark read, preferences page; SSE/poll hook `useLiveCount`. Toasts for transient events.

### 5.11 PWA & offline
Manifest, icons, service worker (Workbox) caching shell + visited lesson text + resources; offline banner; background sync for progress & quiz answers queue.

## 6. State & data fetching
- Query keys factory per feature; `staleTime` tuned (lists 30 s, outline 60 s, static 10 min); optimistic updates for reorder/complete/notes; error boundary per route segment; Suspense skeletons; `useMutation` wrappers surface field errors from API envelope into RHF.
- Prefetch next item's data and video token when ≥ 70 % through current.

## 7. Performance budget
JS ≤ 180 KB gz initial on public routes; route-level code splitting (designer, editor, charts dynamic-imported); `next/image` + AVIF/WebP; font subsetting (`next/font`); Lighthouse ≥ 90 mobile on public pages; Web Vitals reporting.

## 8. Testing
Vitest unit for hooks (`useVideoProgress` segment merging, quiz timer drift), component tests, MSW integration, Playwright E2E for the six acceptance flows in PRD §9, axe-core automated a11y checks in CI, visual regression on Storybook (Chromatic or Playwright snapshots).

---
# ADDENDUM v1.1

## A. Responsive & adaptive strategy (all screen sizes)
- **Mobile-first** Tailwind; min supported width **320 px**; breakpoints: `xs 360 / sm 640 / md 768 (tablet portrait) / lg 1024 (tablet landscape, small laptop) / xl 1280 / 2xl 1536 / 3xl 1920+`. Use **container queries** (`@container`) for components that live in both narrow rails and wide panes (cards, stat blocks, outline).
- Layout adaptation rules: nav = bottom tab bar (<md), collapsible rail (md–lg), full sidebar (lg+). Two-pane learner view: stacked (<md), outline as drawer + content (md), persistent outline + content (lg), + right rail (xl). Tables → card lists below md (`ResponsiveTable` renders column priorities); filters → bottom sheet on mobile; dialogs → full-screen sheets on mobile; popovers → drawers on touch.
- Tablets: support portrait + landscape + split-screen (≥ 320 px pane); touch targets ≥ 44 px; no hover-only affordances; pointer detection via `(hover:hover)` and `(pointer:coarse)`; stylus-friendly drag handles.
- Use `dvh/svh/lvh` (not `vh`), safe-area insets (`env(safe-area-inset-*)`), `viewport-fit=cover`, no horizontal scroll at any width, fluid type with `clamp()`, orientation change preserves state (video position, quiz answers, scroll).
- Foldables/large displays: cap reading width (68ch), center content in ultra-wide, use extra space for side panels not stretched lines.
- Video player: responsive 16:9, landscape-fullscreen on rotate (mobile), sticky mini-player while scrolling notes on mobile, tap zones (double-tap ±10 s), reduced-data mode.
- Forms: `inputmode`/`autocomplete`/`enterkeyhint` set, labels above inputs on mobile, sticky submit bar above keyboard (visualViewport aware), numeric/phone pads, date pickers native on mobile.
- Complex tools: **Course builder & form builder** are usable on tablet (landscape) with touch drag; on phone they degrade to a list-edit mode (reorder via menu, inspector as sheet). **Certificate designer**: full on ≥ md landscape/desktop; on phone show read-only preview + "Open on a larger screen" notice (still allow metadata edits). **Gradebook matrix**: sticky first column + horizontal scroll with column group collapse; compact mode on phone (per-student list).
- Charts: Recharts `ResponsiveContainer`, simplified legends/labels at small widths, tap tooltips, optional table view.
- Images: `next/image` with `sizes`, AVIF/WebP, Mux thumbnails by width; fonts subset; JS budgets unchanged.
- Test matrix (Playwright projects + real devices): 320×568, 360×640 (Android low-end), 390×844 (iPhone), 412×915, 768×1024 & 1024×768 (iPad), 820×1180, 1280×800, 1440×900, 1920×1080, 2560×1440; Chrome/Safari/Firefox/Samsung Internet; 4G-slow and 3G throttle profiles; touch + keyboard-only runs; Storybook viewport snapshots for every shared component.

## B. Study-time gate (`useStudyTimer`)
- Hook sends heartbeats per backend addendum (every 15 s), tracks `active` via Page Visibility API + focus + interaction events (pointer, scroll, keydown, touch) + video `playing`; idle after configured timeout → pause + "Still there?" toast with "I'm here" action; `sendBeacon` on `pagehide`.
- Server response is the source of truth: UI shows `remaining_s` from last response, interpolated locally each second while active; resync on every heartbeat/focus.
- `<CompleteButton>` states: disabled with ring-countdown ("Stay 08:42 more"), enabled "Mark as done", loading, done. Tooltip/aria-live announces at thresholds (halfway, 1 min left, ready). If API returns `MIN_TIME_NOT_MET`, show remaining time and keep disabled.
- Outline shows small clock badge on items with a requirement and a partial ring while accumulating; session header shows total time vs required.
- Authoring UI (tutor/admin): in the item inspector and class defaults: "Estimated time" and "Minimum time to stay" inputs (minutes, with presets 5/10/15/30), "Apply to all items in this session/class", live hint "Students can complete this after 20 min of active reading". Staff view: per-item avg time chart and per-student time column.
- Accessibility: timer never traps; screen-reader announcement polite; reduced motion shows text countdown only.

## C. Finance UI components
`KpiCard` (with delta + sparkline), `TrendChart` (compare toggle), `FunnelChart` (attempts→success), `AgingBar`, `ChannelDonut`, `FailureReasonsList`, `ForecastChart`, `TransactionsTable` (payments/attempts toggle, drawer with event timeline), `LedgerDrawer`, `DeadlinePicker` (None / Fixed / Relative / Per-installment), `NotificationMatrix`, `ScheduledReportForm`. All wired to `/finance/*` endpoints with URL-synced filters (`nuqs`), skeletons, empty states, CSV/XLSX export buttons, and responsive variants (see A).

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
