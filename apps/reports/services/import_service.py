"""Bulk CSV import framework with template generation, dry-run validation & atomic commit."""

import csv
from datetime import date
from io import StringIO
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from apps.accounts.models import User
from apps.institutions.models import Institution
from apps.reports.models import BulkImportJob, BulkImportStatus, BulkImportTarget
from apps.staff.models import Staff
from apps.students.models import Student

IMPORT_TEMPLATES: dict[str, list[str]] = {
    BulkImportTarget.STUDENTS: [
        "student_id",
        "name_en",
        "name_bn",
        "gender",
        "dob",
        "admission_date",
        "emergency_contact_name",
        "emergency_contact_phone",
    ],
    BulkImportTarget.STAFF: [
        "employee_id",
        "full_name_en",
        "full_name_bn",
        "gender",
        "dob",
        "phone",
        "joining_date",
    ],
}


def get_import_template_csv(target_type: str) -> bytes:
    """Return UTF-8 CSV header template for a supported bulk import target."""
    if target_type not in IMPORT_TEMPLATES:
        raise ValidationError(f"Unsupported bulk import target '{target_type}'.")
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(IMPORT_TEMPLATES[target_type])
    return buf.getvalue().encode("utf-8")


def _validate_student_rows(
    institution: Institution,
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    existing_ids = set(
        Student.objects.filter(institution=institution, is_deleted=False).values_list(
            "student_id", flat=True
        )
    )
    seen_ids: set[str] = set()

    for idx, row in enumerate(rows, start=2):
        sid = (row.get("student_id") or "").strip()
        name_en = (row.get("name_en") or "").strip()
        name_bn = (row.get("name_bn") or "").strip() or name_en
        gender = (row.get("gender") or "").strip().lower()
        dob_raw = (row.get("dob") or "").strip()
        adm_raw = (row.get("admission_date") or "").strip()

        if not sid or not name_en or gender not in {"male", "female", "other"}:
            errors.append({"row": idx, "error": "Missing/invalid student_id, name_en, or gender."})
            continue
        if sid in existing_ids or sid in seen_ids:
            errors.append({"row": idx, "error": f"Duplicate student_id '{sid}'."})
            continue
        try:
            dob = date.fromisoformat(dob_raw)
            admission_date = date.fromisoformat(adm_raw) if adm_raw else date.today()
        except ValueError:
            errors.append({"row": idx, "error": "Invalid date format; expected YYYY-MM-DD."})
            continue

        seen_ids.add(sid)
        valid.append(
            {
                "student_id": sid,
                "name_en": name_en,
                "name_bn": name_bn,
                "gender": gender,
                "dob": dob,
                "admission_date": admission_date,
                "emergency_contact_name": (row.get("emergency_contact_name") or "").strip(),
                "emergency_contact_phone": (row.get("emergency_contact_phone") or "").strip(),
            }
        )
    return valid, errors


def _validate_staff_rows(
    institution: Institution,
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    existing_ids = set(
        Staff.objects.filter(institution=institution, is_deleted=False).values_list(
            "employee_id", flat=True
        )
    )
    seen_ids: set[str] = set()

    for idx, row in enumerate(rows, start=2):
        eid = (row.get("employee_id") or "").strip()
        full_name = (row.get("full_name_en") or "").strip()
        gender = (row.get("gender") or "").strip().lower()
        dob_raw = (row.get("dob") or "").strip()
        join_raw = (row.get("joining_date") or "").strip()
        phone = (row.get("phone") or "").strip()

        if not eid or not full_name or not phone or gender not in {"male", "female", "other"}:
            errors.append(
                {
                    "row": idx,
                    "error": "Missing/invalid employee_id, full_name_en, phone, or gender.",
                }
            )
            continue
        if eid in existing_ids or eid in seen_ids:
            errors.append({"row": idx, "error": f"Duplicate employee_id '{eid}'."})
            continue
        try:
            dob = date.fromisoformat(dob_raw)
            joining_date = date.fromisoformat(join_raw) if join_raw else date.today()
        except ValueError:
            errors.append({"row": idx, "error": "Invalid date format; expected YYYY-MM-DD."})
            continue

        seen_ids.add(eid)
        valid.append(
            {
                "employee_id": eid,
                "full_name_en": full_name,
                "full_name_bn": (row.get("full_name_bn") or "").strip(),
                "gender": gender,
                "dob": dob,
                "phone": phone,
                "joining_date": joining_date,
            }
        )
    return valid, errors


@transaction.atomic
def run_bulk_import(
    *,
    institution: Institution,
    target_type: str,
    file_obj: UploadedFile,
    uploaded_by: User | None,
    dry_run: bool = True,
) -> BulkImportJob:
    """Validate CSV bulk import and optionally commit records atomically."""
    if target_type not in IMPORT_TEMPLATES:
        raise ValidationError(f"Unsupported bulk import target '{target_type}'.")

    raw_bytes = file_obj.read()
    file_obj.seek(0)
    decoded = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(decoded))
    rows = list(reader)

    if target_type == BulkImportTarget.STUDENTS:
        valid_rows, errors = _validate_student_rows(institution, rows)
    else:
        valid_rows, errors = _validate_staff_rows(institution, rows)

    status_val = BulkImportStatus.VALIDATED
    if not dry_run:
        if errors:
            status_val = BulkImportStatus.FAILED
        else:
            if target_type == BulkImportTarget.STUDENTS:
                Student.objects.bulk_create(
                    [Student(institution=institution, **item) for item in valid_rows]
                )
            else:
                Staff.objects.bulk_create(
                    [Staff(institution=institution, **item) for item in valid_rows]
                )
            status_val = BulkImportStatus.COMMITTED

    return BulkImportJob.objects.create(
        institution=institution,
        target_type=target_type,
        status=status_val,
        file=file_obj,
        dry_run=dry_run,
        total_rows=len(rows),
        valid_rows=len(valid_rows),
        error_rows=len(errors),
        errors_summary=errors[:100],
        uploaded_by=uploaded_by,
    )
