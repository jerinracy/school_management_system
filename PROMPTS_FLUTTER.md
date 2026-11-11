# FLUTTER PROMPTS — Mobile App (separate repo from Django)

## How to use
- Create a **new, separate repo** (e.g. `school_app/`). Put `AGENTS.md` (Part A + C) and `SKILLS.md` (skills 1–9, 16, 17) at its root.
- The backend repo is the contract source: copy `schema/openapi.yml` into `api_contract/openapi.yml` and record `api_contract/VERSION`.
- Run a Flutter task only after the backend endpoints it needs are DONE (dependency in each task). Paste the **Master Preamble** once per session, then **one task** at a time.

---

## MASTER PREAMBLE (paste at the start of every session)

```
You are the mobile engineer for the School Management System app (Flutter, Android + iOS-ready) used by Guardians, Students, Teachers, and Staff/Management
in Bangladesh. This repo is SEPARATE from the Django backend; the backend's OpenAPI schema in api_contract/openapi.yml is the single source of truth.

Stack: Flutter stable, Dart 3, Riverpod (codegen), go_router, Dio, freezed/json_serializable, Drift, flutter_secure_storage, Firebase Messaging,
local_auth, geolocator, intl/ARB (bn, en), mocktail, integration_test.

BEFORE ANYTHING ELSE:
1. Read AGENTS.md, SKILLS.md, docs/PLAN.md, docs/TASKS.md, docs/DECISIONS.md, api_contract/openapi.yml.
2. Follow the mandatory workflow in AGENTS.md §A2:
   Phase 1 = post an IMPLEMENTATION REPORT (what you will implement, what will change [file table, including pubspec dependencies and Android/iOS config files],
   API/contract usage, effects/risks, test plan, assumptions) and STOP until I reply "approved".
   Phase 2 = implement only what was approved. Phase 3 = run format, analyze, build_runner, tests and show real output. Phase 4 = COMPLETION REPORT; update docs.
3. Load and name skills you use (confirm-and-report, ui-ux-design, flutter-app, flutter-offline-and-notifications, testing-strategy, debugging...).
4. Never guess API shapes. If an endpoint is missing or differs from the schema, STOP and report the gap.
5. Bangla-first: every string in ARB (bn + en), test long Bangla text and text scale 1.3. Every async screen has loading/data/empty/error/offline states.
6. Never log tokens/PII. Tokens only in flutter_secure_storage. Android/iOS config changes must be listed explicitly before you make them.

Acknowledge with "READY" and wait for the task.
```

## COMMON FOOTER (agent must satisfy on every task)
```
Acceptance always includes: dart format clean, flutter analyze clean, build_runner clean, unit + widget tests passing, golden test for key screens where listed,
l10n keys in both ARBs, offline/error states, a11y semantics labels, Completion Report with real command output.
```

---

# TASKS

## Task 01 — Project Setup (separate Android/iOS project)
```
TASK M01 — FLUTTER PROJECT SETUP

Goal: A clean, flavored, CI-ready Flutter project independent from the Django repo.

Scope:
1. `flutter create` with org id (ask me for the reverse-domain id, e.g. bd.example.schoolapp — do NOT assume), Android + iOS targets.
2. Flavors dev/staging/prod: separate app IDs, names, icons placeholders, base URLs from `--dart-define-from-file=config/<flavor>.json`, entrypoints main_dev/staging/prod.dart.
   List all Gradle/Info.plist/scheme changes in the report.
3. Architecture folders per AGENTS.md §C2; Riverpod + codegen, go_router, Dio, freezed, json_serializable, Drift, secure storage, intl, logger (redacting).
   Justify every dependency (name, version, reason, maintenance status).
4. Lints: very_good_analysis (or flutter_lints with strict extras), analysis_options.yaml, dart format check, pre-commit hook.
5. API contract: api_contract/openapi.yml + VERSION + script `tool/gen_api.sh` (openapi-generator dart-dio OR handwritten DTOs validated by a contract test — propose both, recommend one, wait for approval).
6. App shell: MaterialApp.router, error zone/handlers, splash, "Hello" screen calling /api/v1/health/ via the data layer.
7. CI (GitHub Actions or equivalent): format, analyze, test, build apk (dev flavor).
8. Docs: PLAN.md (role-based module map), TASKS.md (all tasks below), DECISIONS.md (ADR-001 state mgmt, ADR-002 API client, ADR-003 offline strategy), API_CONTRACT.md.

Acceptance: `flutter run --flavor dev -t lib/main_dev.dart` works; CI green; no hard-coded URLs.
```

## Task 02 — Design System, Theming & Localization
```
TASK M02 — DESIGN SYSTEM & L10N

Deliver:
1. Material 3 theme from design tokens (match dashboard tokens from the web design system: colors, radius, spacing, typography), light/dark.
2. Bangla font bundled (Noto Sans Bengali / Hind Siliguri) with correct line-height; verify no clipped conjuncts at text scale 1.0–1.3.
3. l10n: ARB bn/en, locale switcher persisted, Bangla digits formatting helpers (NumberFormat 'bn'), BD currency (৳), Bangla date/month names, relative time.
4. Reusable widgets: AppScaffold, AppBar variants, PrimaryButton/SecondaryButton, AppTextField (with validation display), PhoneField (+8801 normalisation),
   StatusChip (icon+text), InfoCard, ListTile variants, EmptyState, ErrorRetry, SkeletonLoader, PagedListView (infinite scroll + pull-to-refresh),
   ConfirmDialog, BottomSheet helpers, AvatarWithFallback, ChildSwitcher (guardian), OfflineBanner.
5. A dev-only "Widgetbook-style" gallery screen (or Widgetbook if justified) showing all widgets/states in bn & en.
6. Golden tests for 5 key widgets in bn/en and text scale 1.3.
```

## Task 03 — Networking, Auth & Session
```
TASK M03 — AUTH (depends on Backend Task 03)

Deliver:
1. Dio client: base URL by flavor, interceptors (auth header, **single-flight refresh on 401**, retry/backoff for idempotent GET, X-App-Version, Accept-Language,
   error mapping to typed Failure from {code,message,details}, redacted logging).
2. Secure token storage; session model; app start → restore session → role resolution → role shell routing.
3. Screens: Splash, Language select (first run), Login (phone/username + password), OTP login (request → verify with resend timer & attempt-limit messaging),
   Forgot/reset password, Force-change-password, Profile (edit basics, change password, active sessions list/revoke), Logout / logout-all.
4. App lock: biometric/PIN lock via local_auth on cold start/resume (configurable timeout), fallback to re-login; settings toggle.
5. Force-update / maintenance handling: on 426/maintenance response show blocking screen with store link.
6. Router guards: auth, role, force-update. Deep-link-safe (post-login redirect).
Tests: refresh race (two parallel 401), OTP flow, guard redirects, token never logged, app-lock behaviour with fake local_auth.
```

## Task 04 — Local Storage, Offline Sync & Connectivity
```
TASK M04 — OFFLINE FOUNDATION

Use skill: flutter-offline-and-notifications.

Deliver:
1. Drift database setup, migrations strategy, encryption decision (sqlcipher or not — propose with trade-offs; wait for approval).
2. Generic stale-while-revalidate repository helper (cache → network → update), `fetched_at`, "last updated" UI.
3. Write queue for offline actions (idempotency keys, retry with backoff, failure surface, "pending sync" badges), background sync trigger on connectivity/resume.
4. Connectivity hint service (connectivity_plus) + OfflineBanner.
5. Cache hygiene: per-user DB scope, wipe on logout, size limits.
Tests: cache-then-network behaviour, queue replay idempotency, logout wipe, conflict handling policy (documented).
```

## Task 05 — Push Notifications & Deep Links
```
TASK M05 — NOTIFICATIONS (depends on Backend Task 16)

Deliver: Firebase setup per flavor (list file placements: google-services.json / GoogleService-Info.plist — do NOT commit secrets; document how to supply them),
FCM token registration/refresh/unregister with backend device-token endpoints, Android channels (attendance, fees, results, notices, emergency high-priority),
foreground/background/terminated handling, payload {type, entity_id} → go_router deep link, in-app notification inbox (list, read/unread, mark all read),
notification preferences screen, permission rationale (Android 13+ POST_NOTIFICATIONS, iOS prompt) just-in-time.
Tests: payload→route mapping table, token lifecycle, inbox state.
```

## Task 06 — Guardian: Home, Multi-Child & Profile
```
TASK M06 — GUARDIAN HOME (depends on Backend Tasks 06, 07)

Deliver: Guardian shell (bottom nav: Home, Attendance, Results/Academics, Fees, More), global selectedChild provider persisted, ChildSwitcher in app bar,
Home dashboard (today's attendance status, next class/exam, due fees banner, latest notices, homework due), Child profile (read-only basics, class/section/roll,
ID card QR view for gate/bus scanning), Authorized pickup people management (add/view, if backend supports), emergency info view/edit (if allowed).
Rules: data is always scoped to the selected child; switching child cancels in-flight requests and refreshes providers.
Tests: child switch isolates data, home widget states, golden for home (bn).
```

## Task 07 — Guardian: Attendance (Live & History)
```
TASK M07 — ATTENDANCE VIEW (depends on Backend Tasks 10, 11)

Deliver: Today status card (present/late/absent/leave with in/out times and method icon), month calendar view with color+icon legend, list view with filters,
attendance % with threshold warning, leave application for child (form → submit → status), push-driven refresh on attendance events (arrival/exit/absent),
offline cache with "last updated".
Tests: calendar mapping from API statuses incl. holiday/weekend, % display rounding, leave form validation, cache fallback.
```

## Task 08 — Guardian/Student: Academics (Routine, Homework, Materials)
```
TASK M08 — ACADEMICS (depends on Backend Tasks 04, 17)

Deliver: Weekly routine (day tabs, current period highlight), Homework list/detail (due soon/overdue/submitted; attachments download with progress & open-in), Student submission
flow (file/photo pick, size/type validation, resumable-friendly UX, retry queue offline), Study materials browser (subject filter, download & offline open), syllabus progress,
online class link join button.
Tests: routine day mapping & holidays, submission validation, offline queued submission.
```

## Task 09 — Guardian/Student: Results & Report Cards
```
TASK M09 — RESULTS (depends on Backend Task 13)

Deliver: Exam list (published only), result detail (subject-wise marks components, GPA/grade, position, pass/fail), progress report card PDF view/download/share (open with pdf viewer;
Bangla verified), exam routine & admit card view, performance trend chart with accessible table alternative, re-scrutiny request form (if enabled).
Tests: GPA/grade display from API values (do not recompute locally), unpublished exam hidden, PDF download error handling.
```

## Task 10 — Guardian: Fees & Online Payment
```
TASK M10 — FEES & PAYMENTS (depends on Backend Task 14)

Deliver: Fee summary (due, advance, next due date), invoice list/detail, payment history + receipt PDF, pay online (create payment session → open gateway in secure WebView/custom tab →
return deep link → poll/verify status from backend; NEVER mark paid from client redirect alone), failed/pending payment states, multi-child payment selection, due reminders via push.
Security: no card/mobile-wallet credentials handled by the app; WebView restrictions (https only, domain allow-list); no screenshots/logs of payment URLs.
Tests: payment state machine (initiated→pending→paid/failed/cancelled), deep-link return handling, idempotent retry, receipt download.
```

## Task 11 — Notices, Events & Chat
```
TASK M11 — COMMUNICATION (depends on Backend Tasks 16, 22)

Deliver: Notice board (pinned, unread badges, attachment viewer, search), Events calendar (agenda + month view), Chat with teachers (thread list, message list with pagination,
send text/attachment, delivery state, polling or WebSocket per backend ADR), Parent-teacher meeting booking, Complaint/suggestion submission, Emergency alert full-screen display.
Tests: unread counters, chat pagination & optimistic send rollback, emergency alert routing.
```

## Task 12 — Guardian/Student: Library, Transport & Misc
```
TASK M12 — LIBRARY & TRANSPORT (depends on Backend Tasks 18, 19, 21)

Deliver: Library (my issued books, due dates, fines, catalog search, reservations, e-books), Transport (child's route/stop/timings, live bus map via OpenStreetMap-based map package
— justify choice, no paid API keys committed; ETA display; boarding/drop notifications history), Health card view (emergency info, vaccination list if enabled), Hostel (if enabled): gate pass request & status.
Tests: map marker updates throttled, offline fallback to last known location with timestamp, feature-flag hiding.
```

## Task 13 — Teacher: Home, Routine & Class Attendance
```
TASK M13 — TEACHER ATTENDANCE (depends on Backend Tasks 08, 10)

Deliver: Teacher shell (Home, Classes, Marks, Messages, More), Today's classes (from routine incl. substitutions), take period/section attendance (fast list with tap-to-cycle statuses,
mark-all-present, search, remarks, submit with confirmation summary), see biometric-recorded statuses read-only and mark exceptions only per policy, edit window rules from backend,
offline write queue with pending-sync badges, attendance history per section, student quick-profile sheet.
Tests: tap-cycle logic, summary counts, offline queue replay, edit-window denial message.
```

## Task 14 — Teacher: Marks Entry
```
TASK M14 — MARKS ENTRY (depends on Backend Task 12)

Deliver: Assigned exam/subject/section picker, mark-entry list optimized for phones (numeric keypad, next-field focus, component columns creative/MCQ/practical, absent toggle),
validation vs max marks, auto-save drafts locally, submit with summary, locked-state read-only, entry progress indicator, offline queue.
Tests: boundary validation, draft restore after app kill, lock state, large class (60+ students) performance.
```

## Task 15 — Teacher: Homework, Notes & Messaging
```
TASK M15 — TEACHER TOOLS (depends on Backend Tasks 16, 17)

Deliver: Create homework (section/subject/due date/attachments/camera capture), review submissions & grade with feedback, upload class notes/materials, lesson plan/syllabus progress update,
message guardians (single/class broadcast with template), leave application & balance, own routine & workload.
Tests: upload validation & compression, grade form, broadcast confirmation shows recipient count.
```

## Task 16 — Staff Self Check-in (Geofence + Selfie)
```
TASK M16 — STAFF CHECK-IN (depends on Backend Task 10 MobileCheckin)

Use skill: flutter-offline-and-notifications.

Deliver: Check-in/out screen for teachers & staff: just-in-time location + camera permission rationale, geofence status (inside/outside with distance & accuracy), selfie capture
(front camera, compressed), mock-location detection flag, send device time + GPS accuracy + device id, server-validated result display, offline behaviour per policy (queue only if allowed),
today's punches timeline, monthly attendance summary, leave balance link.
Android/iOS config changes (permissions, foreground location rationale) must be listed in Phase 1.
Tests: geofence decision display (using server response), permission-denied flows, offline policy, selfie size limits.
```

## Task 17 — Management Dashboard & Approvals
```
TASK M17 — HEAD TEACHER / MANAGEMENT (depends on Backend Tasks 08, 11, 14, 24)

Deliver: Management shell with KPI home (today's student/staff attendance, absentees, fee collection/dues, device online status, pending approvals), approval inbox
(leave, waivers, attendance corrections, requisitions) with approve/reject + comment + undo window if backend supports, quick search student/staff, notices publish (limited),
emergency broadcast (two-step confirm), class-wise attendance drill-down.
Tests: approval actions & optimistic rollback, KPI card states, permission-based tab visibility.
```

## Task 18 — Driver & Security Roles (Light Apps)
```
TASK M18 — DRIVER & SECURITY (depends on Backend Tasks 19, 21)

Deliver: Driver mode (start/end trip, share live location with foreground service + battery-aware interval, student boarding/drop scan via QR/RFID(NFC) or manual list, offline queue),
Security mode (visitor check-in/out with photo, pickup verification via QR/OTP with guardian photo display, gate log).
Android foreground-service & background-location config/permissions must be itemised and justified; implement strict data-minimisation (stop sharing when trip ends).
Tests: trip lifecycle state machine, location throttling logic, pickup OTP verification flows.
```

## Task 19 — Settings, Privacy & Accessibility
```
TASK M19 — SETTINGS & POLISH

Deliver: Settings (language, theme, notification prefs, app lock, data usage / cache clear, about + version + licenses), privacy screen (what data is collected, consent history for
biometric enrollment if provided by backend), account deletion/export request (if backend supports), accessibility pass (semantics labels, tap targets ≥ 48dp, text scale 1.3,
screen-reader walkthrough of top flows, color-contrast), Bangla typography audit across all screens, empty/error copy review.
Report: audit findings + fixes.
```

## Task 20 — Testing, Performance & Release
```
TASK M20 — QUALITY & RELEASE

- Test completeness: coverage report, integration_test flows (login → guardian home → attendance → fee payment → result; teacher: attendance → marks), golden tests for core screens (bn/en).
- Performance: DevTools profiling on a low-end Android device profile, list virtualisation checks, image caching, startup time, APK/AAB size analysis (R8/ProGuard, split per ABI).
- Crash/error reporting (Firebase Crashlytics or Sentry) with PII scrubbing.
- Release engineering: Android signing config (keystore NOT in repo; document secure handling), versioning scheme, Play Store listing checklist (Data Safety form items:
  location, camera, personal info, child data), privacy policy link, staged rollout plan, in-app update/force-update verification, iOS TestFlight checklist.
- Final docs: MOBILE.md (architecture, how to add a feature), CHANGELOG, known limitations, API contract version compatibility matrix.
```
