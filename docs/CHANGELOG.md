# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **Task 06**: Student Management (Profile, Enrollment, Documents, ID Cards, Promotion, Bulk Import, Bangla PDF) (`apps/students`, `apps/core/pdf`).
  - Core Models:
    - `Student`: Multi-tenant master student record with configurable `student_id`, bilingual names (`name_bn`, `name_en`), DOB, gender, blood group, religion, 17-digit birth registration number, photo, present/permanent address, status (`active`, `transferred`, `dropped`, `graduated`, `alumni`, `suspended`), admission date, and special categories (orphan, freedom-fighter quota, disability, stipend).
    - `StudentEnrollment`: Session-specific enrollment linking `Student` to `AcademicSession`, `ClassLevel`, `Section`, `Group`, `Shift`, with unique roll number (`roll_no`) per section/session and enrollment status tracking.
    - `StudentDocument`: Archival document storage with verification workflow.
    - `PreviousSchool`: Previous academic history, board, TC number, and GPA.
    - `StudentIDCard`: Digital/physical ID cards with unique card numbers, JSON QR verification payloads, and RFID/NFC UID mapping.
    - `PromotionBatch` & `PromotionItem`: Academic session progression engine supporting preview, automatic/manual review, atomic commit, and reversible rollback.
    - `TransferCertificate` & `Testimonial`: Official Bangladeshi school clearance and passing certificate records with gap-free sequence numbering (`TC-YYYY-XXXXX`, `TST-YYYY-XXXXX`).
    - `DropoutRecord` & `AlumniProfile`: Dedicated tracking for student attrition and graduated student network.
  - Business Rules & Services:
    - `intake.py`: `admit_from_application` completing the Task 05 bridge to transform admitted applicants into active students and enrollments.
    - `roll_assigner.py`: Configurable automated roll numbering (alphabetical by English/Bangla name, student ID order) with temporary roll offsets preventing unique constraint collisions.
    - `promotion.py`: End-to-end bulk promotion pipeline (`preview_promotion` → `apply_promotion` → `rollback_promotion`) with roll collision prevention and atomic rollback.
    - `transfer.py`: TC issuance workflow transitioning student status to `transferred`, closing active enrollment, and generating official PDF.
    - `bulk_import.py`: Excel spreadsheet parser (`openpyxl`) supporting dry-run validation with row-by-row error reporting and atomic multi-row creation.
    - `id_card_service.py`: Automated student ID card issue and renewal, active card replacement, and badge PDF rendering.
  - Bangla PDF Engine (`apps/core/pdf/`):
    - ReportLab integration registering TrueType Unicode Bengali fonts (`Kalpurush` bundled in `apps/core/fonts/Kalpurush.ttf` with system fallbacks).
    - Templates for Transfer Certificate (ছাড়পত্র), Testimonial (প্রশংসাপত্র), and Student ID Card (আইডি কার্ড).
  - REST API: Endpoints under `/api/v1/students/` for student CRUD, search by Bangla/English name, student ID, and birth reg no, Excel bulk import (`/bulk-import/`), Excel export (`/export/`), student admission intake (`/admit-from-application/`), section roll re-sequencing (`/enrollments/auto-assign-rolls/`), promotion preview/apply/rollback (`/promotions/`), TC issue and PDF download (`/transfer-certificates/`), and Testimonial issue and PDF download (`/testimonials/`).
  - Security: Field-level masking hiding sensitive birth registration numbers and emergency contact phones for unauthorized viewers, role-based permissions (`HasModulePermission("students.view")`, `HasModulePermission("students.manage")`).
  - Architectural Decision Record: ADR-008 (Student Identity Generation, Roll Assignment & Bangla PDF Engine).
- **Task 05**: Admission (Online Application, Test, Merit, Lottery) (`apps/admissions`).
  - Models: `AdmissionCircular` (intake session, class, quota, fee, start/end dates, eligibility criteria), `QuotaRule` (General, Freedom Fighter, Catchment, Special Needs/Disability, Staff Child, Sibling), `Application` (application number `ADM-YYYY-XXXXX`, applicant details, 17-digit birth registration number, guardian contact, status machine), `ApplicationDocument` (photo, birth certificate, marksheet, transfer certificate), `ApplicationPayment` (fee payment transaction, bKash/Nagad/manual, verification), `AdmissionTest` (venue, date, max marks, pass marks), `AdmissionTestResult` (marks obtained, rank, pass/fail), `LotteryDraw` (seeded deterministic PRNG, reproducible candidate order), `MeritList` (merit list generation, approval), `MeritListEntry` (merit rank, waiting rank, quota allocation).
  - Business Rules & Services:
    - `application_workflow.py`: Strict state transition graph (`draft` -> `submitted` -> `fee_paid` -> `under_review` -> `accepted` / `rejected` -> `test_assigned` -> `test_attended` -> `selected` / `waiting` -> `admitted` / `cancelled`), duplicate application prevention using `(circular, birth_reg_no, dob)`, 17-digit BD birth reg number validation, applicant age and minimum GPA validation.
    - `lottery.py`: Auditable deterministic lottery engine utilizing SHA256/Python `Random(seed)` with persistent seed and drawn applicant list for government-mandated lottery admissions.
    - `merit_calculator.py`: Merit scoring and ranking engine with configurable quota reservation caps, handling merit list vs waiting list partitioning.
    - `student_converter.py`: Intake transition service converting `admitted` applications into initial student profile records for Task 06.
  - REST API:
    - Public endpoints under `/api/v1/admissions/public/`: active circulars, multi-step application submission, application status tracking, and downloadable admit card generation.
    - Administrative endpoints under `/api/v1/admissions/`: circulars CRUD, applications management with status transition actions (`/transition/`), document verification (`/verify-document/`), payments review, admission tests and marks entry, lottery draws (`/conduct/`), merit list generation (`/generate/`, `/approve/`), and student intake conversion (`/convert-to-student/`).
  - Security & Integrity: Role-based permissions (`HasModulePermission` for admissions module), public endpoints with throttling and sanitization, audit trail of lottery seed and status transitions.
  - Architectural Decision Record: ADR-007 (Public Prospective Applicant Admission & Deterministic Lottery Engine).
- **Task 04**: Academic Structure (`apps/academics`).
  - Models: `ClassLevel` (medium, order, has_groups), `Group` (Science, Commerce, Humanities), `Section` (class × shift × session with teacher placeholder), `Subject` (code, Bangla/English name, marks components config), `ClassSubject` (session offering, pass rule, credit weight, optional elective flag), `Room` (branch, capacity, type), `Period` (shift, start/end time, order, break flag), `RoutineSlot` (section × weekday × period timetable slot), `SubstituteAssignment` (dated substitution with validation).
  - Database Constraints: `unique_class_code_per_institution`, `unique_class_order_per_medium_institution`, `unique_group_code_per_institution`, `unique_period_order_per_shift`, `unique_room_per_branch`, `unique_section_per_class_shift_session`, `unique_subject_code_per_institution`, `unique_slot_per_section_weekday_period`, partial unique index on room per period, partial unique index on teacher per period, `unique_subject_per_class_group_session`, `unique_substitution_per_slot_date`.
  - Service layer: Timetable conflict detector (`validate_routine_slot_conflicts`, `validate_routine_slots_batch` checking teacher double-booking, room clashes, section clashes, break periods, and calendar weekend warnings), session structure copier (`copy_academic_structure_from_previous_session` supporting `dry_run` preview, section copy, class subject offerings copy, and routine copy).
  - Selectors: Routine queries for sections, teachers, rooms, and a 2D section timetable matrix builder (`build_section_timetable_matrix`).
  - REST API: Endpoints under `/api/v1/academics/` for classes, groups, sections (with `/bulk-create/` and `/{id}/timetable/`), subjects, class subjects, rooms, periods, routine (with `/validate/`), substitute assignments, and `/copy-session/`.
- **Task 03**: Authentication, Users & RBAC (`apps/accounts`).
  - Models: Custom `User` (UUID, institution FK, unique normalized BD phone per tenant, Argon2 hashing, TOTP 2FA fields), `Role`, `UserRole` (with branch scoping), `OTPChallenge`, `UserSession` (trusted device tracking), `LoginAttempt` (brute-force tracking), `PasswordResetToken`.
  - Service layer: Password login, OTP request/verify with pluggable `ConsoleSMSService`, token generation (`issue_tokens_for_user` with minimal claims), session revocation (`revoke_user_session`, `revoke_all_user_sessions`), account lockout protection (5 failed attempts within 15 minutes), and TOTP 2FA generation and verification.
  - Permissions Framework: `HasModulePermission` DRF class factory, `@require_module_permission` decorator, test helpers (`make_user`, `api_client_as`).
  - REST API: Endpoints under `/api/v1/auth/` for `login/`, `otp/request/`, `otp/verify/`, `refresh/`, `logout/`, `logout-all/`, `password/change/`, `me/`, `sessions/`, `users/`, `roles/`.
  - Architecture Decision Record: ADR-005 (No Public Self-Registration for staff/guardians; restricted to prospective applicants in Task 05).
- **Task 02**: Institution & Tenancy Core module (`apps/institutions`).
  - Models: `Institution` (tenant root), `Branch`, `Shift`, `AcademicSession`, `Term`, `Holiday`.
  - Database Constraints: `unique_current_session_per_institution` partial unique index, `unique_branch_code_per_institution`, `unique_shift_name_per_branch`, `unique_term_name_per_session`, `unique_term_order_per_session`.
  - Service layer: `activate_academic_session` (atomic session switching), `close_academic_session` (irreversible close with pre-checks and confirm flag), `validate_institution_settings`.
  - Management command: `seed_demo_institution` seeding "Dhaka Model High School & College" (EIIN 134567), main campus, morning/day shifts, 2026 session, 3 terms, and official BD public holidays.
  - REST API: CRUD for branches, shifts, sessions, terms, holidays; profile GET/PATCH; session activate and close action endpoints.
  - Permissions: `IsInstitutionAdminOrReadOnly` enforcing tenant isolation and write access restrictions.
- **Task 01**: Initial project skeleton, foundation settings, Docker infrastructure, and base documentation.
- Abstract models: `BaseModel` (UUID, timestamps), `TenantOwnedModel` (institution scoping), `SoftDeleteMixin`.
- DRF mixins: `TenantScopedMixin` for automatic tenant queryset filtering and ownership injection.
- Standardized pagination (`StandardResultsSetPagination`) and uniform error envelope handler.
- Bangladeshi utility modules: Phone number normalizer, Bengali digit converter, Asia/Dhaka timezone helpers.
- Celery configuration with Redis broker, `django_celery_results`, `django_celery_beat`, and health check task.
- Health check API endpoint at `/api/v1/health/` testing database and Redis connectivity.
- Swagger UI (`/api/docs/`) and OpenAPI 3.0 schema generation via `drf-spectacular`.
- django-vite template shell placeholder at `/dashboard/`.
- Multi-stage `Dockerfile`, `docker-compose.yml`, `Makefile`, `.pre-commit-config.yaml`, and GitHub Actions CI workflow.
