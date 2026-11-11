# BACKEND PROMPTS — Django + DRF (School Management System, Bangladesh)

## How to use
1. Put `AGENTS.md` (Part A + B) and `SKILLS.md` in the repo first.
2. Paste the **Master Preamble** once at the start of each Antigravity session.
3. Paste **one task** at a time. The agent must answer with an **Implementation Report** and wait for "approved".
4. After completion, it updates `docs/TASKS.md`. Move to the next task only when DONE.

Dependency order is the numbering order unless noted.

---

## MASTER PREAMBLE (paste at the start of every session)

```
You are the backend engineer for a multi-tenant School Management System for Bangladeshi schools
(Django 5 + DRF + PostgreSQL + Redis + Celery; React dashboard is served via django-vite from /frontend).

BEFORE ANYTHING ELSE:
1. Read AGENTS.md, SKILLS.md, docs/PLAN.md, docs/TASKS.md, docs/DECISIONS.md.
2. Follow the mandatory workflow in AGENTS.md §A2:
   Phase 1 = post an IMPLEMENTATION REPORT (what you will implement, what will change [file table],
   database/migration impact and its effect on existing data, API/contract impact, risks, test plan,
   assumptions) and STOP until I reply "approved".
   Phase 2 = implement only what was approved. Phase 3 = run lint/type/tests and show real output.
   Phase 4 = post a COMPLETION REPORT and update docs/TASKS.md, CHANGELOG.md, DECISIONS.md.
3. Load and name the skills you use (confirm-and-report, task-planning, requirements-analysis-bd,
   system-design, django-backend, migration-safety, api-contract-openapi, testing-strategy, debugging...).
4. Never change anything outside the task scope. Never run destructive commands without confirmation.
5. Every model is tenant-scoped (institution, optional branch). Every endpoint is permission-guarded and tested.
6. Bangla + English, Asia/Dhaka, BDT, GPA 5.0 are the defaults; school-specific rules must be configuration.

Acknowledge with "READY" and wait for the task.
```

## COMMON TASK FOOTER (appended mentally to every task; agent must satisfy)
```
Acceptance always includes: tests (unit + API + permission matrix incl. cross-tenant denial), OpenAPI annotations,
ruff/black/mypy clean, makemigrations --check clean, admin registration, docs updated, Completion Report.
```

---

# TASKS

## Task 01 — Project Setup & Foundations
```
TASK 01 — PROJECT SETUP

Goal: Create the Django project skeleton, tooling, infra, docs, and CI so all later modules plug in cleanly.

Scope:
1. Repo layout per AGENTS.md §B2: backend settings in config/settings/{base,dev,prod,test}.py, apps/ package,
   frontend/ folder placeholder (Vite is set up in the Frontend Task 01 — only reserve templates/static wiring here),
   docs/, schema/, .agent/skills/.
2. Dependencies (pin versions; list each in the report): Django 5.x, djangorestframework, drf-spectacular,
   djangorestframework-simplejwt, django-environ, django-filter, django-cors-headers, django-vite, celery, redis,
   django-celery-beat, django-celery-results, psycopg[binary], whitenoise, gunicorn, sentry-sdk (optional),
   dev: pytest, pytest-django, factory_boy, freezegun, ruff, black, mypy, django-stubs, pre-commit, django-debug-toolbar.
3. Settings: env-driven, TIME_ZONE=Asia/Dhaka, USE_TZ=True, LANGUAGE_CODE=en with bn enabled, LocaleMiddleware,
   locale/ folder, security headers for prod, logging (JSON in prod, PII redaction filter), DEFAULT_AUTO_FIELD.
4. DRF defaults: JWT auth, deny-by-default permission, pagination (page-number, max page size 100),
   filter backends, custom exception handler returning {code, message, details}, spectacular settings,
   renderer/parsers.
5. apps/core: BaseModel (UUID, timestamps), TenantOwnedModel (institution FK), SoftDeleteMixin, TenantScopedMixin
   (queryset/ perform_create), base permission classes, pagination class, exception classes, utils
   (BD phone normaliser, Bangla digit converter, Dhaka timezone helpers).
6. Infra: docker-compose (postgres, redis, backend, celery worker, celery beat), Dockerfile, .env.example, Makefile
   (run, test, lint, migrate, schema).
7. Celery wired with a health task; health endpoint /api/v1/health/ (db + redis checks).
8. django-vite settings stub + SPA shell URL placeholder (/dashboard/) — template only, no React yet.
9. CI (GitHub Actions or equivalent): lint, mypy, pytest, makemigrations --check, spectacular --validate.
10. Docs: PLAN.md (module map + phases), TASKS.md (all backend tasks with status), DECISIONS.md (ADR-001 stack,
    ADR-002 multi-tenancy approach, ADR-003 pagination/error envelope), API_CONTRACT.md.

Out of scope: any business models.

Acceptance:
- `docker compose up` runs backend, worker, beat; /api/v1/health/ returns ok.
- `pytest`, `ruff`, `mypy`, `makemigrations --check`, `spectacular --validate` all pass.
- Swagger UI available at /api/docs/ in dev only.
- Pre-commit hooks installed.
Migration impact: only Django built-ins/celery tables — state this explicitly.
```

## Task 02 — Institution, Branch, Shift, Academic Session (Tenant Core)
```
TASK 02 — INSTITUTION & TENANCY CORE

Goal: Model the school (tenant), branches/campuses, shifts, mediums/versions and academic sessions/terms.

Models (apps/institutions):
- Institution: name_bn, name_en, eiin, mpo_status, board (Dhaka/Rajshahi/…/Madrasa/Technical), type (primary/secondary/
  higher-secondary/madrasa/kindergarten), address (division/district/upazila), phone, email, website, logo, seal,
  signature images, timezone, currency, weekend_days (config), settings JSON (validated schema), is_active.
- Branch: institution FK, name, code, address, is_main.
- Shift: branch FK, name (Morning/Day/Evening), start/end time.
- Medium/Version: Bangla, English, English Version, Madrasa (choices or config table).
- AcademicSession: institution FK, name (e.g. 2026), start/end dates, is_current (only one current per institution),
  status (planned/active/closed).
- Term: session FK, name (Half-yearly, Annual…), start/end dates, order.
- HolidayCalendar & Holiday (date range, type: govt/institutional/emergency, applies_to branches) — also used by attendance.

Rules/Business:
- Only one current session per institution (DB constraint + service).
- Closing a session is a service operation with pre-checks (listed in report), irreversible → needs confirmation flag.
- Institution settings JSON validated by a pydantic/JSON-schema; keys documented (grading profile id, attendance defaults,
  SMS sender id, fee receipt prefix, Bangla digits on/off).
- Seed command `seed_demo_institution` creating a demo school (EIIN fake), branch, shifts, session 2026, BD holidays.

API: CRUD for branches, shifts, sessions, terms, holidays; GET/PATCH institution profile; POST sessions/{id}/activate|close.
Permissions: Super Admin, Head Teacher (read/write), others read-only.

Tests: one-current-session constraint, cross-tenant isolation, holiday overlap rules, close-session pre-checks.
Report must include the migration impact table for all new tables and constraints.
```

## Task 03 — Auth, Users, Roles, Permissions, OTP, Sessions
```
TASK 03 — AUTHENTICATION, USERS & RBAC

Goal: Secure identity system for admin dashboard + mobile app.

Models (apps/accounts):
- User (custom AbstractBaseUser): id UUID, institution FK (nullable for platform super admins), username/email/phone
  (phone normalised +8801XXXXXXXXX, unique per institution), full_name, user_type (admin/teacher/staff/student/guardian/
  driver/security), is_active, must_change_password, last_login, language preference (bn/en), avatar.
- Role (per institution; system roles seeded): Super Admin, Head Teacher, Assistant Head, Teacher, Accountant,
  Librarian, Clerk, Guardian, Student, Driver, Security.
- Permission matrix: use Django permissions + custom object/branch-scope permissions; Role ↔ permission set;
  UserRole (user, role, branch scope optional).
- OTPChallenge (hashed code, purpose, phone, expires, attempts, used_at), TrustedDevice/UserSession
  (device id, platform, app version, FCM token ref, last_seen, revoked_at), LoginAttempt, PasswordResetToken.
- Optional TOTP 2FA for admin roles.

Flows/API (/api/v1/auth/):
- login (username/phone + password) → access+refresh
- otp/request, otp/verify (for guardians/students; rate-limited; SMS sent via a pluggable SMSService interface —
  console backend now, real gateway in Task 16)
- refresh, logout (revoke session), logout-all
- password change/reset, force change on first login
- me (profile + role + permissions + branches), PATCH me
- sessions list/revoke; 2FA enable/verify/disable
- Admin: create/update/deactivate users, assign roles, reset passwords, bulk-create guardians/students accounts
  (hook only — actual people models arrive in later tasks).
- “Sign-up”: NO public signup for staff/guardians. Self-registration limited to the admission applicant portal (Task 05).
  Document this decision in DECISIONS.md.

Security: Argon2 hashing, lockout/backoff after N failures, OTP attempt limit, generic error messages, audit log hooks
(AuditLog model lands in Task 24 — create a thin interface now), JWT claims minimal (user id, institution, role ids),
refresh rotation + blacklist, CORS/CSRF notes for SPA served by Django.

Permissions framework deliverable: `HasModulePermission("students.view")` DRF permission class + decorator + test helpers
(`make_user(role="teacher")`, `api_client_as(user)`).

Tests: login/refresh/logout, OTP brute-force limits, lockout, role permission checks, cross-tenant denial,
session revoke, password policy.
Migration report: AUTH_USER_MODEL swap must be done in this task’s FIRST migration — explain the effect (fresh DB only).
```

## Task 04 — Academic Structure (Class, Section, Group, Subject, Routine)
```
TASK 04 — ACADEMIC STRUCTURE

Models (apps/academics):
- ClassLevel (Nursery…Class 12; order, medium, has_groups from class 9), Group (Science/Commerce/Humanities),
  Section (class × shift × session; capacity; class teacher FK→Staff later (use nullable UUID FK placeholder via
  string reference 'staff.Staff' only after Task 08; until then store teacher_user FK to accounts.User)),
- Subject (code, name_bn, name_en, type: compulsory/optional/4th subject/co-curricular, has_papers (1st/2nd),
  marks components config (creative/MCQ/practical default max & pass marks)),
- ClassSubject (class × group × session; full marks, pass rule, credit/weight, is_optional_elective),
- Period (name, start/end, shift), RoutineSlot (section, weekday, period, subject, teacher_user, room),
- SubstituteAssignment (slot date, original teacher, substitute, reason).
- Room (name, capacity, type).

Rules: no teacher double-booking in same period/day (service check + exclusion constraint where feasible),
section capacity checks, copy-structure-from-previous-session service (preview first, then confirm),
routine conflict detection endpoint, weekend/holiday awareness using Task 02 calendar.

API: CRUD + bulk create sections; GET routine by section/teacher/room; POST routine validate; POST copy-session (dry_run=true default).
Permissions: Head Teacher/Admin write; Teacher read own routine.
Tests: conflict detection, capacity, copy dry-run vs apply, cross-tenant.
```

## Task 05 — Admission (Online Application, Test, Merit, Lottery)
```
TASK 05 — ADMISSION

Models (apps/admissions):
- AdmissionCircular (session, class, seats, fee, form open/close dates, instructions, eligibility, status),
- Application (applicant info: name bn/en, DOB, gender, birth reg no, guardian name/phone/NID, address, previous school,
  documents, photo, application_no (unique, human-friendly), status: draft→submitted→paid→shortlisted→test-scheduled→
  admitted/rejected/waitlisted/withdrawn),
- ApplicationDocument, ApplicationPayment (links to fees gateway in Task 14 via interface),
- AdmissionTest (date, venue, subjects, marks), AdmissionTestResult, MeritList (rule: test marks/GPA/lottery/quota),
  LotteryDraw (seeded RNG, audit-logged, reproducible), QuotaRule (siblings, staff child, freedom-fighter, disability),
  WaitingList entry.

Flows: public application endpoints (rate-limited + captcha hook) → payment → admit card → test → merit → offer →
confirmation → convert to Student (service stub; real Student arrives in Task 06 — wire after 06 via signal/service,
documented as a follow-up inside Task 06).

Rules: seat limits per class & quota, duplicate application detection (birth reg no + DOB), state machine enforced in
service, merit tie-breakers configurable, lottery must be verifiable (store seed + order).
API: public (create/submit/status by application_no+phone OTP), admin (list/filter/export, bulk status change,
generate merit, run lottery, send results).
Tests: state machine, seat limit, quota, lottery reproducibility, duplicate detection, public rate limiting.
```

## Task 06 — Student Management
```
TASK 06 — STUDENTS

Models (apps/students):
- Student (student_id (institution-configurable pattern), name_bn/en, DOB, gender, blood group, religion, birth reg no,
  photo, address, status: active/transferred/dropped/graduated/alumni, admission_date, special categories (orphan,
  freedom-fighter quota, disability, stipend)),
- StudentEnrollment (student, session, class, section, group, shift, roll_no, status) — unique roll per section/session,
- StudentDocument, PreviousSchool, Sibling link (via guardian family in Task 07),
- StudentIDCard (card_no, qr_code, rfid_uid, printed_at),
- Promotion (batch record) / PromotionItem, TransferCertificate, Testimonial/CharacterCertificate (number sequence),
  DropoutRecord, AlumniProfile.

Services: admit_from_application (completes Task 05 conversion), auto roll assignment (by name/ID/merit — configurable),
bulk promotion (preview → confirm → apply, with pass/fail source from results later; allow manual), transfer/TC issue,
re-admission, bulk import from Excel template (validate → dry-run → commit; error report file).
Certificates: PDF generation service (Bangla fonts) — create the PDF renderer utility in apps/core/pdf with a test that
renders Bangla text correctly (document font choice in DECISIONS.md).

API: CRUD, search (name/ID/roll/phone), filters, bulk actions, ID card data endpoint, import/export endpoints.
Permissions: field-level — teachers can’t see NID/finance fields; guardians only their own children (enforced later by
Guardian link, create the permission class now).
Tests: roll uniqueness, promotion dry-run/apply atomicity, import validation, cross-tenant, Bangla search.
Migration report: include indexes for search (trigram on names if pg_trgm — state extension requirement).
```

## Task 07 — Guardians & Family
```
TASK 07 — GUARDIANS & FAMILY

Models (apps/guardians): Guardian (user FK nullable, name, relation, phone, alt phone, NID, occupation, address),
StudentGuardian (student, guardian, relation, is_primary, can_pickup, receives_sms, financial_responsible),
Family (family_id grouping siblings), AuthorizedPickup (person, photo, phone, relation, OTP-verifiable).

Services: create guardian + user account + send credentials/OTP (via SMSService), link siblings automatically by
phone/NID with admin confirmation, merge duplicate guardians, one guardian → many children.
API: guardian CRUD, link/unlink, my-children endpoint (for guardian role), sibling suggestions.
Permissions: guardian can only see linked children (central permission class `IsGuardianOfStudent`).
Tests: multi-child access, unlinking revokes access immediately, duplicate merge, phone normalisation.
```

## Task 08 — Staff & HR (Teachers, Leave, Assignments)
```
TASK 08 — STAFF & HR

Models (apps/staff): Staff (employee_id, user FK, designation, department, type: teacher/admin/support/driver/security,
joining date, MPO status, index number, qualifications, documents, status), StaffEducation, StaffDocument,
Designation, Department, LeaveType (casual/sick/maternity/earned; yearly quota; carry-forward), LeaveBalance,
LeaveRequest (status flow, approver chain), TeacherAssignment (teacher × subject × section × session),
WorkloadSummary (view/selector), PerformanceReview, TrainingRecord, StaffIDCard.

Rules: leave overlap prevention, balance deduction on approval, approval workflow configurable (HOD → Head),
approved leave feeds attendance rule engine (Task 10) via events.
API: staff CRUD, leave apply/approve/reject/cancel, balances, teacher assignments, workload report.
Wire-up: replace temporary teacher_user references from Task 04 with Staff FK via a safe data migration (explain effect).
Tests: leave overlap, balance math, approval permissions, assignment conflicts.
```

## Task 09 — Biometric & Attendance Device Management
```
TASK 09 — DEVICE MANAGEMENT (vendor-agnostic)

Use skill: biometric-device-integration (mandatory).

Models (apps/devices):
- Device (name, type: fingerprint/face/iris/palm/rfid/nfc/qr/pin/mobile, vendor, model, serial_no, protocol:
  push_adms/pull_sdk/http_api/mqtt/mobile_app, ip/port, auth secret (encrypted), location (gate/classroom/staff room),
  branch, timezone offset, status, last_seen, firmware, user_capacity, storage stats, is_active),
- DeviceGroup (e.g., “Main Gate → students”, “Staff Room → teachers”) + DeviceGroupMember,
- DeviceUserMap (device, device_user_id → student/staff/driver), BiometricEnrollment (user ref, method, device, consent
  record id, enrolled_at — NO raw templates stored unless explicitly approved; template storage is encrypted + opt-in),
- BiometricConsent (subject, guardian consent for minors, version, timestamp, withdrawn_at),
- DeviceCommand (enroll/delete/sync/reboot; queued → sent → acked/failed), DeviceHealthLog, RawPunch (immutable).

Adapters (apps/devices/adapters/): base interface + registry; implement `ZKTecoPushAdapter` (ADMS-style HTTP push, document
exact endpoints), `GenericHTTPAdapter` (JSON webhook with HMAC), `FakeDeviceAdapter` (simulator), and stubs with clear
TODOs for Hikvision/Suprema/eSSL. For each adapter, document what is verified vs assumed — do NOT claim vendor
compatibility you cannot test.

Endpoints: device CRUD, test-connection, sync-users (celery), enroll request (creates DeviceCommand), health,
device push ingestion endpoints (token auth + rate limit + signature), unmapped-user review queue.
Celery: periodic health check, command dispatcher, poll-based log pull.
Management command: `simulate_punches --students 50 --days 3`.
Tests: ingestion idempotency, signature failure, unmapped queue, command lifecycle, consent required before enrollment.
```

## Task 10 — Attendance Engine & Rules (Configurable)
```
TASK 10 — ATTENDANCE ENGINE

Use skills: biometric-device-integration, system-design, testing-strategy.

Models (apps/attendance):
- AttendancePolicy (per user_type & optionally per branch/class/shift): allowed_methods (any-of/required-all),
  shift/period-based in/out times, grace minutes, late threshold, half-day threshold, early-leave threshold,
  min work duration (staff), multi-punch mode (single/entry-exit/period-wise), duplicate window, weekend/holiday handling,
  exam-day override, effective_from/to (versioned; no retroactive silent change),
- PolicyAssignment, AttendanceEvent (normalised from RawPunch/mobile/manual: subject, direction in/out, method, device, ts, source),
- DailyAttendance (subject, date, status: present/late/absent/half-day/leave/holiday/weekend, first_in, last_out, minutes_late,
  computed_by_policy_version, is_overridden),
- PeriodAttendance (section, period, subject, teacher, student, status) for teacher-taken attendance,
- AttendanceCorrection (reason, requested_by, approver, before/after, status) + audit,
- MobileCheckin (GPS lat/lng/accuracy, geofence result, selfie ref, device id).

Engine: PunchProcessor → dedupe → identity resolve → AttendanceEvent → RuleEngine (pure functions, heavily unit-tested)
→ DailyAttendance upsert → emit events (late/absent/arrival/exit) → notifications (consumed in Task 16/11).
End-of-day Celery job marks absentees (respecting leave/holiday). Recompute endpoint for a date range (idempotent).
Manual attendance entry (bulk by section) as fallback with source=manual.

API: policies CRUD + simulate (dry-run a policy on sample punches), live feed (SSE/WebSocket optional — propose, don’t assume),
daily/period endpoints, corrections workflow, mobile check-in (geofence validation server-side), staff attendance summary.
Tests: table-driven rule tests (on-time/late/half-day/early-leave/multi-punch/holiday/leave), duplicate punches, timezone,
policy versioning, recompute idempotency, 100k-punch performance sanity test.
```

## Task 11 — Attendance Reports, Notifications Hooks & Eligibility
```
TASK 11 — ATTENDANCE REPORTING

Deliver selectors + endpoints + export for: daily/monthly/period-wise reports, late list, absentee list, student/section/class
percentage, staff attendance sheets (payroll-ready), device-wise punch logs, exception reports (missing out-punch, clock drift,
unmapped punches). Attendance % thresholds → exam-eligibility flags & warning letters (configurable).
Define notification events (arrival, exit, absent, late, low-attendance) and a NotificationTemplate hook used in Task 16.
Exports: Excel/CSV/PDF (Bangla-capable). Heavy exports async with download link.
Performance: materialised aggregates or summary tables updated by Celery; indexes; pagination.
Tests: aggregate correctness vs raw data, percentage rounding rules, permissions (teacher: own sections only), export content.
```

## Task 12 — Examination & Grading Setup
```
TASK 12 — EXAMINATION

Models (apps/exams): GradingProfile (grade scale, GPA points, fail rules; default BD GPA-5), ExamType (class test, half-yearly,
annual, pre-test, test, model), Exam (session, term, class, weightage, status draft→scheduled→marking→locked→published),
ExamSubject (exam × class subject, date, time, room, full marks, component split creative/MCQ/practical, pass marks per
component, combined-paper rule), ExamRoutine, SeatPlan, AdmitCard, MarkEntry (student, exam subject, component marks, absent flag,
entered_by, locked), MarkEntryLog, GraceMarkRule, ReScrutinyRequest.

Rules: marks validation vs max; lock/unlock with approval; teacher can enter only assigned subject/section; absent vs zero;
exam eligibility check from attendance (Task 11) + dues policy hook (Task 14) – configurable, never hard-coded.
API: exam CRUD, schedule/seat plan generation, admit card PDF, bulk mark entry (grid + Excel import), lock/unlock, entry progress tracker.
Tests: validation boundaries, permissions, lock behaviour, seat plan generation rules.
```

## Task 13 — Results, Tabulation, Report Cards
```
TASK 13 — RESULTS

Models: ResultSummary (student × exam: total, GPA, grade, position class/section/group, pass/fail, failed subjects),
SubjectResult, TabulationSheet (generated file ref + version), ReportCard (template, file), ResultPublication (visibility, publish time).

Engine (pure, table-driven tests): per-subject marks → component pass checks → combined-paper rule → grade point → 4th subject
rule → GPA → merit position with tie-breakers (configurable) → cumulative across terms with weightage (CGPA/annual).
All rules driven by GradingProfile; document each rule and example calculations in docs/GRADING.md.
Flows: calculate (Celery) → review → publish → notify → re-scrutiny → recalc with audit trail.
Outputs: tabulation sheet (Excel+PDF), marksheet, progress report card (Bangla/English), result search by roll/ID (public, rate-limited),
weak-student/ trend analytics selectors, promotion eligibility feed for Task 06 bulk promotion.
Tests: golden test cases with hand-verified GPA examples (include 4th subject, failed compulsory, absent), recalculation idempotency,
Bangla PDF render test.
```

## Task 14 — Fees & Online Payments
```
TASK 14 — FEES & PAYMENTS

Models (apps/fees): FeeHead, FeeStructure (class/group/session), FeeStructureItem, StudentFeeAssignment, Invoice (monthly/term/one-time;
number sequence per institution), InvoiceLine, Waiver/Discount (sibling, merit, poor fund, quota; approval), FineRule (late fine), Payment
(method: cash/bank/bkash/nagad/rocket/card/gateway, status, gateway txn id, idempotency key, received_by, branch), PaymentAllocation,
MoneyReceipt (immutable number), AdvanceBalance, Refund, DueReminderLog.

Gateways: abstraction `PaymentGateway` with `create_session`, `verify`, `handle_webhook`; implement SSLCommerz/aamarPay adapters in
sandbox mode + bKash/Nagad stubs; webhook/IPN signature verification; never trust client redirect alone; reconcile job for pending payments.

Rules: Decimal money, atomic allocation, no negative/overpay without advance, receipt numbers gap-free per institution (locking strategy),
fine calculation job (idempotent), waiver approval, refund workflow, partial/installment payments.
API: structures, assignments (bulk generate invoices — preview → confirm), collect payment (counter), guardian pay-online endpoints,
due list, daily collection report, defaulters, receipts PDF (Bangla), reminder trigger.
Tests: allocation math, concurrency (receipt numbers), webhook replay, partial payments, waiver caps, permission matrix (Accountant vs Teacher).
Migration report: highlight PROTECT FKs and CheckConstraints on money fields.
```

## Task 15 — Accounting & Payroll
```
TASK 15 — ACCOUNTING & PAYROLL

Accounting: AccountHead (tree), Voucher (receipt/payment/journal), VoucherLine, CashBook/BankAccount, BankReconciliation, Budget, Fund.
Auto-post journal entries from Fee payments/refunds (signal-free: explicit service calls). Reports: daily collection, income/expense,
trial balance, P&L, balance sheet (Bangla/English).
Payroll: SalaryStructure (basic, allowances, MPO component, deductions), StaffSalaryAssignment, PayrollRun (month; draft→reviewed→approved→paid),
Payslip (earnings/deductions lines), Bonus (Eid), Advance/Loan recovery; attendance-linked deductions from Task 10/11; leave integration.
Rules: period locking (no edits after close), double-entry balance check, payslip PDF (Bangla), bank advice export.
Tests: voucher balance, period lock, payroll calculations (golden cases), permissions.
```

## Task 16 — Communication (SMS, Push, Notices, Chat)
```
TASK 16 — COMMUNICATION

Models (apps/communications): Notice (audience targeting: all/class/section/role/individual; schedule; attachments; pinned; expiry),
NotificationTemplate (bn/en, variables), NotificationEvent → NotificationDelivery (channel sms/push/email/in-app/whatsapp-optional;
status; provider id; cost), SMSGatewayConfig (provider, sender/masking, credentials encrypted), SMSBalanceLog, DeviceToken (FCM),
NotificationPreference, ChatThread/ChatMessage (teacher↔guardian, moderation flags, attachments), EmergencyAlert, MeetingSlot (PTM),
Complaint/Suggestion.

Services: SMSService with provider adapters (implement one local gateway behind interface + console backend), Bangla Unicode segment/cost
calculator, FCM push sender (firebase-admin), template rendering, quiet hours, dedupe, retries with backoff, delivery receipts webhooks.
Wire events: attendance (Task 11), result published (13), fee due/payment (14), notice published, OTP (03 SMSService now real).
API: notices CRUD/publish, inbox for each role (read/unread), device token register/unregister, preferences, chat (REST + polling; propose
WebSocket via Channels as optional ADR), emergency broadcast, delivery logs, SMS balance.
Tests: audience resolution, dedupe, retry, template rendering Bangla, permission (Teacher→own sections only), provider failure handling.
```

## Task 17 — Homework, Assignments, Study Materials, Online Exam (lite)
```
TASK 17 — LEARNING MODULE

Models (apps/homework): Homework (section/subject/teacher/due date/attachments), Submission (files/text, status, marks, feedback),
LessonPlan, SyllabusTopic + progress, StudyMaterial (files/links by class/subject), Quiz/Question/Option/Attempt (optional lite),
OnlineClassLink (Zoom/Meet link scheduling).
Rules: file type/size limits + AV scan hook, due-date logic, late submission policy, visibility by section/subject.
API for teacher/student/guardian roles; notifications on new homework/due soon.
Storage: S3-compatible via django-storages (configurable; local FS for dev) — document signed URL download policy.
Tests: permissions, upload validation, late submission, notification triggers.
```

## Task 18 — Library
```
TASK 18 — LIBRARY

Models: Book (ISBN, title, authors, category, publisher, edition, language), BookCopy (accession no, barcode, rfid, shelf, status),
LibraryMember (student/staff link, member card), Issue (issue/due/return dates, renewals), Reservation, LibraryFine, EBook/DigitalResource.
Rules: max books per member type, loan days config, renewal limits, fine per day, block issue on dues/fines (configurable), reservation queue.
API: catalog search, issue/return/renew (barcode/RFID scan friendly), overdue list, popular books, member history; Excel import for catalog.
Tests: loan limits, fine calculation, reservation queue, concurrency on last copy.
```

## Task 19 — Transport
```
TASK 19 — TRANSPORT

Models: Vehicle (reg no, capacity, fitness/insurance/tax expiry), Driver (staff link, license no/expiry), Route, RouteStop (order, pickup/drop times),
TransportAssignment (student/staff × route × stop × session), TransportFee link (FeeHead), VehicleMaintenance, FuelLog, TripLog,
BoardingEvent (student, trip, stop, boarded/dropped, ts, method QR/RFID/manual), LiveLocation (vehicle ping: lat/lng/speed/ts) — GPS ingestion endpoint (device token auth).
Rules: capacity checks, expiry alerts (Celery daily), guardian alerts on boarding/drop events, location retention policy (e.g. 30 days).
API: CRUD, assignment, trip start/end (driver app role), live location latest + history, boarding scan endpoint.
Tests: capacity, expiry alerts, boarding idempotency, driver permissions, retention job.
```

## Task 20 — Hostel (Optional Module)
```
TASK 20 — HOSTEL

Make this module feature-flagged per institution (settings flag + permission gate).
Models: Hostel, Room, Bed, HostelAllocation, HostelFee link, HostelAttendance (night roll call/biometric via attendance engine event type), GatePass/LeaveRequest,
MealPlan/MealAttendance, VisitorLog (hostel).
Rules: bed uniqueness, allocation history, gate pass approval with guardian OTP confirmation, curfew alerts.
Tests: allocation conflicts, gate-pass workflow, feature-flag off → endpoints 404/403.
```

## Task 21 — Health, Safety, Visitors & Pickup
```
TASK 21 — HEALTH & SAFETY

Models: HealthRecord (allergies, conditions, vaccinations, emergency contact; treated as SENSITIVE: encrypted fields or restricted access + audit on view),
SickRoomVisit (symptoms, medication, outcome, guardian notified), VisitorLog (visitor, purpose, host, badge, in/out), GateLog,
PickupRequest/PickupVerification (authorized person list, OTP/QR verification, photo), IncidentReport.
Rules: access limited to Head/Nurse/Admin; every read of health data audited; guardian can view/edit only their child’s emergency info.
Tests: sensitive-field access, pickup OTP verification, visitor lifecycle.
```

## Task 22 — Co-curricular, Events & Gallery
```
TASK 22 — CO-CURRICULAR & EVENTS

Models: Club (scouts/Rover/BNCC/debate/cultural), ClubMembership, Event (sports day, annual function, national days) with calendar,
Competition/Result/Position, Achievement & Certificate (template + PDF), Gallery/Album/Media (image/video, consent flag for student photos, visibility).
Rules: media upload limits/thumbnails (Celery), privacy flags, certificate numbering.
API + permissions + tests including privacy filters (hidden photos not visible to guardians).
```

## Task 23 — Inventory & Assets
```
TASK 23 — INVENTORY

Models: Asset (tag, category, location, purchase info, condition, depreciation optional), StockItem, StockMovement, Supplier, PurchaseOrder/Item,
GoodsReceipt, Requisition (approval), MaintenanceRequest, Sales (uniform/books/stationery — optional, ties to fees/accounting).
Rules: stock never negative, movement ledger immutable, approval flow, low-stock alerts.
Tests: stock math, approvals, permissions.
```

## Task 24 — Dashboard KPIs, Report Builder, Audit Logs, Import/Export
```
TASK 24 — REPORTS, DASHBOARD & AUDIT

Audit: AuditLog (actor, action, object, before/after diff, IP, device, ts) + `audit.record()` service; integrate with sensitive models (health, fees, results,
attendance corrections, role changes, biometric consent). Immutable (no update/delete API).
Dashboard: KPI endpoints (today’s attendance by user type, absentees, fee collected/dues, device online/offline, upcoming exams, pending approvals) with caching
(Redis, short TTL) and role-based variants (Head, Accountant, Teacher).
Report builder: saved report definitions (whitelisted datasets, filters, columns) – NO raw SQL from users; export PDF/Excel/CSV async with download links and expiry.
Bulk import/export framework (template download, validate, dry-run, commit, error file) reused by students/staff/books/marks.
Tests: audit immutability, KPI correctness, report whitelist enforcement, import dry-run.
```

## Task 25 — Integrations, Webhooks, Government Exports, Multi-tenant Admin
```
TASK 25 — INTEGRATIONS & PLATFORM

- Public API keys & scopes for third parties (hashed keys, rate limits), outbound webhooks (events, HMAC signature, retries, delivery log),
- Government/board data exports (EMIS/BANBEIS-style, SSC/HSC registration & form fill-up datasets) — build as configurable export templates; mark exact government
  field specs as “to be provided by the school” and DO NOT invent official formats,
- Platform super-admin (separate permissions): tenant onboarding, plan/feature flags, usage stats,
- Optional: Zoom/Meet scheduling integration interface.
Tests: signature verification, retry/backoff, scope enforcement, tenant onboarding service.
```

## Task 26 — Security Hardening, Backup, Compliance
```
TASK 26 — SECURITY & OPERATIONS

- 2FA enforcement for admin roles, IP/device restrictions option, password/lockout policies review, security headers, rate-limit review on all public endpoints.
- Encryption: field-level encryption for sensitive fields (NID, health, gateway secrets) with key rotation procedure; verify TLS settings.
- Backups: scheduled DB + media backups, restore runbook, tested restore (document RPO/RTO), retention policy, data export/delete (privacy) procedures for students/guardians.
- Observability: structured logs, Sentry, metrics/health, Celery monitoring (Flower or alternative), slow-query logging.
- Run a security review checklist (OWASP ASVS-lite) and report findings; fix or ticket each.
Deliver: docs/SECURITY.md, docs/RUNBOOK.md, docs/BACKUP_RESTORE.md.
```

## Task 27 — Performance, E2E, CI/CD & Deployment
```
TASK 27 — RELEASE READINESS

- Load/perf tests on attendance ingestion, dashboards, fee collection (Locust/k6); fix N+1 and missing indexes; EXPLAIN ANALYZE findings in report.
- E2E API scenario tests: admit → enrol → attendance → fee → exam → result → notification.
- CI/CD pipeline (build image, run tests, push, migrate with approval gate), production compose/Kubernetes manifests (propose, user chooses),
  Nginx/gunicorn settings, static/media strategy, env matrix (dev/staging/prod), zero-downtime migration checklist, rollback plan.
- Seed/demo data command, API changelog, version tagging, final docs pass.
```
