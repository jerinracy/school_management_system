"""Unit tests for Attendance models and database constraints."""

from datetime import date, time

import pytest
from django.db import IntegrityError, transaction

from apps.attendance.models import (
    AttendanceCorrection,
    AttendancePolicy,
    AttendanceStatus,
    CorrectionStatus,
    DailyAttendance,
    MultiPunchMode,
)
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Collegiate", eiin="112233")


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-001",
        name_en="Farhan Ahmed",
        name_bn="ফারহান আহমেদ",
        dob="2012-05-10",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="TCH-001",
        full_name_en="Rafiqul Islam",
        full_name_bn="রফিকুল ইসলাম",
        dob="1985-03-12",
        gender="male",
        joining_date="2020-01-01",
    )


@pytest.mark.django_db
def test_attendance_policy_creation_and_uniqueness(institution):
    policy = AttendancePolicy.objects.create(
        institution=institution,
        name="Morning Students Policy",
        user_type="student",
        start_time=time(8, 0),
        end_time=time(14, 0),
        grace_minutes=15,
        multi_punch_mode=MultiPunchMode.ENTRY_EXIT,
    )
    assert policy.id is not None
    assert "Morning Students Policy" in str(policy)

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            AttendancePolicy.objects.create(
                institution=institution,
                name="Morning Students Policy",
                user_type="student",
            )


@pytest.mark.django_db
def test_daily_attendance_uniqueness_per_student_date(institution, student):
    today = date(2026, 3, 1)
    daily = DailyAttendance.objects.create(
        institution=institution,
        student=student,
        user_type="student",
        date=today,
        status=AttendanceStatus.PRESENT,
    )
    assert daily.id is not None
    assert str(daily) == f"{today}: Farhan Ahmed (present)"

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            DailyAttendance.objects.create(
                institution=institution,
                student=student,
                user_type="student",
                date=today,
                status=AttendanceStatus.LATE,
            )


@pytest.mark.django_db
def test_daily_attendance_uniqueness_per_staff_date(institution, staff):
    today = date(2026, 3, 1)
    daily = DailyAttendance.objects.create(
        institution=institution,
        staff=staff,
        user_type="staff",
        date=today,
        status=AttendanceStatus.PRESENT,
    )
    assert daily.id is not None

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            DailyAttendance.objects.create(
                institution=institution,
                staff=staff,
                user_type="staff",
                date=today,
                status=AttendanceStatus.LATE,
            )


@pytest.mark.django_db
def test_attendance_correction_model(institution, student):
    daily = DailyAttendance.objects.create(
        institution=institution,
        student=student,
        user_type="student",
        date=date(2026, 3, 1),
        status=AttendanceStatus.ABSENT,
    )
    from apps.accounts.test_helpers import make_user

    user = make_user(username="teacher1", institution=institution)

    correction = AttendanceCorrection.objects.create(
        institution=institution,
        daily_attendance=daily,
        requested_by=user,
        reason="Machine offline during morning gate entry",
        status_before=AttendanceStatus.ABSENT,
        status_after=AttendanceStatus.PRESENT,
    )
    assert correction.approval_status == CorrectionStatus.PENDING
    assert "pending" in str(correction)
