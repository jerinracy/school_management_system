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
