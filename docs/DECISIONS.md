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

---

## ADR-010: Staff HR Architecture, Multi-Tier Leave Ledger & Teacher Workload Integration
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Bangladeshi schools require distinct employee identity management (with MPO indexing, educational qualifications, and department hierarchies), a robust leave management workflow (with annual quotas for Casual, Medical, and Maternity leave, and multi-tier HOD recommendation to Principal approval), and explicit curriculum teaching assignments replacing loose user references in academic timetables.
- **Decision**:
  - **Master Employee Directory (`Staff`)**: Encapsulates employee profile, sequential `employee_id` (`EMP-{YEAR}-{SEQUENCE}`), MPO status, NID, and contact details. Portal `User` account (`UserType.TEACHER` or `STAFF`) is linked via optional OneToOneField.
  - **Annual Leave Ledger (`LeaveBalance` & `LeaveRequest`)**: Leave quotas are instantiated per academic session. Applications compute exact calendar day spans and validate against date overlaps. Balance deductions reserve `pending_days` on application, convert to `used_days` on approval, and restore to balance on rejection or cancellation using row-level locking (`select_for_update()`).
  - **Hierarchical Approval Chain**: Leave transitions from `pending` to `recommended` (by HOD or supervisor) and `approved` (by Principal / authorized manager).
  - **Academic Bridge**: `Section`, `RoutineSlot`, and `SubstituteAssignment` models are extended with nullable `teacher_staff` foreign keys. Backward compatibility is retained for existing `teacher_user` fields while enabling transition to rich Staff profiles.
- **Consequences**:
  - Eliminates leave balance overdraws and concurrency race conditions, provides clean MPO tracking for Bangladeshi school regulatory audits, and unifies academic routine management under concrete Staff profiles.

---

## ADR-011: Vendor-Agnostic Biometric Architecture, Raw Punch Immutability & Child Privacy Compliance
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Bangladeshi schools deploy a diverse range of biometric attendance hardware (ZKTeco ADMS push, Hikvision ISAPI, Suprema BioStar, eSSL, RFID cards, and virtual simulators). Hardware devices experience clock drift, intermittent connectivity causing buffer resends, and numeric PIN registries that do not natively map to student/staff UUIDs. Furthermore, strict privacy guidelines (`AGENTS.md §A3 Rule 4`) forbid storing raw biometric images or templates, and student enrollment requires legal guardian authorization.
- **Decision**:
  - **Zero Raw Biometric Templates**: Neither raw fingerprint images nor facial recognition feature templates are accepted or stored in the database. `BiometricEnrollment` records store only terminal device metadata and user PINs.
  - **Mandatory Guardian Consent**: Minor students require signed guardian consent (`BiometricConsent`) before hardware enrollment. Consent withdrawal immediately marks enrollments inactive and queues device deletion commands.
  - **Vendor-Agnostic Adapter Pattern**: `BaseDeviceAdapter` defines a normalized interface for request authentication, payload parsing, and command formatting. `AdapterRegistry` dynamically binds devices by `(vendor, protocol)` with support for ZKTeco ADMS push, Generic HTTP HMAC-SHA256 webhooks, and virtual simulators.
  - **Immutable Append-Only Punch Ledger**: All incoming scans are stored in `RawPunch`. A database unique constraint on `(device, raw_user_id, device_time)` ensures intake idempotency and deduplication during hardware network retransmissions.
  - **Review Queue for Unmapped Punches**: Unrecognized hardware PINs are captured with `status="unmapped"`. Resolving an unmapped punch creates a persistent `DeviceUserMap` and automatically reconciles all pending punches for that PIN.
  - **Native ADMS Protocol Support**: Standard ZKTeco endpoints are served directly at the root (`/iclock/cdata`, `/iclock/getrequest`, `/iclock/devicecmd`), allowing out-of-the-box hardware terminal configuration without reverse proxy rewrites.
- **Consequences**:
  - Full compliance with child biometric privacy standards, complete hardware vendor neutrality, resilient intake capable of handling hardware buffer bursts, and an auditable queue for terminal administration.

---

## ADR-012: Attendance Rule Engine, Multi-Punch Normalization & Geofenced Mobile Check-in
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**: Bangladeshi schools operate under heterogeneous attendance policies: primary shifts vs secondary morning/day shifts, strict grace minutes (e.g. 15 min), late vs half-day thresholds, early departure monitoring, teacher subject-wise roll calls, and mobile field check-ins for transport/support staff. Furthermore, hardware punch streams from Task 09 can produce rapid multi-taps within seconds, and end-of-day absentee reconciliation must reliably respect institutional holidays, Friday/Saturday weekends, and approved staff leave.
- **Decision**:
  - **Pure Deterministic Rule Engine**: The core business logic (`evaluate_daily_status()`) is implemented as a pure Python function without database side effects. Given a sequence of events and a policy, it deterministically computes status (`present`, `late`, `half_day`, `absent`, `holiday`, `weekend`, `leave`), arrival delay, early leave, and total working minutes.
  - **Multi-Punch Deduplication & Batch Window**: `PunchProcessor` deduplicates punches within a 60-second window across both current in-flight batch buffers and persisted `AttendanceEvent` records before triggering daily recalculations.
  - **Hierarchical Policy Resolution**: `resolve_effective_policy()` determines the applicable policy by searching in priority order: Class Level > Shift > Branch > Default Institution Policy.
  - **Server-Side Haversine Geofencing**: Mobile check-ins calculate the great-circle distance between staff GPS coordinates and the branch campus anchor. Check-ins outside the configured radius are logged with distance and verification metadata, but denied automatic check-in event generation.
  - **Asynchronous EOD Absentee Processing**: Celery tasks decouple long-running end-of-day roll evaluation (`mark_daily_absentees_task`) from web request lifecycles.
  - **Formal Correction Workflow**: Discrepancies in attendance records require a structured `AttendanceCorrection` request with change audit tracking and administrative approval/rejection.
- **Consequences**:
  - Predictable, unit-testable attendance status resolution; immune to duplicate punch storms; robust multi-shift institutional flexibility; and full auditability of manual interventions.

---

## ADR-013: Examination Lifecycle, Component Mark Schema, Algorithmic Seating & TrueType Admit Cards
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**:
  - Bangladeshi secondary and higher-secondary examinations require structured mark distribution across distinct components (Creative Question / Written, Multiple Choice Question, and Practical).
  - Passing rules vary: some subjects require passing each component independently, others enforce an overall aggregate threshold, and some separate theory from practical.
  - Exam administration demands automated seating arrangements (including cross-class interleaving to curb malpractices), TrueType bilingual Bangla admit cards with student particulars and routine schedules, rigorous teacher mark-entry authorization, lock/unlock mechanics, and offline bulk mark entry via Excel spreadsheets.
- **Decision**:
  - **Component-Level Mark Schema**: `ExamSubject` explicitly defines maximum and passing marks for CQ, MCQ, and Practical, along with the `pass_policy` (`all_components`, `overall_aggregate`, `theory_practical_separate`).
  - **Teacher Authorization & Lock Mechanism**: Mark entry is restricted to assigned subject teachers or institutional administrators. Once marked as `is_locked`, entries cannot be modified without formal unlock authorization by head teachers / administrators.
  - **Audit Trail via MarkEntryLog**: Every creation and modification of student scores creates an immutable `MarkEntryLog` capturing previous scores, new scores, the submitting user, IP address, and change rationale.
  - **Cross-Class Interleaved Seating**: The seating algorithm partitions students by class/section and alternates seats across benches in examination venues, optimizing space while minimizing adjacent peers from the same class.
  - **TrueType Bangla PDF Generation**: Admit cards are generated via ReportLab using embedded TrueType `Kalpurush.ttf`, rendering Bengali typography (student name, institution header, rules, and exam routine table) cleanly without missing glyphs.
  - **Excel Bulk Mark Entry**: In-memory Excel workbook generation and parsing via `openpyxl` allows teachers to download prepopulated student roll sheets, enter marks offline, and upload them with per-row validation and error feedback.
- **Consequences**:
  - Complete alignment with Bangladesh National Curriculum examinations.
  - High resilience against unauthorized mark alterations, backed by non-repudiation audit trails.
  - Streamlined exam day administration with automated admit cards and fraud-resistant seat plans.

---

## ADR-014: Deterministic GPA 5.0 Grading Engine, 4th Subject Bonus, Combined Paper Grading & Merit Hierarchy
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**:
  - The Bangladesh National Curriculum (administered by Secondary and Higher Secondary Education Boards, NCTB) enforces specific mathematical rules for secondary (SSC/JSC) and higher-secondary (HSC) grading:
    1. Standard 7-tier scale: A+ (5.0, 80-100%), A (4.0, 70-79%), A- (3.5, 60-69%), B (3.0, 50-59%), C (2.0, 40-49%), D (1.0, 33-39%), F (0.0, 0-32%).
    2. Mandatory failure rule: Failing any mandatory subject (Grade Point 0.00 / Grade F) results in an overall exam Grade Point of 0.00 and Letter Grade 'F', regardless of high scores in other subjects.
    3. Fourth (optional/elective) subject bonus: Grade points earned above 2.00 (i.e. $\max(0, \text{GP} - 2.00)$, yielding up to 3.00 bonus points) are added to the numerator of the GPA formula, divided by the count of mandatory subjects, capped at 5.00. Failing a 4th subject does NOT fail the student or reduce their GPA.
    4. Combined papers: Paired subjects (e.g. Bangla 1st + 2nd, English 1st + 2nd) are evaluated over an aggregate of 200 marks, with pass marks (typically 66/200) determined either jointly or per component.
    5. Deterministic tie-breaking for merit ranks: Passing candidates always rank above failing candidates, followed by final GPA descending, total aggregate marks descending, and enrollment roll number ascending.
    6. Multi-term weighted CGPA: Annual session results aggregate multiple examinations with configurable weightages (e.g. Term 1 30%, Term 2 30%, Annual 40%).
- **Decision**:
  - **Decoupled Pure Grading Engine**: Implement `apps/results/services/grading_engine.py` as a pure, side-effect-free mathematical calculation layer with zero database dependencies. All formulas, tier resolutions, bonus calculations, and sorting rules are fully unit-tested with table-driven golden test suites.
  - **Transactional Tabulation Service**: Orchestrate database reads, atomic batch evaluation, and rank persistence via `apps/results/services/result_processor.py` (`tabulate_exam_results` and `tabulate_cumulative_results`).
  - **Background Async Celery Tasks**: Heavy tabulation runs for thousands of students are dispatched asynchronously (`calculate_exam_results_task`, `calculate_cumulative_results_task`) with synchronous fallbacks for instant API responses.
  - **Full Documentation**: Canonical specification published in `docs/GRADING.md`.
- **Consequences**:
  - 100% compliant with Bangladeshi national examination and board grading standards.
  - High computational performance and rock-solid determinism in merit rank assignment.
  - Complete decoupling enables straightforward testing and future extensions (such as semester systems or university 4.0 scales).

---

## ADR-015: Bilingual Report Card Typography, Broadsheet Tabulation & Examination Publication Lifecycle
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**:
  - Academic administration in Bangladeshi schools culminates in two primary artifacts and a strict release workflow:
    1. **Tabulation Broadsheet**: A master multi-column ledger (in both Excel and landscape PDF formats) displaying every enrolled student alongside every subject with breakdown of CQ, MCQ, and practical marks, subject GP/LG, grand total marks, GPAs (with and without 4th subject), and class/section merit positions.
    2. **Student Progress Report Card**: Official individual document containing bilingual (Bangla and English) school details, student particulars, term attendance metrics, subject-wise marks alongside cohort highest marks, GPA 5.0 breakdown, NCTB grading scale legend, teacher remarks, and signature blocks.
    3. **Result Publication Lifecycle**: Results must remain inaccessible to students and guardians while undergoing teacher verification, administrative tabulation, and principal approval. Once formally approved and published, results become visible in student/guardian portals and optional public search portals.
    4. **Academic Diagnostics & Promotion Feed**: Early detection of failing/borderline students for remedial intervention, and annual promotion qualification based on CGPA and minimum attendance thresholds.
- **Decision**:
  - **Dynamic Tabulation Engine (`apps/results/services/tabulation_service.py`)**:
    - Generates multi-level Excel spreadsheets via `openpyxl` with dynamic multi-row header merging per subject (CQ, MCQ, PR, Tot, GP, Grade), auto-fit column widths, zebra striping, and soft-red highlighting on failing components.
    - Generates landscape A4 broadsheet PDFs using ReportLab (`render_story_to_pdf`) with embedded `Kalpurush.ttf` fonts.
  - **Bilingual Progress Report Cards (`apps/results/services/report_card_service.py`)**:
    - Built using ReportLab Flowables (`Paragraph`, `Table`, `Spacer`, `HRFlowable`) utilizing `apps.core.pdf.engine` and TrueType `Kalpurush.ttf`.
    - Real-time attendance integration pulling working days, attendance counts, and presence percentages from `DailyAttendance`.
    - In-memory ZIP archive generation streaming all student progress report cards into a single downloadable file.
  - **Publication Security & Access Control (`apps/results/services/publication_service.py`)**:
    - Multi-stage publication model: `draft` -> `approved` -> `published` (with optional `withheld` or `unpublished` rollbacks).
    - `can_view_exam_result` predicate enforces that students and guardians cannot view results or download report cards until the exam is officially approved and published.
  - **Diagnostic Analytics (`apps/results/services/analytics_service.py`)**:
    - `get_weak_students_analytics`: Identifies students at risk (failing subjects or GPA below threshold) along with frequency analysis of failing subjects across the cohort.
    - `get_promotion_eligibility_feed`: Categorizes session cohorts into `eligible`, `conditional`, and `retained` based on minimum CGPA and attendance percentage.
- **Consequences**:
  - Provides institutional administrators and examination committees with complete broadsheet oversight.
  - Generates authentic, board-compliant report cards with professional Bengali typography.
  - Prevents premature result leakage before official administrative sign-off.

---

## ADR-016: Multi-Tier Fee Structures, Concurrency-Safe Invoice Sequencing, Waivers & Late Fine Mechanics
- **Date**: 2026-11-11
- **Status**: Accepted
- **Context**:
  - Bangladeshi school fee management requires granular recurring fee heads (`Tuition`, `Admission`, `Session Charge`, `Exam`, `Laboratory`, `Library`, `Transport`, `Hostel`), class/session fee templates, individualized exemptions or custom rates, multi-category waivers (sibling, merit, poor fund, quota, teacher child), and late fines.
  - Invoicing requires concurrency safety (avoiding duplicate sequential numbers e.g. `INV-2026-000001`), deduplication against accidental re-billing in the same month, and printable 3-part bank deposit slips (School Copy, Bank Copy, Student Copy).
- **Decision**:
  - **Relational Domain Architecture (`apps/fees`)**:
    - `FeeHead` defines categories with recurrence rules (`one_time`, `monthly`, `termly`, `annually`), opt-in flags, and accounting general ledger codes.
    - `FeeStructure` and `FeeStructureItem` establish standardized rate schedules per class and session, while `StudentFeeAssignment` accommodates individual opt-ins (e.g. transport) and rate customizations.
    - `WaiverRule` and `StudentWaiver` enforce a strict two-stage approval workflow (`pending` $\to$ `approved` / `rejected`) preventing unapproved concessions from impacting issued invoices.
    - `FineRule` supports fixed, daily accrual, and slab-based late payment penalties with configurable grace periods.
    - `Invoice` and `InvoiceLine` model itemized billing with positive monetary constraints (`CheckConstraint(amount >= 0)`) and auto-balanced totals.
  - **Concurrency-Safe Sequencing (`InvoiceSequence`)**:
    - `get_next_invoice_number` uses row-level locking (`select_for_update()`) on institutional sequence records within atomic transactions to eliminate gaps and race conditions during bulk generation.
  - **Deduplication & Bulk Billing (`invoice_service.py`)**:
    - Bulk generation evaluates existing non-cancelled invoices for `(student, session, billing_year, billing_month)` to ensure safe, idempotent batch runs.
  - **Authentic Bengali PDF Output (`invoice_pdf_service.py`)**:
    - Uses ReportLab with TrueType `Kalpurush.ttf` to render bilingual demand and payment receipt slips.
- **Consequences**:
  - Provides institutional cashiers and accountants with complete, automated monthly billing.
  - Guarantees financial auditability and monetary integrity.
  - Ready for online payment collection and gateway settlement in Task 15.
