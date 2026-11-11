"""Integration tests for Biometric Devices, Webhooks, and Intake Endpoints."""

import hashlib
import hmac
import json

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.accounts.test_helpers import make_user
from apps.devices.models import (
    BiometricConsent,
    CommandStatus,
    Device,
    DeviceCommand,
    DeviceGroup,
    DeviceProtocol,
    DeviceType,
    RawPunch,
    RawPunchStatus,
)
from apps.guardians.models import Guardian
from apps.institutions.models import Institution
from apps.students.models import Student


@pytest.fixture
def institution(db) -> Institution:
    return Institution.objects.create(name_en="Dhaka High", eiin="554433")


@pytest.fixture
def other_institution(db) -> Institution:
    return Institution.objects.create(name_en="Chittagong High", eiin="665544")


@pytest.fixture
def admin_user(db, institution) -> User:
    user = make_user(
        username="device_admin",
        institution=institution,
        user_type=UserType.STAFF,
        phone="+8801700000001",
    )
    role, _ = Role.objects.get_or_create(institution=institution, code="device_admin")
    ct = ContentType.objects.get_for_model(Device)
    p_view, _ = Permission.objects.get_or_create(
        codename="view", content_type=ct, defaults={"name": "Can view devices"}
    )
    p_manage, _ = Permission.objects.get_or_create(
        codename="manage", content_type=ct, defaults={"name": "Can manage devices"}
    )
    role.permissions.add(p_view, p_manage)
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def student(db, institution) -> Student:
    return Student.objects.create(
        institution=institution,
        student_id="STU-003",
        name_en="Adib Hasan",
        name_bn="আদিব হাসান",
        dob="2012-04-01",
        gender="male",
        admission_date="2026-01-01",
    )


@pytest.fixture
def guardian(db, institution) -> Guardian:
    return Guardian.objects.create(
        institution=institution,
        name_en="Hasan Ali",
        phone="+8801711223399",
        relation_default="father",
    )


@pytest.fixture
def device(db, institution) -> Device:
    return Device.objects.create(
        institution=institution,
        name="Main Gate Biometric",
        serial_no="ZK-GATE-01",
        vendor="ZKTeco",
        protocol=DeviceProtocol.PUSH_ADMS,
        device_type=DeviceType.FACE,
    )


@pytest.mark.django_db
def test_device_crud_and_tenant_isolation(admin_user, institution, other_institution):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # List devices (empty initially)
    resp = client.get("/api/v1/devices/terminals/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0

    # Create device
    payload = {
        "name": "Library Terminal",
        "serial_no": "LIB-001",
        "vendor": "ZKTeco",
        "protocol": "push_adms",
        "device_type": "fingerprint",
    }
    resp = client.post("/api/v1/devices/terminals/", payload)
    assert resp.status_code == status.HTTP_201_CREATED
    dev_id = resp.data["id"]

    # Device belonging to another institution should not be visible
    Device.objects.create(
        institution=other_institution,
        name="Other Inst Device",
        serial_no="OTHER-001",
    )
    resp = client.get("/api/v1/devices/terminals/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == dev_id


@pytest.mark.django_db
def test_device_test_connection_action(admin_user, device):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    resp = client.post(f"/api/v1/devices/terminals/{device.id}/test-connection/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "online"
    device.refresh_from_db()
    assert device.last_seen is not None


@pytest.mark.django_db
def test_device_enroll_user_action_with_consent(admin_user, device, student, guardian):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Attempt enrollment without consent -> fails
    resp = client.post(
        f"/api/v1/devices/terminals/{device.id}/enroll-user/",
        {
            "user_pin": "501",
            "user_name": "Adib",
            "student_id": str(student.id),
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Create consent
    BiometricConsent.objects.create(
        institution=device.institution,
        subject_type="student",
        student=student,
        guardian=guardian,
    )

    # Enrollment succeeds now
    resp = client.post(
        f"/api/v1/devices/terminals/{device.id}/enroll-user/",
        {
            "user_pin": "501",
            "user_name": "Adib",
            "student_id": str(student.id),
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert "command_id" in resp.data


@pytest.mark.django_db
def test_device_group_members_actions(admin_user, institution, device):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    group = DeviceGroup.objects.create(
        institution=institution,
        name="Gate Group",
    )

    # Add member
    resp = client.post(
        f"/api/v1/devices/groups/{group.id}/add-member/",
        {"device_id": str(device.id)},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert group.members.count() == 1

    # Remove member
    resp = client.post(
        f"/api/v1/devices/groups/{group.id}/remove-member/",
        {"device_id": str(device.id)},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert group.members.count() == 0


@pytest.mark.django_db
def test_raw_punch_and_unmapped_resolution_api(admin_user, institution, device, student):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    punch = RawPunch.objects.create(
        institution=institution,
        device=device,
        serial_no=device.serial_no,
        raw_user_id="UNKNOWN_123",
        device_time=timezone.now(),
        status=RawPunchStatus.UNMAPPED,
    )

    # List unmapped punches
    resp = client.get("/api/v1/devices/unmapped-punches/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    # Resolve punch
    resp = client.post(
        f"/api/v1/devices/unmapped-punches/{punch.id}/resolve/",
        {"student_id": str(student.id), "create_mapping": True},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == RawPunchStatus.UNPROCESSED
    assert str(resp.data["resolved_student"]) == str(student.id)


@pytest.mark.django_db
def test_zkteco_adms_push_flow(device):
    client = APIClient()

    # Heartbeat GET /iclock/cdata?SN=...
    resp = client.get(f"/iclock/cdata?SN={device.serial_no}")
    assert resp.status_code == 200
    assert resp.content.decode() == "OK"

    # Push punch ATTLOG POST /iclock/cdata?SN=...&table=ATTLOG
    raw_body = "1001\t2026-03-01 08:30:00\t0\t1\t0\n"
    resp = client.post(
        f"/iclock/cdata?SN={device.serial_no}&table=ATTLOG",
        data=raw_body,
        content_type="text/plain",
    )
    assert resp.status_code == 200
    assert "OK: 1" in resp.content.decode()

    # Command polling GET /iclock/getrequest
    cmd = DeviceCommand.objects.create(
        institution=device.institution,
        device=device,
        command_type="reboot",
        payload="REBOOT",
        status=CommandStatus.QUEUED,
    )
    resp = client.get(f"/iclock/getrequest?SN={device.serial_no}")
    assert resp.status_code == 200
    assert f"C:{cmd.id}:REBOOT" in resp.content.decode()

    # Command acknowledgement POST /iclock/devicecmd
    cmd_resp_body = f"ID={cmd.id}&Return=0&CMD=REBOOT"
    resp = client.post(
        f"/iclock/devicecmd?SN={device.serial_no}",
        data=cmd_resp_body,
        content_type="text/plain",
    )
    assert resp.status_code == 200
    cmd.refresh_from_db()
    assert cmd.status == CommandStatus.ACKNOWLEDGED


@pytest.mark.django_db
def test_generic_webhook_push(institution):
    secret = "webhook_secret_key"
    device = Device.objects.create(
        institution=institution,
        name="Webhook Terminal",
        serial_no="WB-001",
        protocol=DeviceProtocol.GENERIC_HTTP,
        auth_secret=secret,
    )
    client = APIClient()
    payload = {
        "punches": [
            {
                "user_id": "777",
                "timestamp": "2026-03-01T08:00:00Z",
                "punch_type": "in",
            }
        ]
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    resp = client.post(
        "/api/v1/devices/push/webhook/",
        data=body_bytes,
        content_type="application/json",
        HTTP_X_DEVICE_SERIAL=device.serial_no,
        HTTP_X_SIGNATURE=sig,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created"] == 1
