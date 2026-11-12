# Backup, Restore & Privacy Procedures

## 1. Recovery Objectives
- **RPO (Recovery Point Objective)**: <= 24 hours (daily automated `pg_dump` backups; <= 15 minutes when PostgreSQL WAL archiving is enabled).
- **RTO (Recovery Time Objective)**: <= 1 hour for full database + media restore.
- **Retention Policy**: 30 days local/object-storage retention (`BACKUP_RETENTION_DAYS=30`).

## 2. Automated Database Backup
Run via cron or Celery beat daily at 02:00 Asia/Dhaka:
```bash
python manage.py backup_database --retention-days 30
```
- **PostgreSQL**: produces custom-format compressed dump `db_backup_YYYYMMDD_HHMMSS.dump` using `pg_dump -Fc`.
- **SQLite (dev/test)**: produces consistent snapshot `db_backup_YYYYMMDD_HHMMSS.sqlite3` via `sqlite3.Connection.backup()`.
- **Media Files**: sync `MEDIA_ROOT` daily to encrypted off-site object storage (`rclone sync` / `aws s3 sync --sse AES256`).

## 3. Tested Restore Procedure
1. Stop `web`, `worker`, and `beat` services to prevent concurrent writes.
2. Restore PostgreSQL dump into a clean target database:
   ```bash
   pg_restore --clean --if-exists --no-owner -h $DB_HOST -U $DB_USER -d $DB_NAME /path/to/db_backup_YYYYMMDD_HHMMSS.dump
   ```
3. Restore `MEDIA_ROOT` from object storage.
4. Run `python manage.py migrate --check` and verify `GET /api/v1/health/` returns `200 OK`.
5. Restart `web`, `worker`, and `beat`.

## 4. Student / Guardian Privacy Export & Deletion
- **Data Export**:
  ```bash
  python manage.py privacy_export_student <student_uuid> --output /tmp/student_export.json
  ```
  Exports profile, guardian links, attendance count, and invoices as JSON and records an `AuditAction.EXPORT` entry.
- **Data Deletion / Anonymization**:
  Soft-delete or anonymize PII fields (`name_en`, `name_bn`, `phone`, `nid`, `avatar`) via admin service while retaining immutable financial/audit ledger integrity.
