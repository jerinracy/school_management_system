"""Celery tasks for async report export generation & expired export cleanup."""

from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.reports.models import ReportExportJob
from apps.reports.services.report_service import execute_report_export


@shared_task(name="reports.generate_report_export_task")
def generate_report_export_task(export_job_id: str) -> dict[str, Any]:
    """Asynchronously execute a ReportExportJob."""
    job = ReportExportJob.objects.select_related("institution", "requested_by").get(
        id=export_job_id
    )
    execute_report_export(export_job=job, actor=job.requested_by)
    return {"export_job_id": str(job.id), "status": job.status, "row_count": job.row_count}


@shared_task(name="reports.purge_expired_report_exports")
def purge_expired_report_exports() -> dict[str, int]:
    """Delete expired report export files and records."""
    now = timezone.now()
    expired_qs = ReportExportJob.objects.filter(expires_at__isnull=False, expires_at__lt=now)
    deleted_count = 0
    for job in expired_qs:
        if job.file:
            job.file.delete(save=False)
        job.delete()
        deleted_count += 1
    return {"purged_exports": deleted_count}
