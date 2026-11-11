# AGENTS.md — School Management System (Bangladesh)

> **How to use this file**
> - **Django repo** (backend + React dashboard served by django-vite): keep **Part A + Part B**, delete Part C.
> - **Flutter repo** (separate project, NOT inside the Django repo): keep **Part A + Part C**, delete Part B.
> - Place at repo root as `AGENTS.md`. Skills live in `.agent/skills/` (see `SKILLS.md`).

---

# PART A — UNIVERSAL RULES (all repos)

## A1. Mission
Build a production-grade, multi-tenant School Management System for Bangladeshi schools: configurable multi-device biometric attendance, admission, exams (GPA 5.0), fees (bKash/Nagad/SSLCommerz), HR/payroll, communication (SMS/push), library, transport, hostel — with an Admin Dashboard (React SPA) and a Mobile App (Flutter).

## A2. The Mandatory Workflow (never skip)

Every task goes through these phases **in order**. Do not write or modify any file before Phase 2 is approved.

### Phase 0 — Understand
- Read the task prompt fully. Read `docs/PLAN.md`, `docs/TASKS.md`, `docs/DECISIONS.md` and the affected code.
- Load the relevant skills from `.agent/skills/` and state which ones you loaded.
- If anything is ambiguous, ask. Do not guess business rules (fees, grading, attendance policy).

### Phase 1 — Plan & Report (required output, before coding)
Post this report and **STOP for confirmation**:

```
## IMPLEMENTATION REPORT — <Task ID & name>

### 1. What I will implement
(bullet list of features/behaviours, mapped to the task's acceptance criteria)

### 2. What will change
| Type | Path | Action (create/modify/delete) | Why |
|------|------|-------------------------------|-----|

### 3. Database / Migration impact   (backend only; "None" if none)
- New tables / columns / indexes / constraints
- Altered or dropped columns, data backfill needed?
- Migration file names, reversible? (yes/no)
- Estimated effect on existing data, locking risk, rollback plan

### 4. API / Contract impact
- New/changed endpoints, request/response shape, breaking change? (yes/no)
- OpenAPI schema regeneration required? Which clients are affected (dashboard / Flutter)?

### 5. Effects & Risks
- Behavioural effects on existing features
- Security, performance, permission implications
- Things that could break and how I will detect it

### 6. Test plan
(what tests I will add and which commands I will run)

### 7. Assumptions & open questions
```
Wait for the user to reply **"approved"** (or give edits). Silence is not approval.

### Phase 2 — Implement
- Implement only what was approved. If scope grows, **stop and re-report** (new Phase 1).
- Small, reviewable steps. One logical change at a time.
- Never run destructive commands (`migrate` on non-dev DB, `flush`, `rm -rf`, `git push --force`, dropping tables) without explicit confirmation.

### Phase 3 — Verify
- Run: lint, type-check, tests, and the task's manual checks. Paste real output; never claim "tests pass" without running them.
- Re-read your own diff and fix issues before reporting.

### Phase 4 — Final Report (required)
```
## COMPLETION REPORT — <Task ID>
- Implemented: …
- Files changed: (list)
- Migrations applied: (names + what they did)  [backend]
- Tests: added N, results (paste summary)
- Commands to verify manually: …
- Deviations from approved plan: … (or "none")
- Known limitations / follow-ups: …
- Docs updated: PLAN/TASKS/DECISIONS/CHANGELOG
```
Then update `docs/TASKS.md` (status), append to `docs/CHANGELOG.md`, and record any design decision in `docs/DECISIONS.md`.

## A3. Hard Rules
1. **No silent changes.** Every file touched must appear in the Phase 1 table or a re-report.
2. **No invented requirements.** Missing info → ask, or list under "Assumptions" and wait.
3. **No secrets in code/logs.** Use environment variables. `.env.example` only.
4. **Privacy of children and biometrics.** Never log or store raw biometric images. Store templates/IDs only, with consent tracking. Mask guardian phone numbers/NID in logs.
5. **Bangladesh context by default.** Bangla + English UI, Asia/Dhaka timezone, BDT currency (৳), Bangla digits where displayed, Friday/Saturday weekend configurable, phone format `+8801XXXXXXXXX`, BD grading (GPA 5.0).
6. **Contract-first.** Backend OpenAPI schema is the single source of truth. Dashboard and Flutter clients are generated/validated against it. Never hand-guess response shapes.
7. **Small PR-sized diffs.** If a task needs >25 files, propose a split.
8. **Reversibility.** Every migration/feature must have a rollback path noted in the report.
9. **Don't delete or rewrite working code** outside the task scope. Refactors need their own task.
10. **Dependencies.** Adding a package requires listing it (name, version, reason, license, size/maintenance status) in Phase 1.

## A4. Definition of Done
- Acceptance criteria met and demonstrated.
- Tests written and passing; coverage not reduced.
- Lint/type/format clean.
- Permissions enforced and tested (including negative cases).
- Bangla/English strings externalised (no hard-coded text).
- Docs/OpenAPI/CHANGELOG updated.
- Completion Report delivered.

## A5. Project Docs (create in Task 01 of every repo)
```
docs/PLAN.md       # architecture, module map, phases
docs/TASKS.md      # task list with status: TODO / IN-PROGRESS / DONE / BLOCKED
docs/DECISIONS.md  # ADR-style decisions (date, context, decision, consequences)
docs/CHANGELOG.md
docs/API_CONTRACT.md  # how repos sync the OpenAPI schema
```

## A6. Communication Style
- Be concise and structured; tables for change lists.
- Report problems immediately; do not hide failing tests.
- When unsure between two designs, present both with trade-offs and a recommendation.

---

# PART B — DJANGO BACKEND + REACT DASHBOARD (django-vite)

## B1. Stack
- Python 3.12, Django 5.x, Django REST Framework, drf-spectacular (OpenAPI)
- PostgreSQL 16, Redis, Celery (+ beat), django-celery-results
- Auth: SimpleJWT (access/refresh), phone-OTP, optional TOTP 2FA for admins
- django-vite for serving the React SPA; Vite + React 18 + TypeScript
- Frontend: React Router, TanStack Query, Zustand (UI state only), React Hook Form + Zod, Tailwind + shadcn/ui, i18next, openapi-typescript client
- Testing: pytest, pytest-django, factory_boy, Vitest, React Testing Library, Playwright
- Quality: ruff, black, mypy (django-stubs), pre-commit, ESLint, Prettier, tsc strict

## B2. Backend Layout
```
backend/
  config/            # settings/{base,dev,prod,test}.py, urls, celery, asgi/wsgi
  apps/
    core/            # base models, mixins, permissions, pagination, exceptions, utils
    accounts/        # users, roles, auth, otp, sessions
    institutions/    # school, branch, shift, academic session
    academics/       # class, section, group, subject, routine, calendar
    admissions/ students/ guardians/ staff/
    devices/ attendance/
    exams/ results/
    fees/ accounting/ payroll/
    communications/ homework/ library/ transport/ hostel/ health/ events/ inventory/
    reports/ integrations/ audit/
frontend/            # Vite React app (dashboard) inside the Django repo
docs/ .agent/skills/ AGENTS.md
```
Each app: `models.py` (or `models/`), `services.py` (business logic), `selectors.py` (read queries), `serializers.py`, `views.py` (thin), `permissions.py`, `urls.py`, `tasks.py`, `admin.py`, `tests/`.

## B3. Backend Rules
1. **Fat services, thin views.** Business logic in `services.py`; views only validate/serialize/call services.
2. **Multi-tenancy:** every tenant-owned model inherits `TenantOwnedModel` (FK `institution`, optional `branch`). All querysets filtered by tenant via a base manager/viewset mixin. A cross-tenant leak is a release blocker.
3. **Base model:** UUID PK (`id`), `created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted` (soft delete) where appropriate.
4. **Migrations:** one logical change per migration; never edit applied migrations; data migrations separate from schema migrations; large-table changes use safe patterns (add nullable → backfill → constrain). Always show `sqlmigrate` output in the report for risky changes.
5. **Money:** `DecimalField(max_digits=12, decimal_places=2)`; never floats. Wrap payments in `transaction.atomic` with idempotency keys.
6. **Query hygiene:** `select_related`/`prefetch_related`, pagination everywhere, DB indexes for filter/sort fields, no N+1 (test with `assertNumQueries`).
7. **Permissions:** deny-by-default. Every endpoint has an explicit permission class and tests for allowed/denied roles.
8. **Async work** (SMS, push, report generation, device sync) via Celery with retries + idempotency; never inside request cycle.
9. **Time:** store UTC, display `Asia/Dhaka`. Attendance uses device timestamp + server receipt timestamp.
10. **API:** `/api/v1/`, consistent error envelope `{code, message, details}`, filtering/search/ordering, drf-spectacular annotations on every view. Breaking changes need `/v2/` or a deprecation note.
11. **Audit:** state-changing actions on sensitive models write `AuditLog`.
12. **django-vite:** dev uses Vite dev server; prod serves hashed assets from `manifest.json`. Django serves the SPA shell at `/dashboard/` with a catch-all so React Router works; API stays under `/api/`.

## B4. Frontend (Dashboard) Rules
1. Feature-folder structure: `src/features/<module>/{api,components,pages,hooks,schemas,types}`; shared UI in `src/components/ui`.
2. Server state in TanStack Query only; forms in React Hook Form + Zod; no business rules duplicated from backend beyond UX validation.
3. API types generated from OpenAPI: `npm run gen:api`. Never hand-write response types.
4. Every route is permission-guarded (route guard + UI element guard). Hiding a button is not security; backend is authoritative.
5. Every list page: server-side pagination/filter/sort, loading/empty/error states, URL-synced filters.
6. i18n: all text via `t()`; Bangla and English files in parity (CI check). Bangla font: Noto Sans Bengali / Hind Siliguri.
7. Accessibility: keyboard navigable, labels, contrast AA, focus management in dialogs.
8. Responsive for 1280px+ primarily, usable at tablet width.
9. No `any`; `strict` TypeScript.
10. Performance: route-level code splitting, virtualised long tables, debounced search.

## B5. Commands the agent must use
```
# backend
ruff check . && black --check . && mypy apps
pytest -q --maxfail=1
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.yml --validate
# frontend
npm run lint && npm run typecheck && npm run test && npm run build
npm run gen:api
```

---

# PART C — FLUTTER MOBILE APP (separate repo)

## C1. Stack
- Flutter (stable), Dart 3, null-safety, `flutter_lints` + `very_good_analysis`
- State: Riverpod (with code generation); Navigation: go_router
- Networking: Dio + interceptors (auth refresh, retry, logging with redaction); models via `freezed` + `json_serializable`
- API client generated from the backend OpenAPI schema (`openapi-generator` dart-dio or hand-written repositories validated against schema)
- Local: Drift (SQLite) for offline cache; `flutter_secure_storage` for tokens
- Firebase Cloud Messaging + `flutter_local_notifications`
- `local_auth` (app lock), `geolocator` + `camera`/`image_picker` (staff check-in)
- i18n: `flutter_localizations` + ARB (`bn`, `en`)
- Testing: `flutter_test`, `mocktail`, `integration_test`, golden tests

## C2. Architecture (feature-first clean architecture)
```
lib/
  main_dev.dart main_staging.dart main_prod.dart   # flavors
  app/            # app widget, router, theme, di
  core/           # network, storage, errors, utils, l10n, widgets
  features/<module>/
    data/         # datasources (remote/local), DTOs, repository impl
    domain/       # entities, repository interfaces, use cases
    presentation/ # providers, screens, widgets
test/ integration_test/
```

## C3. Flutter Rules
1. UI never calls Dio directly; UI → provider → use case → repository → datasource.
2. All server errors mapped to typed `Failure`s; every screen handles loading/empty/error/offline.
3. Tokens only in secure storage; never log tokens, phone numbers, or child data.
4. Offline-first for key screens (routine, homework, notices, attendance history, results): show cached data immediately, refresh in background, show "last updated".
5. Multi-role app: role resolved after login; role-specific shells (Guardian, Student, Teacher, Staff/Management) with role-guarded routes.
6. Multi-child guardians: a global "selected child" provider drives every guardian screen.
7. Bangla-first design: test long Bangla strings, Bangla digits, font scaling to 130%.
8. Use `const` widgets, avoid rebuild storms (`select`), paginate lists, cache images.
9. Platform permissions requested just-in-time with rationale screens.
10. Android + iOS config changes (manifest, Info.plist, Gradle, signing) must be explicitly listed in Phase 1.
11. API base URL and flavors from config — never hard-coded.

## C4. Commands the agent must use
```
dart format --set-exit-if-changed .
flutter analyze
dart run build_runner build --delete-conflicting-outputs
flutter test --coverage
flutter test integration_test   # when a device/emulator is available
```
