"""Unit tests for Biometric Services (Ingestion, Enrollment, Consent, Commands)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.devices.models import (
    BiometricEnrollment,
    CommandStatus,
    Device,
    DeviceProtocol,
    DeviceStatus,
    DeviceUserMap,
    RawPunch,
    RawPunchStatus,
)
from apps.devices.services import (
    enroll_user_on_device,
    ingest_raw_punches,
    record_biometric_consent,
    resolve_unmapped_punch,
    withdraw_biometric_consent,
)
from apps.guardians.models import Guardian
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka High", eiin="554433")


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-002",
        name_en="Tareq Aziz",
        name_bn="তারেক আজিজ",
        dob="2012-01-01",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def guardian(db, institution) -> Guardian:
    return Guardian.objects.create(
        institution=institution,
        name_en="Azizul Haque",
        phone="+8801711223344",
        relation_default="father",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="EMP-100",
        full_name_en="Nazmul Hossain",
        full_name_bn="নাজমুল হোসেন",
        dob="1988-02-15",
        gender="male",
        joining_date="2021-01-01",
    )


@pytest.fixture
def device(db, institution) -> Device:
    return Device.objects.create(
        institution=institution,
        name="Main Entrance Terminal",
        serial_no="TERMINAL-01",
        vendor="ZKTeco",
        protocol=DeviceProtocol.PUSH_ADMS,
    )


@pytest.mark.django_db
def test_ingest_raw_punches_mapped_and_unmapped(institution, device, student, staff):
    # Setup mappings
    DeviceUserMap.objects.create(
        institution=institution,
        device=device,
        device_user_id="101",
        user_type="student",
        student=student,
    )
    DeviceUserMap.objects.create(
        institution=institution,
        device=device,
        device_user_id="201",
        user_type="staff",
        staff=staff,
    )

    t1 = timezone.now() - timedelta(minutes=10)
    t2 = timezone.now() - timedelta(minutes=5)
    t3 = timezone.now() - timedelta(minutes=2)

    punches = [
        {"raw_user_id": "101", "device_time": t1, "punch_state": "0"},
        {"raw_user_id": "201", "device_time": t2, "punch_state": "0"},
        {"raw_user_id": "999", "device_time": t3, "punch_state": "0"},  # Unmapped
    ]

    created, duplicates, unmapped = ingest_raw_punches(device, punches)
    assert created == 3
    assert duplicates == 0
    assert unmapped == 1

    # Verify device status
    device.refresh_from_db()
    assert device.status == DeviceStatus.ONLINE
    assert device.last_seen is not None

    # Check student punch
    p_student = RawPunch.objects.get(device=device, raw_user_id="101")
    assert p_student.status == RawPunchStatus.UNPROCESSED
    assert p_student.resolved_student == student

    # Check staff punch
    p_staff = RawPunch.objects.get(device=device, raw_user_id="201")
    assert p_staff.status == RawPunchStatus.UNPROCESSED
    assert p_staff.resolved_staff == staff

    # Check unmapped punch
    p_unmapped = RawPunch.objects.get(device=device, raw_user_id="999")
    assert p_unmapped.status == RawPunchStatus.UNMAPPED
    assert p_unmapped.resolved_student is None
    assert p_unmapped.resolved_staff is None


@pytest.mark.django_db
def test_ingest_raw_punches_duplicate_prevention(institution, device, student):
    DeviceUserMap.objects.create(
        institution=institution,
        device=device,
        device_user_id="101",
        user_type="student",
        student=student,
    )
    t1 = timezone.now() - timedelta(minutes=10)
    punches = [{"raw_user_id": "101", "device_time": t1, "punch_state": "0"}]

    created, duplicates, unmapped = ingest_raw_punches(device, punches)
    assert created == 1
    assert duplicates == 0

    # Ingest again with the exact same punch
    created2, duplicates2, unmapped2 = ingest_raw_punches(device, punches)
    assert created2 == 0
    assert duplicates2 == 1
    assert RawPunch.objects.filter(device=device, raw_user_id="101").count() == 1


@pytest.mark.django_db
def test_resolve_unmapped_punch(institution, device, student):
    t1 = timezone.now() - timedelta(minutes=10)
    t2 = timezone.now() - timedelta(minutes=5)

    p1 = RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="PIN_UNKNOWN",
        device_time=t1,
        status=RawPunchStatus.UNMAPPED,
    )
    p2 = RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="PIN_UNKNOWN",
        device_time=t2,
        status=RawPunchStatus.UNMAPPED,
    )

    resolved = resolve_unmapped_punch(raw_punch=p1, student=student, create_mapping=True)
    assert resolved.status == RawPunchStatus.UNPROCESSED
    assert resolved.resolved_student == student

    # Other unmapped punch with same PIN should also be resolved
    p2.refresh_from_db()
    assert p2.status == RawPunchStatus.UNPROCESSED
    assert p2.resolved_student == student

    # User map should have been created
    mapping = DeviceUserMap.objects.get(device=device, device_user_id="PIN_UNKNOWN")
    assert mapping.student == student


@pytest.mark.django_db
def test_biometric_consent_and_withdrawal(institution, student, guardian, device):
    # Student requires guardian
    with pytest.raises(ValueError, match="Guardian consent is mandatory"):
        record_biometric_consent(
            institution=institution,
            subject_type="student",
            student=student,
            guardian=None,
        )

    consent = record_biometric_consent(
        institution=institution,
        subject_type="student",
        student=student,
        guardian=guardian,
    )
    assert consent.is_active is True

    # Enroll user
    user_map, cmd = enroll_user_on_device(
        device=device,
        user_pin="301",
        user_name="Tareq",
        student=student,
        consent=consent,
    )
    assert user_map.device_user_id == "301"
    assert cmd.command_type == "enroll_user"
    assert cmd.status == CommandStatus.QUEUED

    enrollment = BiometricEnrollment.objects.get(device=device, device_user_id="301")
    assert enrollment.is_active is True

    # Withdraw consent
    withdraw_biometric_consent(consent)
    consent.refresh_from_db()
    assert consent.is_active is False
    assert consent.withdrawn_at is not None

    enrollment.refresh_from_db()
    assert enrollment.is_active is False

    # Deletion command should be queued
    del_cmd = device.commands.filter(command_type="delete_user").order_by("-created_at").first()
    assert del_cmd is not None
    assert "DELETE" in del_cmd.payload
