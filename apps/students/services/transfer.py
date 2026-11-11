"""Transfer certificate and testimonial generation services."""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.pdf.templates import generate_testimonial_pdf, generate_transfer_certificate_pdf
from apps.students.models import (
    EnrollmentStatus,
    Student,
    StudentEnrollment,
    StudentStatus,
    Testimonial,
    TransferCertificate,
)


def _generate_next_tc_number(institution_id: UUID | str, year: int) -> str:
    prefix = f"TC-{year}-"
    last_tc = (
        TransferCertificate.objects.filter(
            institution_id=institution_id, tc_number__startswith=prefix
        )
        .order_by("-tc_number")
        .first()
    )
    if not last_tc or not last_tc.tc_number[len(prefix) :].isdigit():
        seq = 1
    else:
        seq = int(last_tc.tc_number[len(prefix) :]) + 1
    return f"{prefix}{seq:05d}"


def _generate_next_testimonial_no(institution_id: UUID | str, year: int) -> str:
    prefix = f"TST-{year}-"
    last_tst = (
        Testimonial.objects.filter(institution_id=institution_id, certificate_no__startswith=prefix)
        .order_by("-certificate_no")
        .first()
    )
    if not last_tst or not last_tst.certificate_no[len(prefix) :].isdigit():
        seq = 1
    else:
        seq = int(last_tst.certificate_no[len(prefix) :]) + 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def issue_transfer_certificate(
    student_id: UUID | str,
    reason: str,
    conduct_remarks: str = "Satisfactory",
    dues_cleared: bool = True,
    approved_by: User | None = None,
) -> TransferCertificate:
    """Issue official Transfer Certificate, close active enrollment, and set student status to TRANSFERRED."""
    student = Student.objects.select_for_update().get(id=student_id)
    institution = student.institution

    if student.status == StudentStatus.TRANSFERRED:
        raise ValidationError(f"Student {student.student_id} is already transferred.")

    enrollment = (
        StudentEnrollment.objects.filter(
            student=student,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("class_level", "section", "session")
        .order_by("-enrollment_date")
        .first()
    )
    if not enrollment:
        raise ValidationError(f"No active enrollment found for student {student.student_id}.")

    today = timezone.localdate()
    tc_number = _generate_next_tc_number(institution.id, today.year)

    tc = TransferCertificate.objects.create(
        institution=institution,
        student=student,
        enrollment=enrollment,
        tc_number=tc_number,
        issue_date=today,
        reason=reason,
        conduct_remarks=conduct_remarks,
        dues_cleared=dues_cleared,
        approved_by=approved_by,
    )

    # Generate PDF
    inst_data = {
        "name_bn": institution.name_bn or institution.name,
        "name_en": institution.name,
        "eiin": institution.eiin,
        "address": getattr(institution, "address", ""),
        "phone": getattr(institution, "phone", ""),
    }
    student_data = {
        "name_bn": student.name_bn,
        "name_en": student.name_en,
        "student_id": student.student_id,
        "dob": student.dob,
        "birth_reg_no": student.birth_reg_no,
    }
    enrollment_data = {
        "class_name": enrollment.class_level.name,
        "section_name": enrollment.section.name,
        "roll_no": enrollment.roll_no,
        "session_name": enrollment.session.name,
    }
    tc_data = {
        "tc_number": tc.tc_number,
        "issue_date": str(tc.issue_date),
        "reason": tc.reason,
        "conduct_remarks": tc.conduct_remarks,
        "dues_cleared": tc.dues_cleared,
    }

    pdf_bytes = generate_transfer_certificate_pdf(
        institution_data=inst_data,
        student_data=student_data,
        enrollment_data=enrollment_data,
        tc_data=tc_data,
    )
    tc.pdf_file.save(f"{tc_number}.pdf", ContentFile(pdf_bytes), save=True)

    # Update statuses
    student.status = StudentStatus.TRANSFERRED
    student.save(update_fields=["status"])

    enrollment.status = EnrollmentStatus.TRANSFERRED
    enrollment.save(update_fields=["status"])

    return tc


@transaction.atomic
def issue_testimonial(
    student_id: UUID | str,
    exam_name: str,
    passing_year: int,
    gpa: Decimal | float,
    character: str = "Good",
    approved_by: User | None = None,
) -> Testimonial:
    """Issue official Testimonial / Character Certificate with rendered PDF."""
    student = Student.objects.select_for_update().get(id=student_id)
    institution = student.institution

    enrollment = (
        StudentEnrollment.objects.filter(student=student, is_deleted=False)
        .select_related("class_level", "section", "session")
        .order_by("-enrollment_date")
        .first()
    )
    if not enrollment:
        raise ValidationError(f"No enrollment history found for student {student.student_id}.")

    today = timezone.localdate()
    cert_no = _generate_next_testimonial_no(institution.id, today.year)

    testimonial = Testimonial.objects.create(
        institution=institution,
        student=student,
        enrollment=enrollment,
        certificate_no=cert_no,
        issue_date=today,
        exam_name=exam_name,
        passing_year=passing_year,
        gpa=Decimal(str(gpa)),
        character=character,
    )

    inst_data = {
        "name_bn": institution.name_bn or institution.name,
        "name_en": institution.name,
        "eiin": institution.eiin,
        "address": institution.address,
    }
    student_data = {
        "name_bn": student.name_bn,
        "name_en": student.name_en,
        "student_id": student.student_id,
    }
    enrollment_data = {
        "class_name": enrollment.class_level.name,
        "section_name": enrollment.section.name,
        "roll_no": enrollment.roll_no,
        "session_name": enrollment.session.name,
    }
    testimonial_data = {
        "certificate_no": testimonial.certificate_no,
        "issue_date": str(testimonial.issue_date),
        "exam_name": testimonial.exam_name,
        "passing_year": testimonial.passing_year,
        "gpa": str(testimonial.gpa),
        "character": testimonial.character,
    }

    pdf_bytes = generate_testimonial_pdf(
        institution_data=inst_data,
        student_data=student_data,
        enrollment_data=enrollment_data,
        testimonial_data=testimonial_data,
    )
    testimonial.pdf_file.save(f"{cert_no}.pdf", ContentFile(pdf_bytes), save=True)

    return testimonial
