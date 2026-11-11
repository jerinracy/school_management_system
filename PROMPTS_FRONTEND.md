# FRONTEND PROMPTS — React SPA Dashboard via django-vite (School Management System)

## How to use
- Lives inside the **Django repo** under `frontend/`. Same `AGENTS.md` (Part A + B) and `SKILLS.md`.
- Run a frontend task only after the backend task that provides its API is DONE (dependency noted in each task).
- Paste the **Master Preamble** once per session, then **one task** at a time.

---

## MASTER PREAMBLE (paste at the start of every session)

```
You are the frontend engineer for the Admin Dashboard of a Bangladeshi School Management System.
Stack: React 18 + TypeScript (strict) + Vite, served by Django through django-vite, TanStack Query, React Router,
React Hook Form + Zod, Tailwind + shadcn/ui, i18next (bn/en), openapi-typescript generated API client.

BEFORE ANYTHING ELSE:
1. Read AGENTS.md, SKILLS.md, docs/PLAN.md, docs/TASKS.md, docs/DECISIONS.md and schema/openapi.yml.
2. Follow the mandatory workflow in AGENTS.md §A2:
   Phase 1 = post an IMPLEMENTATION REPORT (what you will implement, what will change [file table incl. new
   dependencies], API/contract impact, effects/risks, test plan, assumptions) and STOP until I reply "approved".
   Phase 2 = implement only what was approved. Phase 3 = run lint, typecheck, tests, build and show real output.
   Phase 4 = COMPLETION REPORT; update docs/TASKS.md and CHANGELOG.md.
3. Load and name the skills you use (confirm-and-report, ui-ux-design, react-spa-dashboard, django-vite-integration,
   api-contract-openapi, testing-strategy, debugging...).
4. Never invent API shapes: use generated types from schema/openapi.yml. If the backend lacks something, STOP and report
   the gap instead of mocking it silently (MSW mocks are allowed only for tests/Storybook and must be labeled).
5. Every text is translatable (bn/en). Every list has loading/empty/error states. Every route/action is permission-guarded.

Acknowledge with "READY" and wait for the task.
```

## COMMON FOOTER (agent must satisfy on every task)
```
Acceptance always includes: typecheck/lint/test/build green, RTL tests for components, MSW-based tests for data flows,
permission-guarded routes tested, i18n keys in both bn.json and en.json (CI parity check), keyboard accessibility,
no console errors, no `any`, Completion Report.
```

---

# TASKS

## Task 01 — Vite + React + django-vite Setup
```
TASK F01 — FRONTEND PROJECT SETUP (depends on Backend Task 01)

Goal: A working React SPA served by Django via django-vite in dev (HMR) and prod (manifest).

Scope:
1. Create frontend/ with Vite + React + TypeScript strict; ESLint (typescript-eslint, react-hooks, jsx-a11y), Prettier,
   Vitest + RTL + MSW, Playwright skeleton, husky/lint-staged (or pre-commit).
2. vite.config.ts: build.manifest true, outDir into Django static (e.g. backend/static/dashboard), base for prod,
   dev server strictPort + origin, /api proxy to Django, path alias @/.
3. Django side (minimal, list changes in the report): template templates/dashboard/index.html using
   {% load django_vite %}, {% vite_hmr_client %}, {% vite_react_refresh %}, {% vite_asset 'src/main.tsx' %};
   URL /dashboard/ + catch-all /dashboard/<path:path> (must not swallow /api, /admin, /static, /media); settings DJANGO_VITE.
   Verify exact settings keys against the installed django-vite version before using them.
4. Folder structure per AGENTS.md §B4; npm scripts: dev, build, lint, typecheck, test, gen:api, e2e.
5. `npm run gen:api` generates types/client from ../schema/openapi.yml (openapi-typescript + openapi-fetch or equivalent; justify choice).
6. CI job for frontend; Makefile targets (make fe-dev, make fe-build).
7. "Hello dashboard" page that calls /api/v1/health/ using the generated client.

Acceptance: dev mode with HMR works through Django's URL; prod build + collectstatic serves hashed assets; deep link /dashboard/students
reloads correctly; all scripts green.
Effects to report: static files config, template additions, Docker/compose changes (node service for dev), CSP/CORS implications.
```

## Task 02 — Design System, Layout & Theming
```
TASK F02 — DESIGN SYSTEM & APP SHELL

Use skills: ui-ux-design, react-spa-dashboard.

Deliver:
1. Design tokens (colors, spacing, radius, typography, elevation) via Tailwind theme + CSS variables; light/dark mode; Bangla-friendly typography
   (Noto Sans Bengali + Inter fallback, self-hosted fonts, line-height tuned for Bangla).
2. shadcn/ui base components installed and themed: Button, Input, Select, Combobox, DatePicker (Gregorian; Bangla month names), Dialog, Drawer, Tabs, Tooltip,
   Toast, Badge, Card, Table, Skeleton, Dropdown, Form primitives, Breadcrumbs, Pagination.
3. Composite components: AppShell (collapsible sidebar, topbar with branch switcher/session switcher/language toggle/notifications/user menu),
   PageHeader, DataTable (server-side pagination/sort/filter/column toggle/bulk select/row actions/empty/error/loading states), FilterBar (URL-synced),
   ConfirmDialog (shows impact), StatusChip (icon + text), StatCard, EmptyState, ErrorBoundary/ErrorPage, FileUpload (progress, type/size validation),
   PrintLayout (A4 @page styles).
4. Sidebar nav schema driven by config + permissions (items hidden when lacking permission); responsive down to tablet.
5. A /dashboard/_design page (dev only) showing all components in all states (acts as living style guide; or Storybook if you justify the dependency).
Report must list every new dependency with reason. Add a11y tests (axe) for shell + DataTable.
```

## Task 03 — API Client, Auth & RBAC UI
```
TASK F03 — AUTH, API CLIENT & PERMISSIONS (depends on Backend Task 03)

Deliver:
1. Typed API client wrapper: base URL, auth header, single-flight refresh on 401, error envelope mapping ({code,message,details}) → typed ApiError,
   request id, retry policy for idempotent GETs, abort support.
2. Auth store (Zustand or context — justify): access token in memory; refresh strategy per ADR from backend Task 03 (cookie vs body) — read the ADR and
   restate it in the plan. Session restore on reload, logout, logout-all, idle timeout warning.
3. Pages: Login (username/phone+password), OTP login (if enabled for admins), 2FA step, Forgot/reset password, Force-change-password,
   Profile (edit, change password, active sessions list with revoke, 2FA setup with QR).
4. Permission layer: `usePermission`, `<Can>`, `<ProtectedRoute perm=…>`, 403 page, post-login redirect; permissions from /auth/me.
5. i18n bootstrap (react-i18next): bn/en, language persisted + sent as Accept-Language, number/date formatters (Bangla digits toggle).
6. Query client defaults (staleTime, retry rules, global error toast for non-field errors).
Tests: refresh race (two parallel 401s → one refresh), permission-guarded routes, login errors, language switch.
```

## Task 04 — Institution Setup & Academic Structure Screens
```
TASK F04 — INSTITUTION & ACADEMICS UI (depends on Backend Tasks 02, 04)

Screens: Institution profile (logo/seal/signature upload, settings sections), Branches, Shifts, Sessions & Terms (activate/close with impact dialog),
Holidays (calendar view + list), Classes/Groups/Sections (bulk create), Subjects + class-subject mapping (marks components config),
Periods, Routine builder (weekly grid by section/teacher/room, drag-assign with conflict highlighting using backend validate endpoint),
Substitute assignments, Copy-structure-from-previous-session wizard (dry-run preview → confirm).
UX: wizard-style first-time setup checklist on dashboard home ("Setup progress").
Tests: routine conflict display, wizard dry-run flow, permission variants (Head vs Teacher read-only).
```

## Task 05 — Admission Management UI
```
TASK F05 — ADMISSION UI (depends on Backend Task 05)

Screens: Circular management, Applications list (filters by status/class/quota, bulk status change, export), Application detail (documents viewer, timeline of status changes,
payment status), Admission test scheduling + marks entry, Merit list generator (rule form, preview, publish), Lottery (run + show seed/verification), Waiting list,
Convert-to-student action, Result/notification sending, Public application form & status-check pages (separate lightweight route group; mobile-friendly; Bangla-first; CAPTCHA slot).
Print: admit card, application copy.
Tests: form validation (birth reg no, phone format), merit preview, public form accessibility, status transitions allowed/blocked.
```

## Task 06 — Students & Guardians UI
```
TASK F06 — STUDENTS & GUARDIANS UI (depends on Backend Tasks 06, 07)

Screens: Students list (powerful search: name/ID/roll/phone; filters class/section/group/status), Student profile (tabs: overview, guardians & siblings, documents,
attendance, results, fees, health [permissioned], timeline/audit), Add/Edit student (multi-step form), Bulk import wizard (template download → upload → validation
errors table → commit), Promotion wizard (select source, preview results-based eligibility, adjust, confirm), Transfer/TC/Testimonial issue flows with PDF preview,
ID card designer/printer (batch print with QR, Bangla names), Guardian management, Link/unlink guardians, Duplicate guardian merge, Alumni list.
Tests: import error mapping, promotion preview/confirm, guardian linking, PDF/print layout snapshot for ID card.
```

## Task 07 — Staff & HR UI
```
TASK F07 — STAFF & HR UI (depends on Backend Task 08)

Screens: Staff list/profile (qualifications, documents), Designations/Departments, Leave types & balances, Leave requests (approval queue with comments, calendar view of
who's away), Teacher assignments (matrix subject × section), Workload dashboard, Performance & training records, Staff ID cards.
Tests: leave approval flow, balance display, assignment matrix editing & conflict feedback.
```

## Task 08 — Biometric Device Management UI
```
TASK F08 — DEVICES UI (depends on Backend Task 09)

Screens: Devices list with live status (online/offline, last sync, firmware, storage) and auto-refresh, Add/Edit device wizard (type → vendor → protocol → connection
test → location → group), Device groups (map to user types), Enrollment manager (select users → choose method → send to device → status per user; consent capture step with
guardian consent for students), Device user mapping + Unmapped punches review queue (assign to user / ignore), Command history (retry/cancel), Device health charts,
Raw punch inspector (read-only).
Security UX: secrets never displayed after save (rotate only); consent required before enrollment; destructive device actions show impact.
Tests: wizard validation per protocol, unmapped queue assignment, consent gate.
```

## Task 09 — Attendance UI (Live, Policies, Corrections, Reports)
```
TASK F09 — ATTENDANCE UI (depends on Backend Tasks 10, 11)

Screens:
1. Live attendance board (today's present/late/absent by section, polling or SSE per backend decision; per-device feed).
2. Policy manager: per user type (student/teacher/staff/driver) with forms for methods (any-of/required), shifts/periods, grace/late/half-day/early-leave, multi-punch mode,
   holiday/exam overrides, effective dates; **Policy simulator** (paste/choose sample punches → see computed result).
3. Manual/bulk attendance entry by section & date (keyboard-friendly grid).
4. Corrections workflow (request → approve/reject with reason; diff view before/after).
5. Daily/monthly/period reports, late & absentee lists, staff attendance sheets, exception reports (missing punch, clock drift), export buttons (async download).
6. Low-attendance/exam-eligibility lists with warning letter generation.
Charts with table fallbacks; attendance statuses use icon + text + color.
Tests: policy form validation, simulator rendering, bulk entry grid keyboard navigation, correction diff.
```

## Task 10 — Examination UI
```
TASK F10 — EXAMS UI (depends on Backend Task 12)

Screens: Grading profile (view/edit scale with validation preview), Exam types & exams, Exam subjects/routine builder, Seat plan generator + print, Admit cards batch print,
Mark entry grid (by exam × section × subject; component columns; absent toggle; Excel paste/import; autosave-draft; validation vs max marks; lock status), Entry-progress tracker
(which teacher hasn't submitted), Lock/unlock approvals, Grace-mark rules, Re-scrutiny requests inbox.
Tests: grid keyboard flow, paste import validation, lock state read-only, permission (teacher only own subject).
```

## Task 11 — Results & Report Cards UI
```
TASK F11 — RESULTS UI (depends on Backend Task 13)

Screens: Result processing (run calculation → progress → review anomalies → publish), Tabulation sheet viewer/export, Marksheet & progress report card preview/print (bn/en),
Merit list views (class/section/group), Result analytics (subject performance, teacher performance, weak students, trends), Re-scrutiny handling, Promotion hand-off,
Public result search page (roll/ID + exam; rate-limit message handling).
Tests: report card print layout snapshot (Bangla), publish confirmation shows impact, analytics chart a11y fallback.
```

## Task 12 — Fees & Payments UI
```
TASK F12 — FEES UI (depends on Backend Task 14)

Screens: Fee heads/structures, Student fee assignment & invoice generation wizard (preview → confirm), Collection counter (fast search by student → due list → multi-method payment →
receipt print; keyboard-first), Online payment status & reconciliation, Waivers (request/approve), Refunds, Due list/defaulters with SMS reminder action, Daily collection report,
Money receipt reprint (marked "Duplicate"), Advance balances.
Money display: ৳ with Bangla/English digits; never use floating math in UI (use decimal strings or a decimal lib).
Tests: payment form validation, overpay prevention messaging, receipt print snapshot, permission (Accountant vs Teacher).
```

## Task 13 — Accounting & Payroll UI
```
TASK F13 — ACCOUNTING & PAYROLL UI (depends on Backend Task 15)

Screens: Chart of accounts tree, Vouchers (entry with balance check), Cash/bank book, Bank reconciliation, Budgets/Funds, Financial reports (P&L, trial balance,
balance sheet), Salary structures, Payroll run wizard (generate → review per staff → approve → payslips → bank advice export), Payslip print (Bangla), Period lock controls.
Tests: voucher debit=credit validation, payroll review edits, period-locked read-only behaviour.
```

## Task 14 — Communication UI
```
TASK F14 — COMMUNICATION UI (depends on Backend Task 16)

Screens: Notice board (create with audience targeting + schedule + attachments, preview, pin/expire), Templates manager (bn/en with variable picker + Bangla SMS segment/cost counter),
SMS gateway settings + balance, Delivery logs (filter by channel/status), Chat inbox (teacher↔guardian, moderation), Emergency broadcast (two-step confirm), PTM scheduler,
Complaint/suggestion inbox, Notification preferences.
Tests: audience selector resolution preview, SMS segment calculator (Unicode), two-step emergency confirm.
```

## Task 15 — Learning, Library, Transport, Hostel UIs
```
TASK F15 — OPERATIONS MODULES UI (depends on Backend Tasks 17, 18, 19, 20)

Split into 4 sub-deliverables (each its own Implementation Report; may be approved together but implemented sequentially):
15a Homework & study materials (teacher/admin views, submission review/grading, syllabus tracker, online class links).
15b Library (catalog search, barcode/RFID scan input mode for issue/return, overdue, members, reservations, fines).
15c Transport (vehicles, drivers, routes/stops editor, assignments, expiry alerts, live map [choose OSM/Leaflet — justify; no API keys in repo], boarding logs).
15d Hostel (feature-flagged: rooms/beds grid, allocation, gate pass approval, meal attendance) — hidden when flag off.
Tests: barcode scan input handling, route stop reorder, feature-flag hiding.
```

## Task 16 — Health, Safety, Events, Inventory UIs
```
TASK F16 — SUPPORT MODULES UI (depends on Backend Tasks 21, 22, 23)

16a Health & safety (restricted access with "view is audited" notice, sick room, incidents, visitor log with badge print, pickup verification screen for security role).
16b Co-curricular & events (clubs, event calendar, competitions/results, certificates generator, gallery with privacy flags and bulk upload).
16c Inventory & assets (assets, stock, movements, purchase orders, requisitions approvals, maintenance requests, low-stock alerts).
Tests: restricted-module permission, gallery privacy flag filtering, stock movement forms.
```

## Task 17 — Home Dashboard, Report Builder, Audit & Settings UI
```
TASK F17 — DASHBOARD & ADMIN TOOLS (depends on Backend Tasks 24, 25, 26)

Screens: Role-based home dashboards (Head: attendance, absentees, collections, dues, device status, pending approvals; Accountant: collection/dues; Teacher: today's classes,
pending mark entry), KPI cards with refresh/caching hints, charts with table fallback, Report builder (dataset → filters → columns → preview → save → export async w/ download center),
Download center (expiring links), Audit log viewer (filters, diff viewer), Import/Export center, Role & permission editor (matrix UI with diff + confirm), Integrations (API keys shown once,
webhooks, delivery logs), Security settings (2FA enforcement, sessions), Feature flags (hostel etc.).
Tests: dashboard permission variants, report builder whitelist UI, role matrix change confirmation.
```

## Task 18 — Bangla, Printing & Accessibility Pass
```
TASK F18 — i18n, PRINT & A11Y HARDENING

- i18n audit: scan for hard-coded strings (lint rule), bn/en key parity CI check, pluralisation, Bangla digit/date formatting, long-text overflow checks,
  Bangla search/sort (collation) in tables.
- Print/PDF audit: ID cards, admit cards, receipts, marksheets, certificates — verify Bangla glyph rendering, A4 margins, page breaks, QR readability; decide client-print vs server-PDF
  per document and document in DECISIONS.md.
- Accessibility audit: axe on all main routes, focus management, keyboard-only walkthrough of top 5 flows, reduced motion, color contrast.
Deliver an audit report + fixes (separate commits).
```

## Task 19 — Performance, E2E & Release
```
TASK F19 — QUALITY & RELEASE

- Performance: bundle analysis, route-level splitting, virtualised tables, memoisation where measured, image/PDF lazy loading, Lighthouse budget in CI.
- Playwright E2E (critical flows): login → admit student → attendance bulk entry → fee collection + receipt → mark entry → publish result → notice.
- Error monitoring (Sentry) with PII scrubbing; source maps handling in prod.
- Production build verification through Django (collectstatic, hashed assets, cache headers, CSP compatible with django-vite).
- Final docs: FRONTEND.md (architecture, conventions, how to add a module), CHANGELOG, known limitations.
```
