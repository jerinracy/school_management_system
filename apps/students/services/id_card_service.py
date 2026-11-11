"""Student ID Card generation and renewal service."""

import json
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.pdf.templates import generate_student_id_card_pdf
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment, StudentIDCard


def _generate_next_card_no(institution_id: UUID | str, year: int) -> str:
    prefix = f"IDC-{year}-"
    last_card = (
        StudentIDCard.objects.filter(institution_id=institution_id, card_no__startswith=prefix)
        .order_by("-card_no")
        .first()
    )
    if not last_card or not last_card.card_no[len(prefix) :].isdigit():
        seq = 1
    else:
        seq = int(last_card.card_no[len(prefix) :]) + 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def issue_or_renew_id_card(
    student_id: UUID | str,
    rfid_uid: str | None = None,
    valid_years: int = 1,
) -> tuple[StudentIDCard, bytes]:
    """Issue a new or replacement student ID card and generate printable badge PDF."""
    student = Student.objects.select_for_update().get(id=student_id)
    institution = student.institution

    enrollment = (
        StudentEnrollment.objects.filter(
            student=student,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("class_level", "section")
        .order_by("-enrollment_date")
        .first()
    )
    if not enrollment:
        raise ValidationError(f"No active enrollment found for student {student.student_id}.")

    # Deactivate existing active cards
    StudentIDCard.objects.filter(student=student, is_active=True).update(is_active=False)

    today = timezone.localdate()
    expiry_date = today.replace(year=today.year + valid_years)
    card_no = _generate_next_card_no(institution.id, today.year)

    qr_data = {
        "institution_id": str(institution.id),
        "student_id": student.student_id,
        "name": student.name_en,
        "card_no": card_no,
        "expiry": str(expiry_date),
    }

    id_card = StudentIDCard.objects.create(
        institution=institution,
        student=student,
        enrollment=enrollment,
        card_no=card_no,
        qr_payload=json.dumps(qr_data),
        rfid_uid=rfid_uid,
        issue_date=today,
        expiry_date=expiry_date,
        is_active=True,
    )

    inst_data = {
        "name_bn": institution.name_bn or institution.name,
        "name_en": institution.name,
    }
    student_data = {
        "name_bn": student.name_bn,
        "name_en": student.name_en,
        "student_id": student.student_id,
        "blood_group": student.blood_group,
        "emergency_contact_phone": student.emergency_contact_phone,
    }
    enrollment_data = {
        "class_name": enrollment.class_level.name,
        "section_name": enrollment.section.name,
        "roll_no": enrollment.roll_no,
    }
    card_dict = {
        "card_no": id_card.card_no,
    }

    pdf_bytes = generate_student_id_card_pdf(
        institution_data=inst_data,
        student_data=student_data,
        enrollment_data=enrollment_data,
        id_card_data=card_dict,
    )

    return id_card, pdf_bytes
