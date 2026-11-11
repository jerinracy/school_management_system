"""Automatic roll numbering services."""

from uuid import UUID

from django.db import transaction

from apps.academics.models import Section
from apps.institutions.models import AcademicSession
from apps.students.models import EnrollmentStatus, StudentEnrollment


@transaction.atomic
def auto_assign_section_rolls(
    section_id: UUID | str,
    session_id: UUID | str,
    strategy: str = "name_en",
) -> list[StudentEnrollment]:
    """Re-sequence roll numbers for all active students in a section (1..N).

    Strategies:
    - 'name_en': Alphabetical by English name
    - 'name_bn': Alphabetical by Bangla name
    - 'student_id': Ascending order of student_id
    """
    section = Section.objects.get(id=section_id)
    session = AcademicSession.objects.get(id=session_id)

    enrollments_qs = (
        StudentEnrollment.objects.filter(
            section=section,
            session=session,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("student")
        .select_for_update()
    )

    if strategy == "name_bn":
        ordered_enrollments = sorted(enrollments_qs, key=lambda e: e.student.name_bn)
    elif strategy == "student_id":
        ordered_enrollments = sorted(enrollments_qs, key=lambda e: e.student.student_id)
    else:  # default 'name_en'
        ordered_enrollments = sorted(enrollments_qs, key=lambda e: e.student.name_en.lower())

    # Step 1: Assign temporary roll offset to avoid violating unique constraint during reassignment
    offset = 100000
    for idx, enrollment in enumerate(ordered_enrollments):
        enrollment.roll_no = offset + idx + 1
        enrollment.save(update_fields=["roll_no"])

    # Step 2: Assign final 1..N sequential rolls
    for idx, enrollment in enumerate(ordered_enrollments):
        enrollment.roll_no = idx + 1
        enrollment.save(update_fields=["roll_no"])

    return ordered_enrollments
