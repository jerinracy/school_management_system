"""Whitelisted Report Builder & CSV/XLSX/PDF Export Engine (zero raw SQL)."""

import csv
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO, StringIO
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Model
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from apps.accounts.models import User
from apps.attendance.models import DailyAttendance
from apps.audit.models import AuditAction
from apps.audit.services.audit_service import record as audit_record
from apps.fees.models import Invoice, Payment
from apps.institutions.models import Institution
from apps.reports.models import ExportFormat, ExportJobStatus, ReportDataset, ReportExportJob
from apps.results.models import ExamResult
from apps.students.models import Student

EXPORT_EXPIRY_DAYS = 7
MAX_EXPORT_ROWS = 5000


@dataclass(frozen=True)
class DatasetSpec:
    model: type[Model]
    columns: tuple[str, ...]
    filter_fields: tuple[str, ...]
    has_soft_delete: bool = True


REPORT_DATASETS: dict[str, DatasetSpec] = {
    ReportDataset.STUDENTS: DatasetSpec(
        model=Student,
        columns=(
            "student_id",
            "name_en",
            "name_bn",
            "gender",
            "dob",
            "admission_date",
            "status",
        ),
        filter_fields=("gender", "status"),
    ),
    ReportDataset.DAILY_ATTENDANCE: DatasetSpec(
        model=DailyAttendance,
        columns=("date", "user_type", "status", "minutes_late", "total_minutes"),
        filter_fields=("date", "user_type", "status"),
    ),
    ReportDataset.FEE_INVOICES: DatasetSpec(
        model=Invoice,
        columns=(
            "invoice_number",
            "title",
            "billing_year",
            "billing_month",
            "total_payable",
            "paid_amount",
            "due_amount",
            "status",
            "due_date",
        ),
        filter_fields=("status", "billing_year", "billing_month"),
    ),
    ReportDataset.FEE_PAYMENTS: DatasetSpec(
        model=Payment,
        columns=("payment_method", "amount", "status", "transaction_id", "payment_date"),
        filter_fields=("payment_method", "status"),
    ),
    ReportDataset.EXAM_RESULTS: DatasetSpec(
        model=ExamResult,
        columns=("total_marks", "gpa", "letter_grade", "status", "is_passed"),
        filter_fields=("status", "is_passed"),
    ),
}


def validate_report_spec(
    *,
    dataset: str,
    selected_columns: list[str] | None,
    filters: dict[str, Any] | None,
) -> tuple[DatasetSpec, list[str], dict[str, Any]]:
    """Validate dataset, columns, and filters strictly against whitelists."""
    if dataset not in REPORT_DATASETS:
        raise ValidationError(f"Dataset '{dataset}' is not whitelisted.")
    spec = REPORT_DATASETS[dataset]

    cols = list(selected_columns) if selected_columns else list(spec.columns)
    invalid_cols = [c for c in cols if c not in spec.columns]
    if invalid_cols:
        raise ValidationError(
            f"Disallowed column(s) for dataset '{dataset}': {', '.join(invalid_cols)}."
        )

    clean_filters: dict[str, Any] = {}
    for key, val in (filters or {}).items():
        if key not in spec.filter_fields:
            raise ValidationError(f"Disallowed filter '{key}' for dataset '{dataset}'.")
        clean_filters[key] = val

    return spec, cols, clean_filters


def _render_csv(columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: "" if row.get(c) is None else str(row.get(c)) for c in columns})
    return buf.getvalue().encode("utf-8")


def _render_xlsx(dataset: str, columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = dataset[:31]
    ws.append(columns)
    for row in rows:
        ws.append(["" if row.get(c) is None else str(row.get(c)) for c in columns])
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def _render_pdf(dataset: str, columns: list[str], rows: list[dict[str, Any]]) -> bytes:
    buf = BytesIO()
    width, height = landscape(A4)
    pdf = canvas.Canvas(buf, pagesize=landscape(A4))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, height - 40, f"Report: {dataset}")

    y = height - 70
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(40, y, " | ".join(columns)[:135])
    y -= 16
    pdf.setFont("Helvetica", 9)

    for row in rows[:200]:
        if y < 45:
            pdf.showPage()
            y = height - 45
            pdf.setFont("Helvetica", 9)
        line = " | ".join(str(row.get(c, "")) for c in columns)[:135]
        pdf.drawString(40, y, line)
        y -= 14

    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def execute_report_export(
    *,
    export_job: ReportExportJob,
    actor: User | None = None,
) -> ReportExportJob:
    """Run a whitelisted query, render CSV/XLSX/PDF, save file, and write AuditLog."""
    export_job.status = ExportJobStatus.PROCESSING
    export_job.save(update_fields=["status", "updated_at"])

    try:
        spec, cols, clean_filters = validate_report_spec(
            dataset=export_job.dataset,
            selected_columns=list(export_job.selected_columns),
            filters=dict(export_job.filters or {}),
        )
        qs = spec.model._default_manager.filter(
            institution=export_job.institution,
            **clean_filters,
        )
        if spec.has_soft_delete:
            qs = qs.filter(is_deleted=False)

        rows = list(qs.values(*cols)[:MAX_EXPORT_ROWS])
        fmt = export_job.export_format
        if fmt == ExportFormat.XLSX:
            content = _render_xlsx(export_job.dataset, cols, rows)
            ext = "xlsx"
        elif fmt == ExportFormat.PDF:
            content = _render_pdf(export_job.dataset, cols, rows)
            ext = "pdf"
        else:
            content = _render_csv(cols, rows)
            ext = "csv"

        filename = f"{export_job.dataset}-{export_job.id}.{ext}"
        export_job.file.save(filename, ContentFile(content), save=False)
        export_job.row_count = len(rows)
        export_job.expires_at = timezone.now() + timedelta(days=EXPORT_EXPIRY_DAYS)
        export_job.status = ExportJobStatus.COMPLETED
        export_job.save(update_fields=["file", "row_count", "expires_at", "status", "updated_at"])

        audit_record(
            action=AuditAction.EXPORT,
            module="reports",
            target_model="ReportExportJob",
            target_object_id=export_job.id,
            target_repr=f"{export_job.dataset} ({export_job.export_format}, {len(rows)} rows)",
            actor=actor or export_job.requested_by,
            institution=export_job.institution,
            metadata={"dataset": export_job.dataset, "row_count": len(rows), "format": fmt},
        )
        return export_job
    except Exception as exc:
        export_job.status = ExportJobStatus.FAILED
        export_job.error_message = str(exc)
        export_job.save(update_fields=["status", "error_message", "updated_at"])
        raise


def create_and_run_export(
    *,
    institution: Institution,
    dataset: str,
    selected_columns: list[str] | None,
    filters: dict[str, Any] | None,
    export_format: str,
    requested_by: User | None,
    definition_id: Any = None,
) -> ReportExportJob:
    """Validate spec, create ReportExportJob, and execute synchronously."""
    _, cols, clean_filters = validate_report_spec(
        dataset=dataset,
        selected_columns=selected_columns,
        filters=filters,
    )
    job = ReportExportJob.objects.create(
        institution=institution,
        definition_id=definition_id,
        dataset=dataset,
        selected_columns=cols,
        filters=clean_filters,
        export_format=export_format,
        requested_by=requested_by,
    )
    return execute_report_export(export_job=job, actor=requested_by)
