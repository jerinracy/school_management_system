"""Bulk student import from Excel spreadsheet."""

import io
from datetime import date, datetime
from typing import Any
from uuid import UUID

import openpyxl
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassLevel, Section
from apps.core.utils.phone import normalize_bd_phone
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import (
    BloodGroup,
    EnrollmentStatus,
    Gender,
    Religion,
    Student,
    StudentEnrollment,
    StudentStatus,
)

EXPECTED_COLS = [
    "student_id",
    "name_en",
    "name_bn",
    "dob",
    "gender",
    "session_name",
    "class_code",
    "section_name",
    "roll_no",
]


def _parse_date(val: Any) -> date | None:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


def _get_val(row: tuple[Any, ...], col_idx: dict[str, int], key: str) -> str:
    idx = col_idx.get(key)
    if idx is not None and idx < len(row) and row[idx] is not None:
        return str(row[idx]).strip()
    return ""


def _validate_student_and_section(
    student_id: str,
    sec_key: tuple[str, str, str],
    roll_no: int,
    institution: Institution,
    seen_ids: set[str],
    seen_rolls: set[tuple[str, str, str, int]],
    sections_cache: dict[tuple[str, str, str], Section],
) -> list[str]:
    errors: list[str] = []
    if not student_id:
        errors.append("student_id is required.")
    elif student_id in seen_ids:
        errors.append(f"Duplicate student_id '{student_id}' in Excel file.")
    elif Student.objects.filter(
        institution=institution, student_id=student_id, is_deleted=False
    ).exists():
        errors.append(f"student_id '{student_id}' already exists in database.")
    seen_ids.add(student_id)

    if sec_key not in sections_cache:
        errors.append(
            f"Section '{sec_key[2]}' not found in class '{sec_key[1]}' for session '{sec_key[0]}'."
        )
    elif roll_no > 0:
        roll_key = (sec_key[0], sec_key[1], sec_key[2], roll_no)
        if roll_key in seen_rolls:
            errors.append(f"Duplicate roll_no {roll_no} in section '{sec_key[2]}'.")
        seen_rolls.add(roll_key)

        sec_obj = sections_cache[sec_key]
        if StudentEnrollment.objects.filter(
            institution=institution,
            section=sec_obj,
            session=sec_obj.session,
            roll_no=roll_no,
            is_deleted=False,
        ).exists():
            errors.append(f"Roll {roll_no} is already taken in section '{sec_key[2]}' in database.")
    return errors


def _commit_import_rows(institution: Institution, valid_rows: list[dict[str, Any]]) -> int:
    today = timezone.localdate()
    created_count = 0
    with transaction.atomic():
        for item in valid_rows:
            student = Student.objects.create(
                institution=institution,
                student_id=item["student_id"],
                name_en=item["name_en"],
                name_bn=item["name_bn"],
                dob=item["dob"],
                gender=item["gender"],
                birth_reg_no=item["birth_reg_no"],
                religion=item["religion"],
                blood_group=item["blood_group"],
                emergency_contact_phone=item["emergency_phone"],
                status=StudentStatus.ACTIVE,
                admission_date=today,
            )

            StudentEnrollment.objects.create(
                institution=institution,
                student=student,
                session=item["session"],
                class_level=item["class_level"],
                section=item["section"],
                shift=item["shift"],
                roll_no=item["roll_no"],
                enrollment_date=today,
                status=EnrollmentStatus.ACTIVE,
            )
            created_count += 1
    return created_count


def _validate_row_fields(
    name_en: str,
    name_bn: str,
    dob: date | None,
    gender: str,
    session_name: str,
    class_code: str,
    roll_raw: str,
    sessions_cache: dict[str, AcademicSession],
    classes_cache: dict[str, ClassLevel],
) -> tuple[list[str], int]:
    errors: list[str] = []
    if not name_en:
        errors.append("name_en is required.")
    if not name_bn:
        errors.append("name_bn is required.")
    if not dob:
        errors.append("Invalid or missing dob (format: YYYY-MM-DD).")
    if gender not in Gender.values:
        errors.append(f"Invalid gender '{gender}'. Must be one of {Gender.values}.")
    if session_name not in sessions_cache:
        errors.append(f"Session '{session_name}' not found.")
    if class_code not in classes_cache:
        errors.append(f"Class with code '{class_code}' not found.")

    try:
        roll_no = int(roll_raw)
        if roll_no <= 0:
            errors.append("roll_no must be positive.")
    except ValueError:
        roll_no = 0
        errors.append("roll_no must be a valid integer.")

    return errors, roll_no


def _process_single_row(
    row: tuple[Any, ...],
    col_idx: dict[str, int],
    sessions_cache: dict[str, AcademicSession],
    classes_cache: dict[str, ClassLevel],
    sections_cache: dict[tuple[str, str, str], Section],
    institution: Institution,
    seen_ids: set[str],
    seen_rolls: set[tuple[str, str, str, int]],
) -> tuple[list[str], dict[str, Any] | None, str]:
    student_id = _get_val(row, col_idx, "student_id")
    name_en = _get_val(row, col_idx, "name_en")
    name_bn = _get_val(row, col_idx, "name_bn")
    dob = _parse_date(row[col_idx["dob"]] if col_idx.get("dob") is not None else None)
    gender = _get_val(row, col_idx, "gender").lower()
    session_name = _get_val(row, col_idx, "session_name")
    class_code = _get_val(row, col_idx, "class_code")
    section_name = _get_val(row, col_idx, "section_name")
    roll_raw = _get_val(row, col_idx, "roll_no")
    birth_reg_no = _get_val(row, col_idx, "birth_reg_no")
    phone = _get_val(row, col_idx, "phone")
    religion = _get_val(row, col_idx, "religion").lower() or "islam"
    blood_group = _get_val(row, col_idx, "blood_group") or "unknown"

    row_errors, roll_no = _validate_row_fields(
        name_en,
        name_bn,
        dob,
        gender,
        session_name,
        class_code,
        roll_raw,
        sessions_cache,
        classes_cache,
    )

    sec_key = (session_name, class_code, section_name)
    sec_errors = _validate_student_and_section(
        student_id, sec_key, roll_no, institution, seen_ids, seen_rolls, sections_cache
    )
    row_errors.extend(sec_errors)

    if birth_reg_no and (len(birth_reg_no) != 17 or not birth_reg_no.isdigit()):
        row_errors.append("birth_reg_no must be exactly 17 digits.")

    normalized_phone = ""
    if phone:
        try:
            normalized_phone = normalize_bd_phone(phone)
        except ValidationError as e:
            row_errors.append(f"Invalid phone: {e}")

    if row_errors:
        return row_errors, None, student_id

    sec_obj = sections_cache[sec_key]
    item = {
        "student_id": student_id,
        "name_en": name_en,
        "name_bn": name_bn,
        "dob": dob,
        "gender": gender,
        "birth_reg_no": birth_reg_no or None,
        "religion": religion if religion in Religion.values else "islam",
        "blood_group": blood_group if blood_group in BloodGroup.values else "unknown",
        "emergency_phone": normalized_phone,
        "section": sec_obj,
        "class_level": sec_obj.class_level,
        "session": sec_obj.session,
        "shift": sec_obj.shift,
        "roll_no": roll_no,
    }
    return [], item, student_id


def import_students_from_excel(
    institution_id: UUID | str,
    file_bytes: bytes,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Parse Excel file containing student records and perform validation or commit import."""
    institution = Institution.objects.get(id=institution_id)
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sheet = wb.active
    if not sheet:
        raise ValidationError("Excel workbook has no active sheet.")

    rows = list(sheet.iter_rows(values_only=True))
    if not rows or len(rows) < 2:
        raise ValidationError("Excel file is empty or missing data rows.")

    header = [str(col).strip().lower() if col else "" for col in rows[0]]
    for col in EXPECTED_COLS:
        if col not in header:
            raise ValidationError(f"Missing required column '{col}' in Excel header.")

    col_idx = {col: header.index(col) for col in header if col}

    sessions_cache = {s.name: s for s in AcademicSession.objects.filter(institution=institution)}
    classes_cache = {c.code: c for c in ClassLevel.objects.filter(institution=institution)}
    sections_cache = {
        (s.session.name, s.class_level.code, s.name): s
        for s in Section.objects.filter(institution=institution).select_related(
            "session", "class_level", "shift"
        )
    }

    seen_ids: set[str] = set()
    seen_rolls: set[tuple[str, str, str, int]] = set()
    valid_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for row_num, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue

        row_errs, item, student_id = _process_single_row(
            row=row,
            col_idx=col_idx,
            sessions_cache=sessions_cache,
            classes_cache=classes_cache,
            sections_cache=sections_cache,
            institution=institution,
            seen_ids=seen_ids,
            seen_rolls=seen_rolls,
        )

        if row_errs:
            errors.append({"row": row_num, "student_id": student_id, "errors": row_errs})
        elif item:
            valid_rows.append(item)

    if dry_run or errors:
        return {
            "success": len(errors) == 0,
            "dry_run": dry_run,
            "total_rows": len(rows) - 1,
            "valid_count": len(valid_rows),
            "error_count": len(errors),
            "errors": errors,
        }

    created_count = _commit_import_rows(institution, valid_rows)
    return {
        "success": True,
        "dry_run": False,
        "created_count": created_count,
        "errors": [],
    }
