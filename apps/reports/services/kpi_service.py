"""Role-based Dashboard KPI service with short-TTL caching."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.db.models import Count, Q, Sum

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import User, UserType
from apps.attendance.models import (
    AttendanceCorrection,
    AttendanceStatus,
    CorrectionStatus,
    DailyAttendance,
)
from apps.devices.models import Device, DeviceStatus
from apps.exams.models import Exam
from apps.fees.models import Invoice, InvoiceStatus, Payment, PaymentStatus
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import EnrollmentStatus, StudentEnrollment

KPI_CACHE_TTL_SECONDS = 60

FINANCIAL_KPI_ROLES = {
    UserType.SUPERADMIN,
    UserType.ADMIN,
    UserType.HEAD_TEACHER,
    UserType.ASSISTANT_HEAD,
    UserType.ACCOUNTANT,
}


def _resolve_role_variant(user: User) -> str:
    if user.user_type in {
        UserType.SUPERADMIN,
        UserType.ADMIN,
        UserType.HEAD_TEACHER,
        UserType.ASSISTANT_HEAD,
    }:
        return "executive"
    if user.user_type == UserType.ACCOUNTANT:
        return "accountant"
    if user.user_type == UserType.TEACHER:
        return "teacher"
    return "staff"


def get_dashboard_kpis(
    *,
    institution: Institution,
    user: User,
    target_date: date | None = None,
) -> dict[str, Any]:
    """Compute role-scoped dashboard KPIs for an institution with 60s caching."""
    day = target_date or date.today()
    role_variant = _resolve_role_variant(user)
    cache_key = f"reports:kpis:{institution.id}:{role_variant}:{day.isoformat()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return dict(cached)

    # 1. Today's attendance by user_type
    att_rows = (
        DailyAttendance.objects.filter(
            institution=institution,
            is_deleted=False,
            date=day,
        )
        .values("user_type", "status")
        .annotate(total=Count("id"))
    )
    attendance_summary: dict[str, dict[str, int]] = {
        "student": {s.value: 0 for s in AttendanceStatus},
        "staff": {s.value: 0 for s in AttendanceStatus},
    }
    for row in att_rows:
        ut = row["user_type"]
        st = row["status"]
        if ut in attendance_summary:
            attendance_summary[ut][st] = row["total"]

    # 2. Device status counts
    device_rows = (
        Device.objects.filter(institution=institution, is_deleted=False, is_active=True)
        .values("status")
        .annotate(total=Count("id"))
    )
    devices_summary = {s.value: 0 for s in DeviceStatus}
    for row in device_rows:
        devices_summary[row["status"]] = row["total"]

    # 3. Upcoming exams (next 30 days) & pending attendance corrections
    upcoming_exams_count = Exam.objects.filter(
        institution=institution,
        is_active=True,
        start_date__gte=day,
        start_date__lte=day + timedelta(days=30),
    ).count()
    pending_corrections = AttendanceCorrection.objects.filter(
        institution=institution,
        approval_status=CorrectionStatus.PENDING,
    ).count()

    # 4. Institutional Headcount & Shift Distribution
    active_enrollments = StudentEnrollment.objects.filter(
        institution=institution,
        is_deleted=False,
        status=EnrollmentStatus.ACTIVE,
    )
    total_students = active_enrollments.count()
    morning_shift_students = active_enrollments.filter(
        Q(shift__name__iexact="morning")
        | (Q(shift__isnull=True) & Q(section__shift__name__iexact="morning"))
    ).count()
    day_shift_students = active_enrollments.filter(
        Q(shift__name__iexact="day")
        | (Q(shift__isnull=True) & Q(section__shift__name__iexact="day"))
    ).count()

    total_teachers = Staff.objects.filter(
        institution=institution,
        is_deleted=False,
        status="active",
        staff_type="teacher",
    ).count()
    total_office_staff = (
        Staff.objects.filter(
            institution=institution,
            is_deleted=False,
            status="active",
        )
        .exclude(staff_type="teacher")
        .count()
    )

    total_classes = ClassLevel.objects.filter(
        institution=institution,
    ).count()
    total_sections = Section.objects.filter(
        institution=institution,
    ).count()

    # 5. Today's attendance percentage rates
    student_present = (
        attendance_summary["student"]["present"] + attendance_summary["student"]["late"]
    )
    student_att_rate = (
        round((student_present / total_students) * 100, 1) if total_students > 0 else 0.0
    )

    total_staff = total_teachers + total_office_staff
    staff_present = attendance_summary["staff"]["present"] + attendance_summary["staff"]["late"]
    staff_att_rate = round((staff_present / total_staff) * 100, 1) if total_staff > 0 else 0.0

    payload: dict[str, Any] = {
        "date": day.isoformat(),
        "role_variant": role_variant,
        "headcount": {
            "total_teachers": total_teachers,
            "total_office_staff": total_office_staff,
            "total_students": total_students,
            "morning_shift_students": morning_shift_students,
            "day_shift_students": day_shift_students,
            "total_classes": total_classes,
            "total_sections": total_sections,
        },
        "attendance": attendance_summary,
        "attendance_rates": {
            "student_present_pct": student_att_rate,
            "staff_present_pct": staff_att_rate,
        },
        "devices": devices_summary,
        "upcoming_exams_count": upcoming_exams_count,
        "pending_approvals": {
            "attendance_corrections": pending_corrections,
        },
    }

    # 4. Financial KPIs (restricted to executive & accountant roles)
    if user.user_type in FINANCIAL_KPI_ROLES or user.is_superuser:
        collected_today = Payment.objects.filter(
            institution=institution,
            is_deleted=False,
            status=PaymentStatus.SUCCESSFUL,
            payment_date__date=day,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        total_dues = Invoice.objects.filter(
            institution=institution,
            is_deleted=False,
            status__in=[
                InvoiceStatus.ISSUED,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.OVERDUE,
            ],
        ).aggregate(total=Sum("due_amount"))["total"] or Decimal("0.00")

        payload["finance"] = {
            "currency": "BDT",
            "collected_today": f"{collected_today:.2f}",
            "total_outstanding_dues": f"{total_dues:.2f}",
        }

    cache.set(cache_key, payload, KPI_CACHE_TTL_SECONDS)
    return payload
