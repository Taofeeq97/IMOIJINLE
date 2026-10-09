# 06 — Design System & Visual Direction

## 1. Design intent
**"Calm authority."** The Imo Ijinle ecosystem is anchored on Meditation: interfaces should feel spacious, grounded and luminous, never noisy. Premium academic rigor + contemplative warmth. Think: generous whitespace, soft depth, restrained color with one warm accent, typography with a literary serif for display and a highly legible sans for UI.

Principles: (1) **Focus first**: learning view removes chrome. (2) **Progress is visible**: rings, bars, maps everywhere. (3) **One primary action per screen.** (4) **Forgiving**: autosave, undo, clear recovery. (5) **Low-bandwidth kind**: lean assets, skeletons over spinners. (6) **Culturally resonant, not stereotyped**: subtle geometric motifs (concentric rings echoing meditation/the pillar diagram), no clichéd imagery.

All tokens are overridable through `BrandSettings` (CSS variables injected at runtime) because brand assets are not final.

## 2. Color tokens (placeholders; HSL via shadcn convention)
| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | #FBFAF7 (warm paper) | #0F1412 | page |
| `--foreground` | #16201C | #ECEFEA | text |
| `--card` | #FFFFFF | #151C19 | surfaces |
| `--muted` | #F1EFE9 | #1C2420 | subtle fills |
| `--muted-foreground` | #5B6B63 | #9AA8A0 | secondary text |
| `--primary` | #1F5C4D (deep forest/jade — grounding) | #4FB39A | primary actions |
| `--primary-foreground` | #FFFFFF | #07211A | |
| `--accent` | #C8943A (saffron/gold — wisdom) | #E2B462 | highlights, certificates, achievements |
| `--secondary` | #E7EFEB | #1F2B26 | secondary buttons |
| `--border` / `--input` | #E3E0D8 | #26312C | |
| `--ring` | #1F5C4D | #4FB39A | focus |
| `--success` #2E7D4F · `--warning` #B7791F · `--destructive` #B3372F · `--info` #2B6CB0 |
Pillar accents (for ecosystem cross-links): Medical #2F7F79, Innovation #3B5BA9, Spirit Science #7A4FA0 (the Academy's own tint, used in avatars/badges), Business #B5651D. Contrast: all text ≥ 4.5:1, UI components ≥ 3:1, verified in CI.
Status colors map to chips: Applied (info), Under review (warning), Admitted (success), Waitlisted (muted), Rejected (destructive), Overdue (destructive), Locked (muted w/ lock icon).

## 3. Typography
- Display / headings: **Fraunces** or **Cormorant Garamond** (variable, subset) — editorial feel for hero, program titles, certificate default.
- UI/body: **Inter** (variable) — tables, forms, dashboards. Tabular numerals for money/scores.
- Mono: **JetBrains Mono** (code blocks).
- Scale (rem): 12, 14 (UI base), 16 (reading base), 18, 20, 24, 30, 36, 48, 60. Reading content max-width 68ch, line-height 1.7; UI line-height 1.4. Headings tracking −0.01em.
- Yoruba diacritics must render (Inter + Fraunces cover Latin Extended; test "ẹ ọ ṣ ń").

## 4. Spacing, radius, elevation, grid
4-pt spacing scale (4,8,12,16,24,32,48,64,96). Radius: `--radius: 0.75rem` (cards 12, inputs 10, chips full). Elevation: 3 levels, soft low-opacity green-tinted shadows; avoid heavy borders+shadows together. 12-col grid, max container 1200 (public), 1440 (admin), fluid learner player. Breakpoints: sm 640, md 768, lg 1024, xl 1280, 2xl 1536.

## 5. Motion
Durations 120/200/320 ms, easing `cubic-bezier(0.2,0.8,0.2,1)`. Use for: dialog/sheet entrance, progress ring fills, checkmark draw on completion, list reorder. Celebratory moments (class complete, certificate earned): gentle gold shimmer + confetti-lite (disabled under `prefers-reduced-motion`). Page transitions: fade only. No parallax.

## 6. Iconography & imagery
lucide-react (1.5 px stroke). Motif: concentric ring/lotus-geometry SVG used sparingly as backgrounds (≤ 6 % opacity) and in empty states. Illustrations: simple line-art with accent fill; real photography for programs with art direction brief (natural light, community, nature, study). Avatars: initials on pillar-tinted backgrounds.

## 7. shadcn/ui component inventory & customizations
Use: Button (variants: default, secondary, outline, ghost, destructive, link, **gold** for achievement CTAs), Input, Textarea, Select, Combobox, Checkbox, RadioGroup, Switch, Slider, Calendar/DatePicker (range), Form, Label, Dialog, AlertDialog, Sheet, Drawer (mobile), Popover, Tooltip, DropdownMenu, ContextMenu, Command, Tabs, Accordion, Collapsible, Card, Badge, Avatar, Progress, Skeleton, Separator, ScrollArea, Table, Pagination, Breadcrumb, NavigationMenu, Sidebar, Sonner, Alert, Toggle(Group), HoverCard, Resizable, Carousel, Chart wrapper.
Custom composites (design them once, reuse everywhere): `ProgressRing`, `ProgressBar (segmented)`, `StatusChip`, `MoneyText`, `StatCard`, `Timeline`, `DataTable`, `FileDropzone`, `RichTextEditor/View`, `RuleBuilder`, `FormBuilder`, `VideoPlayer`, `OutlineTree`, `EmptyState`, `PaywallCard`, `ResumeCard`, `CertificatePreview`, `CommandPalette`, `StepWizard`, `AuditTimeline`.

## 8. Layout shells
- **Public shell**: sticky translucent header (logo, Programs, About, Verify, Login, Apply), footer with ecosystem links (Medical, Innovation, Business) per client taxonomy.
- **Student shell**: slim left rail (desktop) / bottom tab bar (mobile: Home, Learn, Calendar, Pay, Me); top bar with search (⌘K) and notifications.
- **Learning shell**: distraction-free; collapsible outline; progress bar at top; "Back to class".
- **Staff/Admin shell**: collapsible sidebar with grouped nav, breadcrumb header, global command palette, environment/test-mode badge.

## 9. Accessibility
WCAG 2.2 AA: visible focus (2 px ring + offset), full keyboard paths (including drag-and-drop alternatives via "Move up/down" menu), ARIA live regions for toasts/timers, captions on videos, reduced motion, 44 px min touch targets, form errors tied by `aria-describedby`, don't rely on color alone, skip links, language attribute, correct heading order, accessible data tables, timer announcements at thresholds, extra-time accommodations.

## 10. Dark mode & theming
System-default with toggle; tokens only (no hard-coded hex in components); certificate/preview canvases are always light.

## 11. Content & voice
Warm, plain, respectful. "Pick up where you left off." not "Resume course." Errors say what happened and what to do. Avoid dark patterns in payment reminders; use neutral, supportive language.

---
# ADDENDUM v1.1

## 12. Responsive design system (all sizes)
- **Device classes**: Phone (320–639), Tablet portrait (640–1023), Tablet landscape / small laptop (1024–1279), Desktop (1280–1919), Large (≥1920). Design every component at 360, 768, 1024, 1440; verify 320 and 1920+.
- **Fluid tokens**: type `clamp()` scale (body 15→16 px, h1 28→48 px), spacing scales up ~1.25× on large screens, container gutters 16 / 24 / 32 px. Cap reading measure at 68ch and dashboard width at 1440 px (admin may go fluid with max 1680).
- **Touch**: targets ≥ 44×44 px (≥ 48 for primary actions on phones), 8 px minimum spacing between targets, thumb-zone placement of primary actions (bottom bars/sheets on phones), swipe gestures always have visible alternatives.
- **Patterns by size**: nav (bottom tabs → rail → sidebar); dialogs (full-screen sheet → centered modal); tables (cards → compact table → full table); filters (bottom sheet → inline bar); tabs (scrollable chips → standard tabs); charts (simplified, swipeable → full); forms (single column → two column only ≥ lg).
- **Orientation**: landscape phone gives video max height with outline hidden; tablets landscape use two-pane master/detail everywhere (roster/detail, inbox/drawer, class/outline).
- **Density modes**: comfortable (default phone/tablet), compact (desktop admin tables) with user toggle.
- **Input modality**: styles keyed to `(pointer:coarse)` vs `(hover:hover)`; hover affordances always have a tap/focus equivalent.
- **Performance on low-end devices**: skeletons, no heavy blur/backdrop-filter on phones, animations transform/opacity only, `content-visibility:auto` for long lists, virtualization for lists > 100 rows.
- **Text resilience**: layouts must survive 200 % browser zoom and OS large-text settings, long Yoruba/Igbo/Hausa names, and 30 % longer translations.

## 13. Component additions
`StudyTimerBadge`, `CountdownRing`, `CompleteButton`, `KpiCard`, `FunnelChart`, `DeadlinePicker`, `NotificationMatrix`, `ResponsiveTable`, `BottomSheetFilters`, `StickyActionBar`. Each requires Storybook stories at 4 viewport sizes plus light/dark.

## 14. Study-time visual language
Calm, non-punitive: a thin progress ring around the Done button fills as time accrues; copy "Take your time — 08:42 left" not "You cannot proceed". Idle prompt is gentle ("Still reading? Tap to continue"). Completed state uses a soft gold check.

---
# ADDENDUM v1.2 — SUPERSEDED IN PART BY FILE 10
The admissions flow, content hierarchy (**Cohort › Class › Subject › Topic › Subtopic**; Session/Item are now Topic/Subtopic), Udemy-style authoring workspace, Udemy-style student player and the Payment Configuration page are defined in `10-UDEMY_MODEL_AND_FLOW_v1.2.md`. Where this file conflicts with file 10, **file 10 wins**. Map terms: Session→Topic, Item→Subtopic, ClassInstance→Class, course/lesson→Subject/Subtopic, fee scopes now include `class` and `subject`.
