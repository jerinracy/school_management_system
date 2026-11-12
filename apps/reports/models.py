"""Models for saved report definitions, async/sync export jobs, and bulk import jobs."""

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class ReportDataset(models.TextChoices):
    STUDENTS = "students", "Students"
    DAILY_ATTENDANCE = "daily_attendance", "Daily Attendance"
    FEE_INVOICES = "fee_invoices", "Fee Invoices"
    FEE_PAYMENTS = "fee_payments", "Fee Payments"
    EXAM_RESULTS = "exam_results", "Exam Results"


class ExportFormat(models.TextChoices):
    CSV = "csv", "CSV"
    XLSX = "xlsx", "Excel (XLSX)"
    PDF = "pdf", "PDF"


class ExportJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class BulkImportTarget(models.TextChoices):
    STUDENTS = "students", "Students"
    STAFF = "staff", "Staff"


class BulkImportStatus(models.TextChoices):
    VALIDATED = "validated", "Validated (Dry Run)"
    COMMITTED = "committed", "Committed"
    FAILED = "failed", "Failed"


class ReportDefinition(TenantOwnedModel, SoftDeleteMixin):
    """Saved whitelisted report definition."""

    name = models.CharField(max_length=150)
    dataset = models.CharField(max_length=50, choices=ReportDataset.choices, db_index=True)
    selected_columns = models.JSONField(default=list)
    filters = models.JSONField(default=dict, blank=True)
    default_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_definitions",
    )
    is_shared = models.BooleanField(default=False)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Report Definition"
        verbose_name_plural = "Report Definitions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.dataset})"


class ReportExportJob(TenantOwnedModel):
    """Tracks generated report export files with expiry."""

    definition = models.ForeignKey(
        ReportDefinition,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="export_jobs",
    )
    dataset = models.CharField(max_length=50, choices=ReportDataset.choices)
    selected_columns = models.JSONField(default=list)
    filters = models.JSONField(default=dict, blank=True)
    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )
    status = models.CharField(
        max_length=20,
        choices=ExportJobStatus.choices,
        default=ExportJobStatus.PENDING,
        db_index=True,
    )
    file = models.FileField(upload_to="reports/exports/", null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="report_export_jobs",
    )
    error_message = models.TextField(blank=True)

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Report Export Job"
        verbose_name_plural = "Report Export Jobs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Export({self.dataset}, {self.export_format}, {self.status})"


class BulkImportJob(TenantOwnedModel):
    """Tracks dry-run validation and atomic commit of CSV bulk imports."""

    target_type = models.CharField(max_length=30, choices=BulkImportTarget.choices)
    status = models.CharField(
        max_length=20,
        choices=BulkImportStatus.choices,
        default=BulkImportStatus.VALIDATED,
        db_index=True,
    )
    file = models.FileField(upload_to="reports/imports/")
    dry_run = models.BooleanField(default=True)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    errors_summary = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bulk_import_jobs",
    )

    class Meta(TenantOwnedModel.Meta):
        verbose_name = "Bulk Import Job"
        verbose_name_plural = "Bulk Import Jobs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Import({self.target_type}, {self.status}, rows={self.total_rows})"
