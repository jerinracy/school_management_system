# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
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
