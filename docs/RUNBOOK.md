# Production Operations Runbook

## 1. Service Topology
- **Web / API**: Gunicorn (`config.wsgi:application`) behind Nginx / reverse proxy with TLS termination (`X-Forwarded-Proto: https`).
- **Async Workers**: Celery worker (`celery -A config worker -l info`) + Celery beat (`celery -A config beat -l info`).
- **State Stores**: PostgreSQL 16 + Redis 7 (broker, cache, rate limiting).

## 2. Health, Metrics & Monitoring
- **Health Probe**: `GET /api/v1/health/` — verifies PostgreSQL (`SELECT 1`) and Redis (`PING`). Returns `200 OK` when healthy or `503 Service Unavailable` when DB is unreachable.
- **Operational Metrics**: `GET /api/v1/metrics/` (admin-only) — returns active institutions, active users, `enforce_admin_2fa` flag, and debug state.
- **Sentry**: Set `SENTRY_DSN` and `SENTRY_TRACES_SAMPLE_RATE` (`0.1` default). `send_default_pii=False` is enforced.
- **Celery Monitoring (Flower)**:
  ```bash
  celery -A config flower --port=5555 --basic_auth=$FLOWER_USER:$FLOWER_PASSWORD
  ```
- **Slow-Query & SQL Logging**:
  - Set `LOG_SQL_QUERIES=true` temporarily in staging/prod diagnostics to emit `django.db.backends` queries to structured logs.
  - Enable PostgreSQL `log_min_duration_statement = 250` (ms) in `postgresql.conf` for production slow-query capture.

## 3. Incident Response Checklist
1. Check `/api/v1/health/` and container logs (`web`, `worker`, `beat`, `postgres`, `redis`).
2. Inspect `AuditLog` (`/api/v1/audit/logs/`) for recent role changes, overrides, or exports.
3. For suspected credential compromise: revoke user sessions, rotate `FIELD_ENCRYPTION_KEYS` / `SECRET_KEY`, and verify `ENFORCE_ADMIN_2FA=True`.
