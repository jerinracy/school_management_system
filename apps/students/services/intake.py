"""Student intake service: converts admitted admission applications into permanent Student profiles."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Section
from apps.admissions.models import Application, ApplicationStatus
from apps.institutions.models import AcademicSession
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment, StudentStatus


def generate_next_student_id(
    institution_id: UUID | str, session_year: str, class_order: int
) -> str:
    """Generate next sequential student ID.

    Format: {YEAR}{CLASS_CODE:02d}{SEQ:04d}, e.g. 2026100001
    """
    prefix = f"{session_year}{class_order:02d}"
    last_student = (
        Student.objects.filter(institution_id=institution_id, student_id__startswith=prefix)
        .order_by("-student_id")
        .first()
    )
    if not last_student or not last_student.student_id[len(prefix) :].isdigit():
        seq = 1
    else:
        seq = int(last_student.student_id[len(prefix) :]) + 1

    return f"{prefix}{seq:04d}"


@transaction.atomic
def admit_from_application(
    application_id: UUID | str,
    section_id: UUID | str,
    roll_no: int,
    session_id: UUID | str | None = None,
    student_id: str | None = None,
) -> tuple[Student, StudentEnrollment]:
    """Convert an admitted Application into a permanent Student and StudentEnrollment."""
    application = (
        Application.objects.select_related("circular", "circular__class_level", "circular__session")
        .select_for_update()
        .get(id=application_id)
    )

    if application.status != ApplicationStatus.ADMITTED:
        raise ValidationError(
            f"Application status must be ADMITTED to enroll as student (currently {application.status})."
        )

    if hasattr(application, "student_profile") and application.student_profile is not None:
        raise ValidationError(
            f"Student profile already exists for application {application.application_no}."
        )

    circular = application.circular
    institution = circular.institution
    target_session = AcademicSession.objects.get(id=session_id) if session_id else circular.session
    section = Section.objects.select_related("class_level").get(
        id=section_id, institution=institution
    )
    class_level = section.class_level

    # Check roll uniqueness in section
    if StudentEnrollment.objects.filter(
        institution=institution,
        session=target_session,
        section=section,
        roll_no=roll_no,
        is_deleted=False,
    ).exists():
        raise ValidationError(
            f"Roll number {roll_no} is already assigned in section '{section.name}' for session '{target_session.name}'."
        )

    # Determine student ID
    if not student_id:
        student_id = generate_next_student_id(
            institution_id=institution.id,
            session_year=target_session.name,
            class_order=class_level.order,
        )

    today = timezone.localdate()

    # Map quota from application
    quota = "none"
    if application.quota_rule:
        quota = str(application.quota_rule.quota_type)

    student = Student.objects.create(
        institution=institution,
        student_id=student_id,
        name_bn=application.name_bn,
        name_en=application.name_en,
        dob=application.dob,
        gender=application.gender,
        birth_reg_no=application.birth_reg_no,
        present_address=application.present_address,
        permanent_address=application.permanent_address,
        status=StudentStatus.ACTIVE,
        admission_date=today,
        quota_category=quota,
        emergency_contact_name=application.guardian_name,
        emergency_contact_phone=application.guardian_phone,
        application=application,
    )

    enrollment = StudentEnrollment.objects.create(
        institution=institution,
        student=student,
        session=target_session,
        class_level=class_level,
        section=section,
        shift=section.shift,
        roll_no=roll_no,
        enrollment_date=today,
        status=EnrollmentStatus.ACTIVE,
    )

    return student, enrollment
