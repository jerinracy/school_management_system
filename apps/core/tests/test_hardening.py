"""Tests for security headers, admin 2FA/IP enforcement, encryption rotation, metrics, backup & privacy."""

import json
from datetime import date

import pytest
from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User, UserType
from apps.audit.models import AuditAction, AuditLog
from apps.core.utils.encryption import decrypt_value, encrypt_value, rotate_ciphertext
from apps.institutions.models import Institution
from apps.students.models import Student


@pytest.fixture
def hardening_env(db):
    inst = Institution.objects.create(
        name_en="Hardened School",
        name_bn="হার্ডেন্ড স্কুল",
        eiin="106601",
    )
    admin = User.objects.create_user(
        username="hard_admin",
        password="Password123!",
        phone="+8801711000041",
        institution=inst,
        user_type=UserType.ADMIN,
        is_staff=True,
        is_totp_enabled=False,
    )
    teacher = User.objects.create_user(
        username="hard_teacher",
        password="Password123!",
        phone="+8801711000042",
        institution=inst,
        user_type=UserType.TEACHER,
        is_staff=False,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-HARD-01",
        name_en="Amina Begum",
        name_bn="আমিনা বেগম",
        dob=date(2012, 4, 12),
        gender="female",
        admission_date=date(2025, 1, 5),
        emergency_contact_name="Karim",
        emergency_contact_phone="+8801711000042",
    )
    return {"inst": inst, "admin": admin, "teacher": teacher, "student": student}


@pytest.mark.django_db
def test_security_headers_and_metrics_endpoint(hardening_env):
    client = APIClient()
    health = client.get("/api/v1/health/")
    assert health["X-Content-Type-Options"] == "nosniff"
    assert health["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in health["Permissions-Policy"]

    # Non-staff cannot access /api/v1/metrics/
    client.force_authenticate(user=hardening_env["teacher"])
    assert client.get("/api/v1/metrics/").status_code == 403

    # Staff admin can access /api/v1/metrics/
    client.force_authenticate(user=hardening_env["admin"])
    m = client.get("/api/v1/metrics/")
    assert m.status_code == 200
    assert m.data["active_institutions"] >= 1


@pytest.mark.django_db
@override_settings(ENFORCE_ADMIN_2FA=True)
def test_admin_2fa_enforcement_and_ip_allowlist(hardening_env):
    admin = hardening_env["admin"]
    client = APIClient()
    client.force_authenticate(user=admin)

    # Blocked when is_totp_enabled=False
    blocked = client.get("/api/v1/metrics/")
    assert blocked.status_code == 403

    # Health & Auth endpoints remain accessible
    assert client.get("/api/v1/health/").status_code == 200

    # Allowed once 2FA is enabled
    admin.is_totp_enabled = True
    admin.save(update_fields=["is_totp_enabled"])
    assert client.get("/api/v1/metrics/").status_code == 200

    # IP allowlist restriction
    with override_settings(ADMIN_ALLOWED_IPS=["10.0.0.1/32"]):
        ip_blocked = client.get("/api/v1/metrics/", REMOTE_ADDR="192.168.1.50")
        assert ip_blocked.status_code == 403

        ip_ok = client.get("/api/v1/metrics/", REMOTE_ADDR="10.0.0.1")
        assert ip_ok.status_code == 200


def test_field_encryption_and_key_rotation():
    key1 = Fernet.generate_key().decode("utf-8")
    key2 = Fernet.generate_key().decode("utf-8")

    with override_settings(FIELD_ENCRYPTION_KEYS=[key1]):
        cipher = encrypt_value("NID-1990123456789")
        assert cipher != "NID-1990123456789"
        assert decrypt_value(cipher) == "NID-1990123456789"

    # Rotate from key1 -> key2 (newest key first)
    with override_settings(FIELD_ENCRYPTION_KEYS=[key2, key1]):
        assert decrypt_value(cipher) == "NID-1990123456789"
        rotated = rotate_ciphertext(cipher)

    # After retiring key1, rotated ciphertext still decrypts with key2 alone
    with override_settings(FIELD_ENCRYPTION_KEYS=[key2]):
        assert decrypt_value(rotated) == "NID-1990123456789"


@pytest.mark.django_db
def test_backup_database_and_privacy_export_commands(hardening_env, tmp_path):
    backup_dir = tmp_path / "backups"
    call_command("backup_database", backup_dir=str(backup_dir), retention_days=30)
    backups = list(backup_dir.glob("db_backup_*"))
    assert len(backups) == 1

    export_file = tmp_path / "privacy.json"
    call_command(
        "privacy_export_student",
        str(hardening_env["student"].id),
        output=str(export_file),
    )
    data = json.loads(export_file.read_text(encoding="utf-8"))
    assert data["student"]["student_id"] == "STU-HARD-01"
    assert AuditLog.objects.filter(
        institution=hardening_env["inst"],
        action=AuditAction.EXPORT,
        target_model="Student",
    ).exists()
