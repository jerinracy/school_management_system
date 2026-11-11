# Architecture Decision Records (ADRs)

## ADR-001: Technology Stack Selection
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: We need a resilient, scalable, maintainable foundation for a multi-tenant Bangladeshi School Management System supporting web, mobile, and hardware biometric integrations.
- **Decision**:
  - Backend: Django 5.x with Django REST Framework (DRF) in Python 3.12.
  - Relational Database: PostgreSQL 16 for ACID compliance, relational integrity, and robust JSON querying.
  - Task Queue & Cache: Celery 5.x backed by Redis 7 for async processing (SMS, report generation, device log syncing).
  - Admin Web Dashboard: Vite + React 18 SPA served via `django-vite` within the Django application.
  - Mobile Application: Flutter (Dart 3) in a dedicated repository communicating via OpenAPI contract.
- **Consequences**:
  - Pros: High developer velocity, battle-tested ORM and ecosystem, rich ecosystem for background jobs, shared deployment for backend and dashboard.
  - Cons: Requires strict architectural discipline (service layer) to prevent fat views and tight coupling.

---

## ADR-002: Multi-Tenancy Architecture (Shared Database with Discriminator Column)
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: The system will host hundreds to thousands of schools (institutions) ranging from small kindergartens to large colleges. We need operational simplicity, fast onboarding, and strict isolation.
- **Decision**:
  - Implement a Shared Database with Row-Level Discrimination via `institution_id`.
  - All tenant-owned models must inherit `TenantOwnedModel` (which enforces `institution` foreign key).
  - All API viewsets must inherit `TenantScopedMixin` to guarantee querysets filter by `request.user.institution`.
  - Service functions must explicitly require tenant context.
- **Consequences**:
  - Pros: Cost-effective resource utilization, painless database migrations across all tenants, easy global aggregation when authorized.
  - Cons: High risk of cross-tenant data leaks if isolation is not enforced at the base layer; mitigated with automated multi-tenant permission tests and strict ORM mixins.

---

## ADR-003: API Response Envelope & Pagination Standards
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Frontend clients (React Dashboard, Flutter Mobile) need consistent, predictable response envelopes for errors and paginated list views.
- **Decision**:
  - Success responses return the raw payload or paginated structure.
  - Paginated responses follow standard format:
    ```json
    {
      "count": 100,
      "next": "...",
      "previous": "...",
      "results": [...]
    }
    ```
  - Default page size: 20; Maximum page size: 100.
  - Error responses follow a uniform error envelope:
    ```json
    {
      "code": "ERROR_CODE",
      "message": "Human readable summary",
      "details": { ... }
    }
    ```
- **Consequences**:
  - Simplifies client error handling, form field validation mapping, and infinite scrolling.

---

## ADR-004: Virtual Environment & Dependency Management Standard
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Need consistent local development and CI/CD runtime environments.
- **Decision**:
  - Standard virtual environment directory is `venv` at the repository root.
  - Production dependencies are pinned in `requirements.txt`.
  - Development, testing, and linting tools are pinned in `requirements-dev.txt`.
- **Consequences**:
  - Reproducible builds across developer machines, Docker containers, and CI pipelines.

---

## ADR-005: User Self-Registration Policy (No Public Sign-Up)
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Educational institutions require verified, authorized identities for guardians, teachers, and staff to prevent unauthorized access to student records and school operations.
- **Decision**:
  - No public self-registration/sign-up endpoints are permitted for staff, teachers, or guardians.
  - Staff and teachers are created by institution administrators via Admin/HR onboarding.
  - Guardian and student credentials are generated automatically upon successful enrollment.
  - The ONLY public registration allowed in the system is for prospective student applicants in the Online Admission Portal (Task 05).
- **Consequences**:
  - Eliminates unverified tenant spam accounts and guarantees that all users in the system belong to verified real-world relationships.

---

## ADR-006: Timetable Conflict Prevention and Structure Replication
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Scheduling school timetables is prone to teacher double-booking, room clashes, and administrative overhead during annual academic session transitions.
- **Decision**:
  - Double-booking prevention uses defense-in-depth:
    1. Database-level partial unique indexes on `(teacher_user, weekday, period)` and `(room, weekday, period)` preventing race conditions.
    2. Service-layer validator (`validate_routine_slot_conflicts`) returning structured conflict reports with human-readable error messages and weekend/holiday warnings.
    3. Dedicated validation endpoint (`/api/v1/academics/routine/validate/`) allowing frontend drag-and-drop timetable builders to validate slot placements before submission.
  - Academic structure rollover across sessions provides dry-run simulation (`copy_academic_structure_from_previous_session` with `dry_run=True` default), idempotently copying sections and subject offerings while skipping duplicates.
- **Consequences**:
  - Guarantees schedule integrity while providing a seamless UX for school administrators.

---

## ADR-007: Public Prospective Admission Portal & Auditable Deterministic Lottery Engine
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Bangladeshi schools require both merit-based test admissions (for high schools/colleges) and government-mandated digital lottery draws (primary/secondary grades 1-9). Furthermore, external parents must apply online without possessing a prior system user account, requiring robust duplicate prevention and status tracking.
- **Decision**:
  - Public applications allow unauthenticated submissions under `/api/v1/admissions/public/apply/` scoped to an active `AdmissionCircular`.
  - Duplicate submissions are strictly prevented by a unique database constraint and service-layer check on `(circular, birth_reg_no, dob)`.
  - Application numbers use standard format `ADM-{YYYY}-{5-digit sequence}` with atomic counter sequencing per institution.
  - Lottery draws are made deterministic and auditable by accepting/storing an integer `seed` and serializing the resulting draw order into `drawn_order` JSON on `LotteryDraw`. Re-running the draw with the same seed produces the identical sequence for regulatory audit.
  - Admission status transitions follow an explicit finite state machine enforced by `transition_application_status`.
  - Once an application reaches `admitted` status, `convert_admitted_application_to_student` transitions the applicant to Task 06 intake without data loss.
- **Consequences**:
  - Eliminates duplicate entries and fraudulent registrations while fulfilling Ministry of Education regulatory requirements for transparent lottery draws and merit list rankings.

---

## ADR-008: Student Identity Generation, Roll Assignment & Bangla PDF Engine
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Bangladeshi schools require unique student identification numbers, session-and-section scoped sequential roll numbers (1..N), atomic class promotion with rollback capabilities, and official printable certificates in Bengali (ছাড়পত্র and প্রশংসাপত্র) adhering to Ministry of Education guidelines.
- **Decision**:
  - **Student ID**: Generated sequentially per institution using pattern `{YEAR}{CLASS_ORDER:02d}{SEQUENCE:04d}` (e.g. `2026100001`), guaranteed unique via DB constraint `unique_student_id_per_institution`.
  - **Roll Numbers**: Scoped to `(institution, session, section, roll_no)` with unique DB constraint. Automated roll re-sequencing uses temporary high offsets (+100,000) during permutation to prevent intermediate collision violations.
  - **Promotion Engine**: Multi-step pipeline: `preview_promotion` generates staged `PromotionBatch` and `PromotionItem` records; `apply_promotion` executes atomic closing of previous enrollments and instantiation of next-session enrollments; `rollback_promotion` cleanly deletes created target enrollments and reactivates source records.
  - **Bangla PDF Generation**: Implemented via ReportLab using TrueType Unicode font registration. The `Kalpurush.ttf` font is bundled directly under `apps/core/fonts/` with system fallback paths (`/usr/share/fonts/...`). Standardized templates for Transfer Certificates, Testimonials, and Student ID Cards render cleanly without ligature distortion.
  - **Field-level Privacy**: Serializer representations dynamically mask 17-digit birth registration numbers and emergency contact phones for non-administrative users.
- **Consequences**:
  - Prevents data corruption during promotion and roll-numbering, guarantees compliance with Bangladeshi school administration norms, and produces crisp, official PDF documents out of the box.

---

## ADR-009: Guardian Identity Model, Household Family Grouping & Delegated Student Authorization
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: In Bangladeshi schools, a guardian may have multiple children across different classes/sections, while a student typically has multiple guardians (Father, Mother, Local Guardian, Uncle, etc.). Furthermore, schools require strict parent portal authentication, sibling discounts/grouping, emergency contact synchronization, and security controls for third-party student pickup (e.g. drivers or relatives).
- **Decision**:
  - **Decoupled User & Guardian Entities**: `Guardian` is a standalone master record scoped to the institution with a unique active phone constraint. A portal `User` is provisioned on-demand (`apps.accounts.models.UserType.GUARDIAN`), linking to the `Guardian` profile.
  - **Explicit Relationship Model (`StudentGuardian`)**: Multi-cardinality links between `Student` and `Guardian` store granular responsibility flags (`is_primary`, `can_pickup`, `receives_sms`, `financial_responsible`).
  - **Primary Contact Synchronization**: Setting a guardian as `is_primary=True` atomically demotes other primaries for that student and synchronizes `emergency_contact_name` and `emergency_contact_phone` on the `Student` master record. Unlinking a primary automatically promotes the next available guardian.
  - **Household Family Grouping (`Family`)**: Household unit characterized by `FAM-{YEAR}-{SEQUENCE}` grouping siblings for fee discounts and family notices. Sibling discovery searches across shared emergency contact phones and guardian NIDs.
  - **Authorized Pickup Verification (`AuthorizedPickup`)**: Third-party pickup individuals are registered with relation/phone details and validated via short-lived (10-minute) 6-digit OTP challenges cached in Redis and dispatched via `SMSService`.
  - **Object-Level Security (`IsGuardianOfStudent`)**: Guardian users are restricted from listing or viewing students outside their authorized `StudentGuardian` links.
- **Consequences**:
  - Delivers a secure, multi-child parent experience while maintaining strict multi-tenant isolation, automated primary contact invariants, and verified school pickup security.
