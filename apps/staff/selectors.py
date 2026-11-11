"""Read queries and computed metric selectors for Staff, Workload, and Leave."""

from typing import Any

from django.db.models import Sum

from apps.academics.models import RoutineSlot
from apps.institutions.models import AcademicSession, Institution
from apps.staff.models import (
    Department,
    LeaveRequest,
    LeaveRequestStatus,
    Staff,
    StaffStatus,
    TeacherAssignment,
)


def get_teacher_workload_summary(
    teacher: Staff,
    session: AcademicSession | None = None,
) -> dict[str, Any]:
    """Compute comprehensive teaching workload metrics for an instructor."""
    assignments_qs = TeacherAssignment.objects.filter(teacher=teacher).select_related(
        "subject", "section__class_level", "session"
    )
    if session:
        assignments_qs = assignments_qs.filter(session=session)

    routine_qs = RoutineSlot.objects.filter(teacher_staff=teacher)
    if session:
        routine_qs = routine_qs.filter(section__session=session)

    total_assigned_periods = assignments_qs.aggregate(total=Sum("periods_per_week"))["total"] or 0
    total_routine_slots_per_week = routine_qs.count()
    unique_subjects = assignments_qs.values_list("subject_id", flat=True).distinct().count()
    unique_sections = assignments_qs.values_list("section_id", flat=True).distinct().count()

    assignment_details = []
    for a in assignments_qs:
        assignment_details.append(
            {
                "id": str(a.id),
                "subject_name": a.subject.name_en,
                "class_name": a.section.class_level.name,
                "section_name": a.section.name,
                "session_name": a.session.name,
                "periods_per_week": a.periods_per_week,
                "is_primary": a.is_primary_teacher,
            }
        )

    return {
        "teacher_id": str(teacher.id),
        "teacher_name": teacher.full_name_en,
        "employee_id": teacher.employee_id,
        "total_assigned_periods": total_assigned_periods,
        "total_routine_slots_per_week": total_routine_slots_per_week,
        "unique_subjects_count": unique_subjects,
        "unique_sections_count": unique_sections,
        "assignments": assignment_details,
    }


def get_department_staff_roster(department: Department) -> list[dict[str, Any]]:
    """Retrieve full active employee roster for a department sorted by seniority rank."""
    members = (
        Staff.objects.filter(department=department, status=StaffStatus.ACTIVE)
        .select_related("designation")
        .order_by("designation__rank_order", "full_name_en")
    )
    return [
        {
            "id": str(m.id),
            "employee_id": m.employee_id,
            "full_name_en": m.full_name_en,
            "full_name_bn": m.full_name_bn,
            "designation": m.designation.title if m.designation else "",
            "phone": m.phone,
            "email": m.email,
            "staff_type": m.staff_type,
            "is_mpo": m.is_mpo,
        }
        for m in members
    ]


def get_staff_leave_calendar(
    institution: Institution,
    session: AcademicSession,
    start_date: Any,
    end_date: Any,
) -> list[dict[str, Any]]:
    """Retrieve approved staff leaves in a given date range for institutional scheduling."""
    leaves = (
        LeaveRequest.objects.filter(
            institution=institution,
            session=session,
            status=LeaveRequestStatus.APPROVED,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        .select_related("staff__designation", "leave_type")
        .order_by("start_date")
    )

    return [
        {
            "leave_id": str(lv.id),
            "staff_id": str(lv.staff.id),
            "staff_name": lv.staff.full_name_en,
            "designation": lv.staff.designation.title if lv.staff.designation else "",
            "leave_type": lv.leave_type.code,
            "start_date": lv.start_date.isoformat(),
            "end_date": lv.end_date.isoformat(),
            "days_count": float(lv.days_count),
        }
        for lv in leaves
    ]
