"""API integration tests for Attendance endpoints, simulator, bulk actions, and mobile check-in."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section, Subject
from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.attendance.models import (
    AttendancePolicy,
    AttendanceStatus,
    CorrectionStatus,
    DailyAttendance,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.staff.models import Staff
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka Model School", eiin="135790")


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(name_en="Rajshahi Model School", eiin="246800")


@pytest.fixture
def admin_user(db, institution) -> User:
    user = make_user(
        username="att_admin",
        institution=institution,
        user_type=UserType.STAFF,
        phone="+8801700000001",
    )
    role, _ = Role.objects.get_or_create(institution=institution, code="att_admin")
    ct = ContentType.objects.get_for_model(AttendancePolicy)
    p_view, _ = Permission.objects.get_or_create(
        codename="view", content_type=ct, defaults={"name": "Can view attendance"}
    )
    p_manage, _ = Permission.objects.get_or_create(
        codename="manage", content_type=ct, defaults={"name": "Can manage attendance"}
    )
    role.permissions.add(p_view, p_manage)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-999",
        name_en="Nabil Karim",
        name_bn="নাবিল করিম",
        dob="2012-08-14",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="TCH-888",
        full_name_en="Anisur Rahman",
        full_name_bn="আনিসুর রহমান",
        dob="1986-07-22",
        gender="male",
        joining_date="2020-01-01",
    )


@pytest.fixture
def academic_setup(db, institution):
    session = AcademicSession.objects.create(
        institution=institution,
        name="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    branch = Branch.objects.create(institution=institution, name="Main", code="MN")
    shift = Shift.objects.create(
        institution=institution,
        branch=branch,
        name="Morning",
        start_time="08:00:00",
        end_time="14:00:00",
    )
    class_level = ClassLevel.objects.create(
        institution=institution, name="Class 6", code="C6", order=6
    )
    section = Section.objects.create(
        institution=institution, session=session, class_level=class_level, shift=shift, name="A"
    )
    subject = Subject.objects.create(institution=institution, name_en="English", code="ENG-6")
    return section, subject


@pytest.mark.django_db
def test_policy_crud_and_simulation(admin_user, institution):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # 1. Create policy
    create_payload = {
        "name": "Standard High School Policy",
        "user_type": "student",
        "start_time": "08:00:00",
        "end_time": "14:00:00",
        "grace_minutes": 15,
        "late_threshold_minutes": 45,
    }
    resp = client.post("/api/v1/attendance/policies/", create_payload)
    assert resp.status_code == status.HTTP_201_CREATED
    policy_id = resp.data["id"]

    # 2. Simulate policy
    sim_payload = {
        "target_date": "2026-03-02",
        "punches": ["2026-03-02T08:25:00+06:00", "2026-03-02T14:05:00+06:00"],
    }
    sim_resp = client.post(
        f"/api/v1/attendance/policies/{policy_id}/simulate/", sim_payload, format="json"
    )
    assert sim_resp.status_code == status.HTTP_200_OK
    assert sim_resp.data["status"] == AttendanceStatus.LATE
    assert sim_resp.data["minutes_late"] == 25


@pytest.mark.django_db
def test_daily_attendance_bulk_manual_and_recompute(admin_user, institution, student):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    target_date = "2026-03-02"
    bulk_payload = {
        "date": target_date,
        "user_type": "student",
        "records": [
            {
                "person_id": str(student.id),
                "status": AttendanceStatus.PRESENT,
                "remarks": "Assembly roll call",
            }
        ],
    }
    resp = client.post("/api/v1/attendance/daily/bulk-manual/", bulk_payload, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    # Verify created daily record
    daily = DailyAttendance.objects.get(student=student, date=target_date)
    assert daily.status == AttendanceStatus.PRESENT
    assert daily.is_overridden is True

    # Recompute endpoint
    recompute_payload = {
        "start_date": "2026-03-01",
        "end_date": "2026-03-03",
        "user_type": "all",
    }
    recomp_resp = client.post(
        "/api/v1/attendance/daily/recompute/", recompute_payload, format="json"
    )
    assert recomp_resp.status_code == status.HTTP_200_OK
    assert "recomputed_count" in recomp_resp.data


@pytest.mark.django_db
def test_period_attendance_bulk_submit(admin_user, institution, student, academic_setup):
    section, subject = academic_setup
    client = APIClient()
    client.force_authenticate(user=admin_user)

    payload = {
        "date": "2026-03-02",
        "section_id": str(section.id),
        "subject_id": str(subject.id),
        "records": [
            {"student_id": str(student.id), "status": "present", "remarks": "Active participation"}
        ],
    }
    resp = client.post("/api/v1/attendance/periods/bulk-submit/", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert "Successfully saved 1" in resp.data["message"]


@pytest.mark.django_db
def test_attendance_correction_workflow_api(admin_user, institution, student):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    daily = DailyAttendance.objects.create(
        institution=institution,
        student=student,
        user_type="student",
        date=date(2026, 3, 2),
        status=AttendanceStatus.ABSENT,
    )

    # 1. Request correction
    create_payload = {
        "daily_attendance_id": str(daily.id),
        "reason": "Student was attending sports competition",
        "status_after": AttendanceStatus.PRESENT,
    }
    resp = client.post("/api/v1/attendance/corrections/", create_payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    correction_id = resp.data["id"]

    # 2. Approve correction
    decide_payload = {"approved": True}
    decide_resp = client.post(
        f"/api/v1/attendance/corrections/{correction_id}/decide/", decide_payload, format="json"
    )
    assert decide_resp.status_code == status.HTTP_200_OK
    assert decide_resp.data["approval_status"] == CorrectionStatus.APPROVED

    daily.refresh_from_db()
    assert daily.status == AttendanceStatus.PRESENT


@pytest.mark.django_db
def test_mobile_checkin_geofence_api(institution):
    user = make_user(username="mobile_staff", institution=institution, user_type=UserType.STAFF)
    _staff = Staff.objects.create(
        institution=institution,
        user=user,
        employee_id="STF-01",
        full_name_en="Salim Khan",
        dob="1990-01-01",
        gender="male",
        joining_date="2022-01-01",
    )
    # Configure campus policy with exact geofence
    AttendancePolicy.objects.create(
        institution=institution,
        name="Staff Campus Policy",
        user_type="staff",
        geofence_latitude=Decimal("23.810331"),
        geofence_longitude=Decimal("90.412521"),
        geofence_radius_meters=100,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    # Check-in at campus coordinates -> 201 Created
    checkin_payload = {
        "latitude": "23.810331",
        "longitude": "90.412521",
        "accuracy_meters": 5.0,
        "device_info": "Samsung S23",
    }
    resp = client.post("/api/v1/attendance/mobile-checkin/checkin/", checkin_payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["is_within_geofence"] is True

    # Check-in 5km away -> 400 Bad Request
    far_payload = {
        "latitude": "23.890000",
        "longitude": "90.412521",
        "accuracy_meters": 5.0,
    }
    resp_far = client.post("/api/v1/attendance/mobile-checkin/checkin/", far_payload, format="json")
    assert resp_far.status_code == status.HTTP_400_BAD_REQUEST
    assert resp_far.data["is_within_geofence"] is False
