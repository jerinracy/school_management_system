"""Service for validating, recording, locking, and importing/exporting examination marks."""

import io
import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

import openpyxl
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from apps.accounts.models import User
from apps.exams.models import ExamSubject, MarkEntry, MarkEntryLog
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment

logger = logging.getLogger(__name__)


def _check_mark_bound(name: str, val: Decimal | None, max_val: Decimal) -> None:
    if val is not None:
        if val < Decimal("0.00") or val > max_val:
            raise ValidationError(
                f"{name} ({val}) cannot be negative or exceed maximum ({max_val})."
            )


def validate_component_marks(
    exam_subject: ExamSubject,
    creative_marks: Decimal | None,
    mcq_marks: Decimal | None,
    practical_marks: Decimal | None,
    is_absent: bool = False,
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    """Validate component marks against subject thresholds and return normalized (CQ, MCQ, Practical, Total)."""
    if is_absent:
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    cq = Decimal(str(creative_marks)) if creative_marks is not None else None
    mcq = Decimal(str(mcq_marks)) if mcq_marks is not None else None
    prac = Decimal(str(practical_marks)) if practical_marks is not None else None

    _check_mark_bound("Creative marks", cq, exam_subject.creative_full_marks)
    _check_mark_bound("MCQ marks", mcq, exam_subject.mcq_full_marks)
    _check_mark_bound("Practical marks", prac, exam_subject.practical_full_marks)

    total = sum((v for v in (cq, mcq, prac) if v is not None), Decimal("0.00"))
    if total > exam_subject.full_marks:
        raise ValidationError(
            f"Calculated total marks ({total}) exceeds full marks ({exam_subject.full_marks})."
        )

    return cq, mcq, prac, total


def check_teacher_mark_entry_permission(user: User, exam_subject: ExamSubject) -> bool:
    """Verify if user is authorized to enter marks for this exam subject.

    Superusers, institutional admins, assigned teachers via exam_subject,
    teachers assigned to this subject/class in routine slots, or teachers of the institution are authorized.
    """
    if user.is_superuser:
        return True

    # Check administrative roles
    if user.user_roles.filter(
        role__code__in=["super_admin", "admin", "principal", "exam_controller", "admin_role"]
    ).exists():
        return True

    # Check assigned teacher link on ExamSubject
    staff_profile = getattr(user, "staff_profile", None)
    if not staff_profile:
        from apps.staff.models import Staff

        staff_profile = Staff.objects.filter(user=user).first()

    if staff_profile and exam_subject.assigned_teacher_id:
        return exam_subject.assigned_teacher_id == staff_profile.id

    if exam_subject.assigned_teacher_id:
        return False

    # Check if teacher is assigned to this subject for this class level in RoutineSlot
    from apps.academics.models import RoutineSlot

    routine_q = RoutineSlot.objects.filter(
        section__class_level=exam_subject.class_level,
        subject=exam_subject.subject,
    )
    if staff_profile and routine_q.filter(teacher_staff=staff_profile).exists():
        return True
    if routine_q.filter(teacher_user=user).exists():
        return True

    # If teacher belongs to the same institution and user_type is teacher, allow entry
    if (
        getattr(user, "user_type", None) == "teacher"
        or user.user_roles.filter(role__name__icontains="Teacher").exists()
    ):
        if user.institution_id == exam_subject.institution_id:
            return True

    return False


@transaction.atomic
def save_single_mark_entry(
    exam_subject: ExamSubject,
    student: Student,
    user: User,
    creative_marks: Decimal | None = None,
    mcq_marks: Decimal | None = None,
    practical_marks: Decimal | None = None,
    is_absent: bool = False,
    reason: str = "",
) -> MarkEntry:
    """Validate, record, and log mark entry for a student."""
    if exam_subject.is_marks_locked:
        raise ValidationError(f"Marks for {exam_subject} are locked against editing.")

    if not check_teacher_mark_entry_permission(user, exam_subject):
        raise PermissionDenied("You do not have permission to enter marks for this exam subject.")

    cq, mcq, prac, total = validate_component_marks(
        exam_subject=exam_subject,
        creative_marks=creative_marks,
        mcq_marks=mcq_marks,
        practical_marks=practical_marks,
        is_absent=is_absent,
    )

    entry = MarkEntry.objects.filter(exam_subject=exam_subject, student=student).first()

    if entry:
        if entry.is_locked:
            raise ValidationError(
                f"Mark entry for student {student.student_id} is individually locked."
            )

        # Log changes
        changes = []
        if entry.creative_marks != cq:
            changes.append(("creative_marks", str(entry.creative_marks), str(cq)))
        if entry.mcq_marks != mcq:
            changes.append(("mcq_marks", str(entry.mcq_marks), str(mcq)))
        if entry.practical_marks != prac:
            changes.append(("practical_marks", str(entry.practical_marks), str(prac)))
        if entry.is_absent != is_absent:
            changes.append(("is_absent", str(entry.is_absent), str(is_absent)))

        for field_name, old_val, new_val in changes:
            MarkEntryLog.objects.create(
                institution=exam_subject.institution,
                mark_entry=entry,
                modified_by=user,
                field_name=field_name,
                old_value=old_val,
                new_value=new_val,
                reason=reason or "Mark updated via entry interface",
            )

        entry.creative_marks = cq
        entry.mcq_marks = mcq
        entry.practical_marks = prac
        entry.total_marks = total
        entry.is_absent = is_absent
        entry.entered_by = user
        entry.save()
    else:
        entry = MarkEntry.objects.create(
            institution=exam_subject.institution,
            exam_subject=exam_subject,
            student=student,
            creative_marks=cq,
            mcq_marks=mcq,
            practical_marks=prac,
            total_marks=total,
            is_absent=is_absent,
            entered_by=user,
        )

    return entry


@transaction.atomic
def bulk_save_marks(
    exam_subject_id: UUID | str,
    entries_data: list[dict[str, Any]],
    user: User,
) -> tuple[int, list[str]]:
    """Batch save student mark records inside an atomic transaction."""
    exam_subject = ExamSubject.objects.select_related("institution", "class_level", "subject").get(
        id=exam_subject_id
    )

    if exam_subject.is_marks_locked:
        raise ValidationError(f"Marks for {exam_subject} are locked against editing.")

    if not check_teacher_mark_entry_permission(user, exam_subject):
        raise PermissionDenied("You do not have permission to enter marks for this exam subject.")

    saved_count = 0
    errors: list[str] = []

    for idx, item in enumerate(entries_data, start=1):
        student_id = item.get("student_id")
        if not student_id:
            errors.append(f"Row {idx}: Missing student_id")
            continue
        try:
            student = Student.objects.get(id=str(student_id), institution=exam_subject.institution)
            save_single_mark_entry(
                exam_subject=exam_subject,
                student=student,
                user=user,
                creative_marks=item.get("creative_marks"),
                mcq_marks=item.get("mcq_marks"),
                practical_marks=item.get("practical_marks"),
                is_absent=item.get("is_absent", False),
                reason=item.get("reason", "Bulk grid save"),
            )
            saved_count += 1
        except Exception as exc:
            errors.append(f"Row {idx} (Student {student_id}): {exc}")

    return saved_count, errors


@transaction.atomic
def lock_exam_subject_marks(exam_subject_id: UUID | str, user: User) -> ExamSubject:
    """Lock mark entry for an entire ExamSubject, preventing further teacher modifications."""
    exam_subject = ExamSubject.objects.select_related("institution").get(id=exam_subject_id)
    exam_subject.is_marks_locked = True
    exam_subject.save(update_fields=["is_marks_locked", "updated_at"])

    now = timezone.now()
    MarkEntry.objects.filter(exam_subject=exam_subject).update(
        is_locked=True,
        locked_by=user,
        locked_at=now,
    )
    return exam_subject


@transaction.atomic
def unlock_exam_subject_marks(exam_subject_id: UUID | str, user: User, reason: str) -> ExamSubject:
    """Administratively unlock an ExamSubject and log the unlock event."""
    exam_subject = ExamSubject.objects.select_related("institution").get(id=exam_subject_id)
    exam_subject.is_marks_locked = False
    exam_subject.save(update_fields=["is_marks_locked", "updated_at"])

    MarkEntry.objects.filter(exam_subject=exam_subject).update(is_locked=False)

    # Log unlock event across marks
    for mark in MarkEntry.objects.filter(exam_subject=exam_subject)[:10]:
        MarkEntryLog.objects.create(
            institution=exam_subject.institution,
            mark_entry=mark,
            modified_by=user,
            field_name="is_locked",
            old_value="True",
            new_value="False",
            reason=f"Administrative unlock: {reason}",
        )

    return exam_subject


def export_mark_entry_excel(exam_subject_id: UUID | str) -> bytes:
    """Generate pre-filled Excel template for bulk offline mark entry."""
    exam_subject = ExamSubject.objects.select_related(
        "exam", "class_level", "subject", "institution", "exam__session"
    ).get(id=exam_subject_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Marks Entry"

    # Styles
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    meta_font = Font(name="Calibri", size=11, bold=True)
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # Title & Metadata
    ws["A1"] = f"{exam_subject.institution.name_en} - Examination Mark Entry Sheet"
    ws["A1"].font = title_font
    ws["A2"] = (
        f"Exam: {exam_subject.exam.name} | Class: {exam_subject.class_level.name} | Subject: {exam_subject.subject.name_en}"
    )
    ws["A2"].font = meta_font
    ws["A3"] = (
        f"Max Marks -> CQ: {exam_subject.creative_full_marks} | MCQ: {exam_subject.mcq_full_marks} | "
        f"Practical: {exam_subject.practical_full_marks} | Full: {exam_subject.full_marks}"
    )
    ws["A3"].font = meta_font

    # Column Headers
    headers = [
        "Student UUID",
        "Student ID",
        "Roll No",
        "Student Name",
        f"CQ Marks (Max {exam_subject.creative_full_marks})",
        f"MCQ Marks (Max {exam_subject.mcq_full_marks})",
        f"Practical (Max {exam_subject.practical_full_marks})",
        "Absent? (Y/N)",
    ]

    for col_num, h_text in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col_num, value=h_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Populate Student Rows
    enrollments = (
        StudentEnrollment.objects.filter(
            institution=exam_subject.institution,
            session=exam_subject.exam.session,
            class_level=exam_subject.class_level,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("student")
        .order_by("roll_no")
    )

    row_num = 6
    for enr in enrollments:
        student = enr.student
        existing_mark = MarkEntry.objects.filter(exam_subject=exam_subject, student=student).first()

        cq_val = (
            float(existing_mark.creative_marks)
            if existing_mark and existing_mark.creative_marks is not None
            else ""
        )
        mcq_val = (
            float(existing_mark.mcq_marks)
            if existing_mark and existing_mark.mcq_marks is not None
            else ""
        )
        prac_val = (
            float(existing_mark.practical_marks)
            if existing_mark and existing_mark.practical_marks is not None
            else ""
        )
        abs_val = "Y" if existing_mark and existing_mark.is_absent else "N"

        ws.cell(row=row_num, column=1, value=str(student.id))
        ws.cell(row=row_num, column=2, value=student.student_id)
        ws.cell(row=row_num, column=3, value=enr.roll_no)
        ws.cell(row=row_num, column=4, value=student.name_en)
        ws.cell(row=row_num, column=5, value=cq_val)
        ws.cell(row=row_num, column=6, value=mcq_val)
        ws.cell(row=row_num, column=7, value=prac_val)
        ws.cell(row=row_num, column=8, value=abs_val)

        for c in range(1, 9):
            ws.cell(row=row_num, column=c).border = thin_border

        row_num += 1

    # Adjust Column Widths
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_length + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@transaction.atomic
def import_mark_entry_excel(
    exam_subject_id: UUID | str,
    file_bytes: bytes,
    user: User,
) -> tuple[int, list[str]]:
    """Parse uploaded Excel file and update student mark entries."""
    exam_subject = ExamSubject.objects.select_related("institution", "class_level", "subject").get(
        id=exam_subject_id
    )

    if exam_subject.is_marks_locked:
        raise ValidationError(f"Marks for {exam_subject} are locked against editing.")

    if not check_teacher_mark_entry_permission(user, exam_subject):
        raise PermissionDenied("You do not have permission to enter marks for this exam subject.")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active

    imported_count = 0
    errors: list[str] = []

    # Student rows start from row 6
    for row_idx in range(6, ws.max_row + 1):
        s_uuid_cell = ws.cell(row=row_idx, column=1).value
        if not s_uuid_cell:
            continue

        student_uuid_str = str(s_uuid_cell).strip()
        cq_raw = ws.cell(row=row_idx, column=5).value
        mcq_raw = ws.cell(row=row_idx, column=6).value
        prac_raw = ws.cell(row=row_idx, column=7).value
        abs_raw = str(ws.cell(row=row_idx, column=8).value or "N").strip().upper()

        is_absent = abs_raw in ["Y", "YES", "TRUE", "1"]

        try:
            student = Student.objects.get(id=student_uuid_str, institution=exam_subject.institution)

            cq = Decimal(str(cq_raw)) if cq_raw not in [None, ""] and not is_absent else None
            mcq = Decimal(str(mcq_raw)) if mcq_raw not in [None, ""] and not is_absent else None
            prac = Decimal(str(prac_raw)) if prac_raw not in [None, ""] and not is_absent else None

            save_single_mark_entry(
                exam_subject=exam_subject,
                student=student,
                user=user,
                creative_marks=cq,
                mcq_marks=mcq,
                practical_marks=prac,
                is_absent=is_absent,
                reason="Bulk Excel import",
            )
            imported_count += 1
        except Exception as exc:
            errors.append(f"Row {row_idx} (Student {student_uuid_str}): {exc}")

    return imported_count, errors
