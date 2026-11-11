"""Integration tests for Attendance services (PunchProcessor, Recomputation, Geofence, Corrections)."""

from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone

from apps.attendance.models import (
    AttendanceEvent,
    AttendanceStatus,
    CorrectionStatus,
    DailyAttendance,
)
from apps.attendance.services import (
    decide_attendance_correction,
    mark_daily_absentees_for_date,
    process_raw_punches,
    recompute_daily_attendance,
    request_attendance_correction,
    submit_manual_attendance,
    validate_geofence,
)
from apps.devices.models import Device, RawPunch, RawPunchStatus
from apps.institutions.models import AcademicSession, Branch, Holiday, Institution
from apps.staff.models import LeaveRequest, LeaveType, Staff
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Model College", eiin="332211")


@pytest.fixture
def branch(db, institution) -> Branch:
    return Branch.objects.create(
        institution=institution,
        name="Main Campus",
        code="MAIN",
        latitude=23.810331,
        longitude=90.412521,
        geofence_radius_meters=100,
    )


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-101",
        name_en="Tahmidur Rahman",
        name_bn="তাহমিদুর রহমান",
        dob="2012-06-20",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="EMP-202",
        full_name_en="Mahmudul Hasan",
        full_name_bn="মাহমুদুল হাসান",
        dob="1987-04-18",
        gender="male",
        joining_date="2021-01-01",
    )


@pytest.fixture
def device(db, institution, branch) -> Device:
    return Device.objects.create(
        institution=institution,
        branch=branch,
        name="Main Entrance Gate",
        serial_no="TERMINAL-ATT-01",
    )


@pytest.mark.django_db
def test_punch_processor_pipeline_and_daily_recalc(institution, device, student):
    target_dt = timezone.make_aware(datetime(2026, 3, 2, 8, 10))

    # 1. Create unprocessed RawPunch resolved to student
    raw = RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="101",
        device_time=target_dt,
        status=RawPunchStatus.UNPROCESSED,
        resolved_student=student,
    )

    # 2. Process raw punches
    events_count, punches_count = process_raw_punches(batch_size=50)
    assert events_count == 1
    assert punches_count == 1

    # Verify raw punch marked processed
    raw.refresh_from_db()
    assert raw.status == RawPunchStatus.PROCESSED

    # Verify AttendanceEvent created
    event = AttendanceEvent.objects.get(raw_punch=raw)
    assert event.student == student

    # Verify DailyAttendance created
    daily = DailyAttendance.objects.get(student=student, date=target_dt.date())
    assert daily.status in [
        AttendanceStatus.PRESENT,
        AttendanceStatus.LATE,
        AttendanceStatus.HALF_DAY,
    ]
    assert daily.first_in is not None


@pytest.mark.django_db
def test_punch_processor_duplicate_suppression(institution, device, student):
    t1 = timezone.now() - timedelta(minutes=5)
    t2 = t1 + timedelta(seconds=20)  # within 60s window

    RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="101",
        device_time=t1,
        status=RawPunchStatus.UNPROCESSED,
        resolved_student=student,
    )
    RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="101",
        device_time=t2,
        status=RawPunchStatus.UNPROCESSED,
        resolved_student=student,
    )

    events_count, punches_count = process_raw_punches(batch_size=50)
    assert punches_count == 2
    assert events_count == 1  # 2nd punch was suppressed as duplicate event


@pytest.mark.django_db
def test_mark_daily_absentees_respects_holiday_and_leave(institution, student, staff):
    target_date = date(2026, 3, 2)  # Monday

    # 1. Normal day -> student is marked ABSENT
    count1 = mark_daily_absentees_for_date(institution=institution, target_date=target_date)
    assert count1 >= 1
    daily_s = DailyAttendance.objects.get(student=student, date=target_date)
    assert daily_s.status == AttendanceStatus.ABSENT

    # 2. Holiday -> on holiday date, person is marked HOLIDAY
    holiday_date = date(2026, 3, 3)
    Holiday.objects.create(
        institution=institution,
        name="Test Holiday",
        start_date=holiday_date,
        end_date=holiday_date,
    )
    mark_daily_absentees_for_date(institution=institution, target_date=holiday_date)
    daily_h = DailyAttendance.objects.get(student=student, date=holiday_date)
    assert daily_h.status == AttendanceStatus.HOLIDAY

    # 3. Approved leave for staff -> marked LEAVE
    leave_date = date(2026, 3, 4)
    session = AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_current=True,
    )
    lt = LeaveType.objects.create(institution=institution, name="Casual Leave", code="CL")
    LeaveRequest.objects.create(
        institution=institution,
        staff=staff,
        session=session,
        leave_type=lt,
        start_date=leave_date,
        end_date=leave_date,
        days_count=1,
        status="approved",
    )
    mark_daily_absentees_for_date(institution=institution, target_date=leave_date)
    daily_leave = DailyAttendance.objects.get(staff=staff, date=leave_date)
    assert daily_leave.status == AttendanceStatus.LEAVE


@pytest.mark.django_db
def test_recompute_daily_attendance_idempotency(institution, student):
    start = date(2026, 3, 1)
    end = date(2026, 3, 2)

    c1 = recompute_daily_attendance(institution=institution, start_date=start, end_date=end)
    assert c1 >= 2

    # Second run produces identical state without extra rows
    c2 = recompute_daily_attendance(institution=institution, start_date=start, end_date=end)
    assert c2 == c1
    assert DailyAttendance.objects.filter(student=student).count() == 2


@pytest.mark.django_db
def test_manual_bulk_attendance_and_correction_flow(institution, student):
    target_date = date(2026, 3, 2)
    records = [{"person_id": student.id, "status": AttendanceStatus.ABSENT, "remarks": "Sick"}]

    dailies = submit_manual_attendance(
        institution=institution,
        target_date=target_date,
        user_type="student",
        records=records,
    )
    assert len(dailies) == 1
    daily = dailies[0]
    assert daily.status == AttendanceStatus.ABSENT
    assert daily.is_overridden is True

    # Teacher submits correction request
    from apps.accounts.test_helpers import make_user

    requester = make_user(
        username="teacher_submit", phone="+8801700000051", institution=institution
    )
    approver = make_user(
        username="principal_approve", phone="+8801700000052", institution=institution
    )

    corr = request_attendance_correction(
        daily_attendance=daily,
        requested_by=requester,
        reason="Student was present in assembly",
        status_after=AttendanceStatus.PRESENT,
    )
    assert corr.approval_status == CorrectionStatus.PENDING

    # Principal approves correction
    decided = decide_attendance_correction(correction=corr, approver=approver, approved=True)
    assert decided.approval_status == CorrectionStatus.APPROVED
    daily.refresh_from_db()
    assert daily.status == AttendanceStatus.PRESENT
    assert "Correction approved" in daily.override_reason


def test_geofence_calculation():
    campus_lat = 23.810331
    campus_lon = 90.412521

    # Exact location -> 0m
    is_valid, dist = validate_geofence(
        user_lat=campus_lat,
        user_lon=campus_lon,
        center_lat=campus_lat,
        center_lon=campus_lon,
        allowed_radius_meters=100,
    )
    assert is_valid is True
    assert dist == 0.0

    # 2km away -> invalid
    far_lat = 23.830000
    far_lon = 90.412521
    is_valid_far, dist_far = validate_geofence(
        user_lat=far_lat,
        user_lon=far_lon,
        center_lat=campus_lat,
        center_lon=campus_lon,
        allowed_radius_meters=100,
    )
    assert is_valid_far is False
    assert dist_far > 1000
