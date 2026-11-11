# SKILLS.md — Antigravity Skills for the School Management System

> **How to use**
> Each `## SKILL:` section below is one skill. Antigravity-style skills live as
> `.agent/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
> Either keep this single file at repo root and tell the agent to read it, **or** split every section into its own folder
> (the frontmatter is already included). Verify the folder convention against your installed Antigravity version.
>
> **Django repo:** keep skills 1–12 and 13–15.  **Flutter repo:** keep skills 1–9 and 16–17.
> Skills 1–9 are universal. `AGENTS.md` defines *when* the mandatory workflow runs; these skills define *how* to do each step well.

## Skill Index

| # | Skill | Used in phase | Repo |
|---|-------|--------------|------|
| 1 | confirm-and-report | Phase 1 & 4 | all |
| 2 | task-planning | Phase 0–1 | all |
| 3 | requirements-analysis-bd | Phase 0 | all |
| 4 | system-design | Phase 1 | all |
| 5 | ui-ux-design | Phase 1–2 | all |
| 6 | development-standards | Phase 2 | all |
| 7 | debugging | Phase 2–3 | all |
| 8 | testing-strategy | Phase 1–3 | all |
| 9 | code-review-self-check | Phase 3 | all |
| 10 | django-backend | Phase 2 | Django |
| 11 | migration-safety | Phase 1–3 | Django |
| 12 | api-contract-openapi | Phase 1–3 | Django + clients |
| 13 | react-spa-dashboard | Phase 2 | Django (frontend/) |
| 14 | django-vite-integration | Phase 2 | Django |
| 15 | biometric-device-integration | Phase 1–2 | Django |
| 16 | flutter-app | Phase 2 | Flutter |
| 17 | flutter-offline-and-notifications | Phase 2 | Flutter |

---

## SKILL: confirm-and-report
```yaml
---
name: confirm-and-report
description: Use at the START of every task (to post an implementation plan and wait for approval) and at the END (to post a completion report). Mandatory for any change to code, config, schema, or dependencies.
---
```
### Procedure
1. **Before touching any file**, gather: task prompt, affected modules, existing code, current migrations/contract.
2. Produce the **Implementation Report** exactly in the format defined in `AGENTS.md §A2 Phase 1`.
3. Fill the **What will change** table by actually inspecting the repo (list real paths, not guesses).
4. For backend tasks, fill **Database/Migration impact** by:
   - listing every model/field added, altered, removed
   - stating nullability/defaults, indexes, constraints
   - stating whether data backfill is needed and how
   - stating reversibility and rollback
   - stating the effect on existing rows and locking risk
5. State **API/Contract impact** and which clients (dashboard, Flutter) need regeneration.
6. End with: `Reply "approved" to proceed, or tell me what to change.` Then **stop**.
7. After implementation, produce the **Completion Report** with real command output.

### Rules
- Never merge Phase 1 and Phase 2 in the same message.
- If you discover new scope mid-implementation → stop → post an **Amendment Report** (what changed vs. plan, why, impact) → wait.
- "Looks fine" or silence ≠ approval.

### Self-check before posting a plan
- [ ] Every acceptance criterion maps to a bullet
- [ ] Every file in the table has a reason
- [ ] Migration effect explained in plain language
- [ ] Risks include permissions and data privacy
- [ ] Test plan is concrete (file names/commands)

---

## SKILL: task-planning
```yaml
---
name: task-planning
description: Use when starting a task or when a task looks too large. Breaks work into small verifiable steps, orders them by dependency, and identifies risks before coding.
---
```
### Procedure
1. Restate the goal in one sentence and list explicit **non-goals**.
2. Identify dependencies on earlier tasks (check `docs/TASKS.md`). If a dependency is not DONE → flag BLOCKED.
3. Decompose into steps of ≤ ~1–2 hours each; each step must have a verifiable outcome.
4. Order: models/contract → services → API → tests → UI/integration → docs.
5. Identify the riskiest assumption and validate it first (spike if needed).
6. Estimate file count; if > 25 files, propose splitting into sub-tasks (`Task 14a`, `14b`).
7. Write the plan to `docs/PLAN.md` (module section) only after approval.

### Output template
```
Goal / Non-goals
Dependencies (DONE / BLOCKED)
Steps (numbered, each with "done when…")
Risks & mitigations
Open questions
```

---

## SKILL: requirements-analysis-bd
```yaml
---
name: requirements-analysis-bd
description: Use when a task touches Bangladeshi school domain rules — grading, exams, fees, admission, holidays, languages, mobile payments, SMS, MPO/EIIN, board exams. Prevents wrong local assumptions.
---
```
### Domain facts to apply (confirm with user if the school differs)
- **Grading (GPA 5.0, typical school scale):** 80–100 A+ (5.00), 70–79 A (4.00), 60–69 A- (3.50), 50–59 B (3.00), 40–49 C (2.00), 33–39 D (1.00), 0–32 F (0.00). **Make this configurable per institution**; never hard-code.
- Final GPA fails if any compulsory subject is F; **4th subject**: GPA above 2.00 is added to total points and divided by (subjects − 1) — implement as configurable rule, document in `DECISIONS.md`.
- Bangla/English have **1st & 2nd paper** → combined pass rule (configurable: separate pass or combined).
- Marks split: creative (CQ), MCQ, practical — each with its own pass mark.
- Sessions: January–December typical; exams: class test, half-yearly, annual, pre-test, test, model test.
- Groups from Class 9: Science / Commerce / Humanities(Arts).
- Weekend: Friday (and often Saturday) — configurable; holidays include Eid, Puja, Victory Day, Independence Day, Pohela Boishakh, etc. — editable calendar.
- Identifiers: **EIIN** (school), birth registration number (student), NID (guardian), roll number per class-section-session.
- Payments: bKash, Nagad, Rocket, SSLCommerz, aamarPay — always webhook/IPN-verified, idempotent.
- SMS: local gateways (masking vs non-masking); Bangla Unicode SMS = 70 chars/segment — compute cost correctly.
- Phone format: `01XXXXXXXXX` ↔ `+8801XXXXXXXXX` normalisation.
- Language: Bangla + English, Bangla numerals (০–৯) in print/UI where configured, Bangla PDF requires proper font embedding (Noto Sans Bengali / SolaimanLipi) and shaping (HarfBuzz-based).

### Rules
- If a rule is school-specific → make it a **configuration**, not code.
- Record every assumption in the Phase 1 report under "Assumptions".

---

## SKILL: system-design
```yaml
---
name: system-design
description: Use in Phase 1 whenever a task introduces a new module, model, integration, or cross-cutting behavior. Produces a small design before code.
---
```
### Procedure
1. Identify entities, relationships, and ownership (tenant/branch scoping).
2. Define invariants and state machines (e.g. Admission: draft → submitted → shortlisted → admitted/rejected).
3. Decide sync vs async work; identify idempotency keys.
4. Define permissions matrix: role × action.
5. Define events (e.g. `attendance.recorded`, `payment.confirmed`) and who consumes them.
6. Define failure modes (gateway timeout, device offline, duplicate punch) and handling.
7. Define data volume/indexing assumptions (e.g. attendance logs: millions of rows → partition/index plan).
8. Document: ER sketch (text), endpoint list, permissions matrix, state diagram.

### Output
Add a short ADR to `docs/DECISIONS.md` for any non-obvious choice.

---

## SKILL: ui-ux-design
```yaml
---
name: ui-ux-design
description: Use before building any screen (dashboard or Flutter). Produces a layout description, states, and interaction flow, and enforces consistent design language and accessibility.
---
```
### Procedure
1. For each screen list: purpose, user role, primary action, data shown, filters, empty/loading/error/offline states.
2. Describe layout (wireframe in text), components used from the design system, responsive behaviour.
3. Define flows: happy path + 2 failure paths.
4. Bangla-specific: allow ~30% longer text, don't truncate meaningful Bangla words mid-conjunct, test Bangla digits, use Noto Sans Bengali.
5. Accessibility: contrast AA, tap targets ≥ 48dp (mobile), focus order, semantic labels, no colour-only meaning (attendance Present/Absent/Late needs icon + text).
6. Consistent patterns: list+filter+detail drawer (dashboard); card list + pull-to-refresh (mobile).
7. Destructive actions always confirm; show impact ("This will remove 32 students from Class 6-A").

### Design tokens (agree once in Task 02, then reuse)
Primary, secondary, success, warning, danger, neutral scale, radius, spacing scale (4/8), typography scale, elevation. Light + dark mode.

---

## SKILL: development-standards
```yaml
---
name: development-standards
description: Use during implementation (Phase 2) in any repo. Enforces small steps, clean code, naming, error handling, and security basics.
---
```
### Checklist
- Small functions, single responsibility, meaningful names (domain terms: `fee_head`, `academic_session`, `punch`).
- No dead code, no commented-out blocks, no TODO without a task reference.
- Handle errors explicitly; never swallow exceptions; user-facing messages are translatable.
- No secrets, no PII in logs.
- Validate at boundaries (API input, device payloads, webhook payloads) — verify signatures for gateway/device webhooks.
- Prefer composition and explicit dependencies over globals.
- Commit message format: `feat(attendance): add shift-based late rule` (Conventional Commits).
- Update docs as you go.

---

## SKILL: debugging
```yaml
---
name: debugging
description: Use whenever a test fails, an error appears, or behaviour differs from expectation. Enforces systematic root-cause analysis instead of trial-and-error edits.
---
```
### Procedure (do not skip steps)
1. **Reproduce** — get the exact failing command/input; write a failing test if feasible.
2. **Read the error fully** — stack trace, SQL, HTTP status/body, Flutter exception + widget stack.
3. **Isolate** — bisect: which layer? (model → service → serializer → view → permission → URL → client). Narrow by logging/`pdb`/breakpoints.
4. **Hypothesise** — write down 1–3 hypotheses ranked by likelihood; test the cheapest first.
5. **Root cause** — fix the cause, not the symptom. State it in one sentence.
6. **Fix minimally**, keep the failing test as a regression test.
7. **Verify** — run the broader suite; check for side effects.
8. **Report** — in the Completion Report: symptom, root cause, fix, regression test.

### Stack-specific toolbox
- **Django:** `python manage.py shell_plus`, `django-debug-toolbar`/`silk` for queries, `connection.queries`, `EXPLAIN ANALYZE`, `pytest -x --pdb`, Celery: `celery -A config inspect active`, check task retries/dead letters.
- **DRF:** check `permission_classes`, `get_queryset` tenant filter, serializer `.errors`, spectacular warnings.
- **Migrations:** `showmigrations`, `sqlmigrate`, conflicting leaf nodes → `makemigrations --merge` only after review.
- **Vite/React:** browser console + Network tab, React DevTools, TanStack Query Devtools, check CORS/CSRF/proxy, check `manifest.json` entry for django-vite.
- **Flutter:** `flutter doctor -v`, DevTools (widget inspector, network, performance), `debugPrint` with redaction, check `ref.watch` vs `ref.read`, async gaps (`mounted` checks), Gradle/Pod errors → read the first error, not the last.
- **Biometric devices:** capture raw payload, check timezone/clock drift, duplicate punches, device SN mapping, network/ADMS push logs.

### Anti-patterns (forbidden)
- Random edits until it works; disabling tests; broad `try/except: pass`; adding `sleep()` to "fix" races; changing applied migrations.

---

## SKILL: testing-strategy
```yaml
---
name: testing-strategy
description: Use in Phase 1 to define the test plan and in Phase 2–3 to write and run tests. Ensures every task ships with unit, integration, permission, and edge-case tests.
---
```
### Test pyramid per task
- **Unit:** pure logic (services, grade calculation, late/half-day rules, fee fine calculation).
- **Integration:** API endpoints with DB (Django) / repository + fake datasource (Flutter) / hooks + MSW (React).
- **Permission matrix tests:** for each endpoint, test allowed role, denied role, unauthenticated, other-tenant user.
- **Contract tests:** schema validates (`spectacular --validate`); generated clients compile.
- **E2E (few, critical):** login → admit student → take attendance → collect fee → publish result.

### Must-have cases
- Boundary values (marks 32/33, grace minutes, 0/100).
- Idempotency (duplicate payment webhook, duplicate punch).
- Concurrency (two receipts generated simultaneously → no duplicate numbers).
- Time zones & Friday/holiday logic.
- Bangla text (names, search, PDF generation).
- Empty / huge data sets, pagination edges.

### Tooling
- Django: pytest, pytest-django, factory_boy, freezegun, `django_assert_num_queries`, responses/respx for gateways.
- React: Vitest, RTL, MSW, Playwright, axe for a11y.
- Flutter: flutter_test, mocktail, golden tests, integration_test.

### Rules
- Test names describe behaviour: `test_late_if_punch_after_grace_period`.
- No test depends on another test's state.
- Report real results; flaky tests are fixed or quarantined with a ticket, never ignored.

---

## SKILL: code-review-self-check
```yaml
---
name: code-review-self-check
description: Use at the end of Phase 2 before reporting. Self-review the diff against a checklist to catch bugs, leaks, and scope creep.
---
```
### Checklist
- [ ] Diff contains only approved files/changes
- [ ] No tenant/permission leak (every query scoped, every endpoint guarded)
- [ ] No N+1, no unbounded queries
- [ ] No secrets / PII in code, logs, fixtures
- [ ] Migrations safe, reversible, named clearly
- [ ] Error paths and empty states handled
- [ ] Strings externalised (bn/en)
- [ ] Types strict (no `any` / no `dynamic` without reason)
- [ ] Tests cover happy + failure + permission
- [ ] Docs, OpenAPI, CHANGELOG updated

---

## SKILL: django-backend
```yaml
---
name: django-backend
description: Use for any Django/DRF work: models, services, serializers, viewsets, permissions, Celery tasks, admin, settings. Enforces tenant scoping, service-layer architecture, and performance hygiene.
---
```
### Patterns
**Model base**
```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class TenantOwnedModel(BaseModel):
    institution = models.ForeignKey("institutions.Institution", on_delete=models.PROTECT, related_name="+")
    class Meta: abstract = True
```
**Viewset mixin:** `TenantScopedMixin.get_queryset()` filters by `request.user.institution`; `perform_create` injects institution.

**Service layer:** `services.admit_student(*, application, section, actor) -> Student` — keyword-only args, wrapped in `transaction.atomic`, raises domain exceptions mapped to API errors.

**Selectors:** read-only query functions returning optimized querysets.

### Rules
- `on_delete=PROTECT` for financial/academic history; soft delete for students/staff.
- Unique constraints scoped by tenant: `UniqueConstraint(fields=["institution","roll_no","section","session"])`.
- Use `Meta.indexes` for filter/sort fields; add `CheckConstraint` for invariants (e.g. `paid_amount <= payable_amount`).
- Use `TextChoices` for enums; store Bangla labels via translations, not DB values.
- Serializers: separate read/write serializers when shapes differ; never expose internal IDs/fields unintentionally.
- Use `django-filter`, `SearchFilter`, `OrderingFilter`; cap `page_size`.
- Celery: `acks_late`, `autoretry_for`, exponential backoff, idempotent tasks.
- Settings split; secrets via `django-environ`; `DEBUG=False` in prod; secure cookies/HSTS.
- Admin: register useful models with `list_display`, `search_fields`, `list_filter` (internal tooling only).
- Bangla PDF: WeasyPrint/ReportLab with Noto Sans Bengali embedded; test render.
- Document every endpoint with `@extend_schema`.

### Definition of done (backend task)
Models + migrations + services + serializers + viewsets + permissions + urls + admin + tasks + tests + OpenAPI + docs.

---

## SKILL: migration-safety
```yaml
---
name: migration-safety
description: Use whenever a model change creates or alters a migration. Ensures migrations are safe, reversible, explained to the user, and do not harm existing data.
---
```
### Procedure
1. Run `python manage.py makemigrations --dry-run -v 3` and read the output.
2. Classify each operation: **Safe** (add nullable column, add table, add index concurrently) / **Caution** (add NOT NULL w/ default, add unique, alter type) / **Dangerous** (drop column/table, rename, data loss).
3. For Caution/Dangerous: use multi-step pattern (add nullable → backfill in data migration → add constraint → remove old in a later release).
4. Check `sqlmigrate <app> <number>` and quote the key SQL in the report.
5. Confirm reversibility (`migrate <app> <previous>`); provide `RunPython` reverse functions.
6. Estimate impact on existing data: rows affected, lock duration, required downtime.
7. Postgres: use `AddIndexConcurrently` / `atomic = False` for big tables.
8. Never edit an applied migration; never squash without approval.
9. Run `makemigrations --check` in CI to catch missing migrations.
10. Test: migrate forward on a copy with sample data, then backward if reversible.

### Report block (copy into Phase 1)
```
Migration: apps/<app>/migrations/00NN_<name>.py
Operations: <list>
Classification: Safe | Caution | Dangerous
Existing data effect: <plain language>
Backfill: <none | description>
Locking/downtime: <none | estimate>
Reversible: yes/no — rollback: <command/steps>
```

---

## SKILL: api-contract-openapi
```yaml
---
name: api-contract-openapi
description: Use when creating/changing endpoints or when a client (dashboard/Flutter) consumes the API. Keeps the OpenAPI schema as the single source of truth and the clients in sync.
---
```
### Procedure
1. Annotate views with `@extend_schema` (request, responses, params, error examples).
2. Generate schema: `python manage.py spectacular --file schema/openapi.yml --validate`; commit it.
3. **Dashboard:** `npm run gen:api` → regenerate TypeScript types/client from `schema/openapi.yml`.
4. **Flutter repo:** copy `openapi.yml` (or fetch from a tagged release) into `api_contract/openapi.yml` and regenerate the Dart client / DTOs; record schema version in `api_contract/VERSION`.
5. Classify changes: **additive** (OK) / **breaking** (needs `/v2/` or compatibility period) — mention in the report.
6. Error format: `{ "code": "attendance.device_not_found", "message": "...", "details": {...} }`; keep code list in `docs/API_CONTRACT.md`.
7. Pagination: `{count, next, previous, results}` (page-number or cursor — decide once in Task 01).
8. Version header for app compatibility: `X-App-Version`; server may return `426` with a minimum version message for forced updates.

---

## SKILL: react-spa-dashboard
```yaml
---
name: react-spa-dashboard
description: Use for any React/TypeScript dashboard work inside the Django repo's frontend/ folder: pages, forms, tables, data fetching, routing, i18n, permissions, and tests.
---
```
### Patterns
- **Structure:** `features/<module>/{api,components,pages,hooks,schemas,types}`; shared `components/ui`, `lib`, `routes`.
- **Data:** TanStack Query hooks per resource: `useStudents(filters)`, `useCreateStudent()`; query keys factory; invalidate precisely on mutation; optimistic updates only where safe.
- **Forms:** React Hook Form + Zod; map server field errors back to fields; disable submit while pending; confirm unsaved changes.
- **Tables:** one reusable `DataTable` (server pagination/sort/filter, column visibility, CSV export hook, row actions, bulk select).
- **Permissions:** `usePermission("students.add")`, `<Can perm="...">`, route guards from `/me/permissions`.
- **Auth:** access token in memory, refresh via httpOnly cookie or secure refresh flow (decide in Task 03); automatic refresh on 401 once; logout everywhere on refresh failure.
- **i18n:** namespaces per feature; ICU plurals; `Intl.NumberFormat("bn-BD")` and `bn` date formatting with Bangla/English toggle.
- **Charts:** Recharts; every chart has a table/aria fallback.
- **Printing:** print-optimised routes for ID cards, admit cards, receipts, marksheets (CSS `@page`, Bangla fonts).
- **Error boundaries** per route; toast for transient, inline for validation.
- **Testing:** RTL for components, MSW for API, Playwright for critical flows.

### Rules
- Never trust UI hiding for security.
- No `any`; no unused deps; lazy-load heavy routes.
- Keep components < ~200 lines; extract hooks.

---

## SKILL: django-vite-integration
```yaml
---
name: django-vite-integration
description: Use when wiring, debugging, or deploying the React SPA served via django-vite (dev server, manifest, static files, SPA routing, CSRF/CORS).
---
```
### Setup facts
- `INSTALLED_APPS += ["django_vite"]`; `DJANGO_VITE = {"default": {"dev_mode": DEBUG, "manifest_path": BASE_DIR / "static/dashboard/.vite/manifest.json", ...}}` (verify the exact keys against the installed django-vite version).
- Template: `{% load django_vite %}` → `{% vite_hmr_client %}` + `{% vite_react_refresh %}` (dev) and `{% vite_asset 'src/main.tsx' %}`.
- `vite.config.ts`: `base` = static URL in prod, `build.manifest: true`, `build.outDir` into Django static dir, dev server `origin`/`strictPort`, proxy `/api` to Django in dev.
- Django serves SPA shell at `dashboard/` and `dashboard/<path:path>` (catch-all → same template) so React Router deep links work; `/api/`, `/admin/`, `/static/`, `/media/` must not be swallowed.
- Auth: prefer same-origin (cookie-based refresh + CSRF) since SPA is served by Django; if using Authorization header, keep access token in memory.
- Prod: `npm run build` → `collectstatic` → serve via WhiteNoise/Nginx with long cache for hashed files.

### Debug checklist
- Blank page → check `manifest.json` path & entry key; `dev_mode` flag; Vite server running & reachable (HMR WebSocket).
- 404 on deep link → catch-all URL missing or ordered after other routes.
- CSRF 403 → missing CSRF cookie/header or wrong `CSRF_TRUSTED_ORIGINS`.
- Stale assets → hashed filenames, clear browser/CDN cache.

---

## SKILL: biometric-device-integration
```yaml
---
name: biometric-device-integration
description: Use for any task touching biometric/RFID/QR/face devices, punch ingestion, device enrollment, or attendance-rule processing. Defines the vendor-agnostic adapter architecture and safe handling of biometric data.
---
```
### Architecture
```
Device (ZKTeco / Hikvision / Suprema / eSSL / generic HTTP / mobile app)
   │  (push: ADMS/HTTP webhook | pull: SDK/poll via connector)
   ▼
DeviceAdapter (per vendor)  →  normalise  →  RawPunch (immutable, stored as-received)
   ▼
PunchProcessor (Celery)  →  dedupe  →  identity resolve  →  AttendanceEvent
   ▼
AttendanceRuleEngine (per user-type policy)  →  DailyAttendance  →  notifications
```
### Rules
- **Adapter interface:** `authenticate()`, `fetch_logs(since)`, `parse_push(payload)`, `enroll_user(user, template|card|pin)`, `remove_user()`, `get_health()`; register adapters in a registry keyed by `device.vendor` + `device.protocol`.
- **Never store raw fingerprint/face images.** Store vendor template reference or device-side user ID; track **consent** (who, when, version).
- Immutable `RawPunch` log (payload hash, device SN, received_at, device_time); processing is replayable and idempotent (unique `(device, user_ref, punch_time)`).
- **Clock drift:** record device time and server time; flag drift > threshold; allow per-device timezone/offset.
- Duplicate-punch window configurable (e.g. 60s).
- **Offline devices:** buffer & backfill; late-arriving punches recompute the affected day only.
- **Identity mapping:** `DeviceUserMap(device, device_user_id → student/staff)`; unmapped punches go to a review queue.
- **Policies per user type & device group:** methods allowed/required, shifts, grace, late/half-day/early-leave, multi-punch/period-wise, holiday/leave/exam overrides.
- **Manual correction:** requires reason + approver, writes audit log, never mutates RawPunch.
- **Security:** device auth by shared secret/token + IP allow-list option; verify signatures; rate-limit device endpoints.
- **Simulators:** provide a `FakeDevice` adapter + management command to generate punches for tests/demo.
- Notifications on arrival/exit/absence are async, deduplicated, and respect quiet hours.

---

## SKILL: flutter-app
```yaml
---
name: flutter-app
description: Use for any Flutter work: features, screens, state management, navigation, API integration, theming, l10n, and platform configuration in the separate mobile repo.
---
```
### Patterns
- **Feature-first clean architecture** (see AGENTS.md §C2). Each feature: `data / domain / presentation`.
- **Riverpod:** `AsyncNotifier` for async state; `ref.watch` in build, `ref.read` in callbacks; `select` to limit rebuilds; family providers for per-id data; global `selectedChildProvider` for guardians.
- **Routing:** go_router with typed routes, redirect guard (auth + role + force-update + maintenance), nested shells per role (bottom nav).
- **Networking:** Dio with interceptors — auth header, single-flight refresh on 401, retry with backoff for idempotent GETs, `X-App-Version`, error mapping to `Failure`; redact logs.
- **Models:** `freezed` + `json_serializable`; DTO ↔ entity mappers; no DTOs in UI.
- **UI:** Material 3 theme from tokens; reusable widgets (`AppScaffold`, `StatusChip`, `EmptyState`, `ErrorRetry`, `PagedListView`); Bangla font bundled; test text scale 1.3.
- **Forms:** validate locally, map server errors to fields.
- **l10n:** ARB `app_bn.arb` / `app_en.arb`; locale persisted; Bangla digits via `intl` `NumberFormat` with locale `bn`.
- **Flavors:** dev/staging/prod with distinct app IDs, base URLs, Firebase configs.
- **Platform config:** list each manifest/Info.plist/Gradle change in the Phase 1 report. Android minSdk/targetSdk decisions go in `DECISIONS.md`.
- **Testing:** unit (use cases, mappers), provider tests with `ProviderContainer` overrides, widget tests, goldens for key screens, `integration_test` for login → home.

### Rules
- No business logic in widgets.
- Every async screen: loading / data / empty / error / offline states.
- Never block UI thread with heavy parsing (use `compute`).
- Always check `context.mounted` after awaits.
- Dispose controllers; avoid memory leaks.

---

## SKILL: flutter-offline-and-notifications
```yaml
---
name: flutter-offline-and-notifications
description: Use for caching/offline behavior, background sync, FCM push notifications, deep links, geofenced check-in, camera/location permissions, and app-lock biometrics in the Flutter app.
---
```
### Offline
- Drift tables per cached resource with `fetched_at`; **stale-while-revalidate**: render cache → refresh → update.
- Write queue for offline actions (teacher attendance, leave request) with idempotency keys, retry, and conflict handling; show "pending sync" badges.
- Use `connectivity_plus` as a hint only; real failures come from requests.

### Push (FCM)
- Register token after login, send to backend with device info; unregister on logout; refresh on token change.
- Channels (Android): attendance, fees, results, notices, emergency (high importance).
- Notification payload carries `type` + `entity_id` → deep link via go_router; handle foreground/background/terminated.
- Respect user notification preferences from backend.

### Staff check-in
- Permission rationale screens; geofence check (radius from institution config) + selfie; send device time + GPS accuracy; handle mock-location detection flag; offline queue allowed only if policy permits.

### App lock
- `local_auth` for biometric/PIN lock on resume after N minutes; tokens remain in secure storage; fallback to password/OTP.
