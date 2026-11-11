"""Unit tests for Biometric Device models and constraints."""

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.devices.models import (
    BiometricConsent,
    BiometricEnrollment,
    Device,
    DeviceGroup,
    DeviceGroupMember,
    DeviceProtocol,
    DeviceStatus,
    DeviceType,
    DeviceUserMap,
    RawPunch,
    RawPunchStatus,
)
from apps.guardians.models import Guardian
from apps.institutions.models import Institution
from apps.staff.models import Staff
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(
        name_en="Dhaka Model Academy",
        name_bn="ঢাকা মডেল একাডেমি",
        eiin="123456",
    )


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-001",
        name_en="Rahim Uddin",
        name_bn="রহিম উদ্দিন",
        dob="2012-05-15",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def guardian(db, institution) -> Guardian:
    return Guardian.objects.create(
        institution=institution,
        name_en="Kalam Uddin",
        name_bn="কালাম উদ্দিন",
        phone="+8801711000001",
        relation_default="father",
    )


@pytest.fixture
def staff(db, institution) -> Staff:
    return Staff.objects.create(
        institution=institution,
        employee_id="TCH-001",
        full_name_en="Abdul Karim",
        full_name_bn="আব্দুল করিম",
        dob="1985-05-10",
        gender="male",
        joining_date="2020-01-01",
    )


@pytest.mark.django_db
def test_device_creation_and_str(institution):
    device = Device.objects.create(
        institution=institution,
        name="Main Gate Terminal 1",
        serial_no="ZK-SN-001",
        vendor="ZKTeco",
        model="SpeedFace-V5L",
        device_type=DeviceType.FACE,
        protocol=DeviceProtocol.PUSH_ADMS,
    )
    assert device.id is not None
    assert str(device) == "Main Gate Terminal 1 (ZKTeco - ZK-SN-001)"
    assert device.status == DeviceStatus.OFFLINE


@pytest.mark.django_db
def test_device_serial_uniqueness_per_institution(institution):
    Device.objects.create(
        institution=institution,
        name="Gate 1",
        serial_no="ZK-SN-UNIQUE",
    )
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Device.objects.create(
                institution=institution,
                name="Gate 2",
                serial_no="ZK-SN-UNIQUE",
            )


@pytest.mark.django_db
def test_device_group_and_membership(institution):
    group = DeviceGroup.objects.create(
        institution=institution,
        name="Student Perimeter",
        target_audience="students",
    )
    d1 = Device.objects.create(institution=institution, name="D1", serial_no="D1")
    member = DeviceGroupMember.objects.create(
        institution=institution,
        group=group,
        device=d1,
    )
    assert member.id is not None
    assert str(member) == "D1 in Student Perimeter"

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            DeviceGroupMember.objects.create(
                institution=institution,
                group=group,
                device=d1,
            )


@pytest.mark.django_db
def test_device_user_map_uniqueness(institution, student):
    device = Device.objects.create(institution=institution, name="D1", serial_no="SN-MAP")
    DeviceUserMap.objects.create(
        institution=institution,
        device=device,
        device_user_id="101",
        user_type="student",
        student=student,
    )

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            DeviceUserMap.objects.create(
                institution=institution,
                device=device,
                device_user_id="101",
                user_type="student",
                student=student,
            )


@pytest.mark.django_db
def test_biometric_consent_and_enrollment(institution, student, guardian):
    consent = BiometricConsent.objects.create(
        institution=institution,
        subject_type="student",
        student=student,
        guardian=guardian,
        consent_version="v1.0",
    )
    assert consent.is_active is True
    assert "Active" in str(consent)

    device = Device.objects.create(institution=institution, name="D1", serial_no="SN-ENR")
    enrollment = BiometricEnrollment.objects.create(
        institution=institution,
        subject_type="student",
        student=student,
        device=device,
        method=DeviceType.FACE,
        device_user_id="101",
        consent=consent,
    )
    assert enrollment.id is not None
    assert enrollment.is_active is True


@pytest.mark.django_db
def test_raw_punch_immutability_and_unique_constraint(institution):
    device = Device.objects.create(institution=institution, name="D1", serial_no="SN-PUNCH")
    dt = timezone.now()

    punch = RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="101",
        device_time=dt,
        payload_hash="hash123",
        status=RawPunchStatus.UNMAPPED,
    )
    assert punch.id is not None

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            RawPunch.objects.create(
                institution=institution,
                device=device,
                serial_no=device.serial_no,
                raw_user_id="101",
                device_time=dt,
                payload_hash="hash123-dup",
                status=RawPunchStatus.UNMAPPED,
            )
