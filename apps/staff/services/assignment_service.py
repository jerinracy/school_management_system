"""Teacher assignments and section class teacher synchronization."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.academics.models import Section, Subject
from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import Staff, TeacherAssignment


def assign_teacher_to_subject(
    institution: Institution,
    teacher: Staff,
    subject: Subject,
    section: Section,
    session: AcademicSession,
    periods_per_week: int = 0,
    is_primary_teacher: bool = False,
) -> TeacherAssignment:
    """Assign an instructor to deliver a curriculum subject in an academic section."""
    if (
        teacher.institution_id != institution.id
        or subject.institution_id != institution.id
        or section.institution_id != institution.id
        or session.institution_id != institution.id
    ):
        raise ValidationError("All entities must belong to the specified institution.")

    with transaction.atomic():
        if is_primary_teacher:
            TeacherAssignment.objects.filter(
                subject=subject,
                section=section,
                session=session,
                is_primary_teacher=True,
            ).update(is_primary_teacher=False)

        assignment, _ = TeacherAssignment.objects.update_or_create(
            institution=institution,
            teacher=teacher,
            subject=subject,
            section=section,
            session=session,
            defaults={
                "periods_per_week": periods_per_week,
                "is_primary_teacher": is_primary_teacher,
            },
        )

    return assignment


def sync_academics_section_class_teacher(section: Section, staff: Staff | None) -> Section:
    """Synchronize class teacher assignment between staff profile and academic section."""
    section.teacher_staff = staff
    if staff and staff.user:
        section.teacher_user = staff.user
    elif staff is None:
        section.teacher_user = None
    section.save(update_fields=["teacher_staff", "teacher_user"])
    return section
