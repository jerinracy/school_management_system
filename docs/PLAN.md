# School Management System (Bangladesh) — Master Architecture & Plan

## 1. System Vision
A production-grade, multi-tenant School Management System tailored for Bangladeshi educational institutions (Primary, Secondary, Higher Secondary, Madrasa, English Medium/Version).
The system supports:
- Multi-device configurable biometric attendance (ZKTEco, Realtime, Hikvision, ADMS push).
- Academic management with GPA 5.0 grading (continuous evaluation, CQ, MCQ, practical, combined paper rules, 4th subject handling).
- Multi-channel fee collection (bKash, Nagad, Rocket, SSLCommerz, bank slip) with automated fine/waiver calculations.
- Staff HR, biometric-linked payroll, leave management.
- Communication suite (bulk Bangla Unicode SMS, push notifications via FCM, notices).
- Frontends:
  - Admin/Staff Web Dashboard (React 18 SPA served by `django-vite`).
  - Cross-platform Mobile App (Flutter for Guardians, Students, Teachers, Staff).

## 2. Repository Layout & Architecture
- **Backend**: Django 5.x, Django REST Framework, PostgreSQL 16, Redis, Celery 5.x.
- **Frontend SPA**: Vite + React 18 + TypeScript in `frontend/` served by `django-vite`.
- **Multi-Tenancy Model**: Shared Database with Discriminator Column (`institution_id`) on all tenant-owned entities.
  - Every tenant model inherits `TenantOwnedModel`.
  - Every API endpoint filters querysets by `request.user.institution`.
  - Strict tenant isolation enforced at ORM and service layer.

## 3. Module Map
| App | Description | Key Models |
|---|---|---|
| `core` | Base abstractions, mixins, BD utils, health | `BaseModel`, `TenantOwnedModel`, `SoftDeleteMixin` |
| `institutions` | Tenant core, branches, shifts, sessions, holidays | `Institution`, `Branch`, `Shift`, `AcademicSession`, `Holiday` |
| `accounts` | Users, roles, permissions, OTP, sessions | `User`, `Role`, `UserRole`, `OTPChallenge`, `UserSession` |
| `academics` | Classes, sections, subjects, routine | `ClassLevel`, `Section`, `Subject`, `RoutineSlot` |
| `admissions` | Online applications, tests, merit lists, lottery | `AdmissionCircular`, `Application`, `MeritList` |
| `students` | Student profiles, enrollments, roll numbers | `Student`, `StudentEnrollment`, `Guardian` |
| `staff` | Teachers, administrative staff, designations | `Staff`, `Department`, `Designation` |
| `devices` | Biometric machines, ADMS protocols | `BiometricDevice`, `DeviceSyncLog` |
| `attendance` | Daily attendance, shift rules, punches | `AttendanceRecord`, `RawPunchLog` |
| `exams` | Exam terms, schedules, mark entry, grade profiles | `Exam`, `ExamSchedule`, `MarkEntry`, `GradeProfile` |
| `results` | GPA 5.0 engine, report cards, tabulations | `StudentResult`, `TabulationSheet` |
| `fees` | Fee structures, invoices, waivers, fines | `FeeHead`, `FeeStructure`, `StudentInvoice` |
| `accounting` | Payment gateways (bKash/Nagad/SSLCommerz), ledger | `PaymentTransaction`, `JournalEntry` |
| `payroll` | Salary structures, payslips, deductions | `SalaryStructure`, `Payslip` |
| `communications` | SMS gateways, push notifications, notices | `SMSLog`, `Notice`, `PushNotification` |

## 4. Delivery Phases
- **Phase 1: Foundations & Core Identity** (Tasks 01–03)
- **Phase 2: Academic & Student Lifecycle** (Tasks 04–07)
- **Phase 3: Devices & Attendance Engine** (Tasks 08–10)
- **Phase 4: Examination & GPA 5.0 Engine** (Tasks 11–13)
- **Phase 5: Fees, Payments & Financials** (Tasks 14–17)
- **Phase 6: Communications, Portal & Auxiliary Modules** (Tasks 18–24)
- **Phase 7: End-to-End Hardening & Launch Readiness** (Tasks 25–26)
