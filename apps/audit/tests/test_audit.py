"""Tests for immutable AuditLog, ActivityLog, PII/secret redaction, signal hooks, and RBAC."""

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.audit.models import ActivityLog, AuditAction, AuditLog
from apps.audit.services import record, record_activity
from apps.institutions.models import Institution


def _grant_audit_view(user: User) -> None:
    ct = ContentType.objects.get_for_model(AuditLog)
    perm, _ = Permission.objects.get_or_create(
        codename="view",
        content_type=ct,
        defaults={"name": "audit.view"},
    )
    role, _ = Role.objects.get_or_create(
        institution=user.institution,
        code="role_audit_view",
        defaults={"name": "Auditor"},
    )
    role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role)


@pytest.fixture
def audit_env(db):
    inst_a = Institution.objects.create(
        name_en="School A",
        name_bn="স্কুল এ",
        eiin="109901",
    )
    inst_b = Institution.objects.create(
        name_en="School B",
        name_bn="স্কুল বি",
        eiin="109902",
    )
    auditor_a = User.objects.create_user(
        username="auditor_a",
        password="Password123!",
        phone="+8801711000021",
        institution=inst_a,
        user_type=UserType.ADMIN,
    )
    _grant_audit_view(auditor_a)

    teacher_a = User.objects.create_user(
        username="teacher_a",
        password="Password123!",
        phone="+8801711000022",
        institution=inst_a,
        user_type=UserType.TEACHER,
    )
    auditor_b = User.objects.create_user(
        username="auditor_b",
        password="Password123!",
        phone="+8801711000023",
        institution=inst_b,
        user_type=UserType.ADMIN,
    )
    _grant_audit_view(auditor_b)

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "auditor_a": auditor_a,
        "teacher_a": teacher_a,
        "auditor_b": auditor_b,
    }


@pytest.mark.django_db
def test_audit_log_is_immutable_orm_and_api(audit_env):
    log = record(
        action=AuditAction.UPDATE,
        module="fees",
        target_model="FeePayment",
        target_object_id="pay-1",
        before_data={"amount": "500.00"},
        after_data={"amount": "1000.00"},
        actor=audit_env["auditor_a"],
        institution=audit_env["inst_a"],
    )
    assert log.changed_fields == ["amount"]

    log.target_repr = "tampered"
    with pytest.raises(ValidationError):
        log.save()

    with pytest.raises(ValidationError):
        log.delete()

    client = APIClient()
    client.force_authenticate(user=audit_env["auditor_a"])

    assert client.post("/api/v1/audit/logs/", {}, format="json").status_code == 405
    assert client.patch(f"/api/v1/audit/logs/{log.id}/", {}, format="json").status_code == 405
    assert client.delete(f"/api/v1/audit/logs/{log.id}/").status_code == 405


@pytest.mark.django_db
def test_audit_record_redacts_secrets_and_masks_phones(audit_env):
    log = record(
        action=AuditAction.CREATE,
        module="guardians",
        target_model="Guardian",
        target_object_id="g-1",
        after_data={
            "name": "Rahim",
            "phone": "+8801712345678",
            "nid_number": "1990123456789",
            "password": "my-secret-password",
            "biometric_template": "raw-template-bytes",
        },
        actor=audit_env["auditor_a"],
        institution=audit_env["inst_a"],
    )
    assert log.after_data["password"] == "[REDACTED]"
    assert log.after_data["nid_number"] == "[REDACTED]"
    assert log.after_data["biometric_template"] == "[REDACTED]"
    assert log.after_data["phone"] == "+88017****5678"


@pytest.mark.django_db
def test_user_role_signal_creates_audit_log(audit_env):
    role = Role.objects.create(
        institution=audit_env["inst_a"],
        code="teacher_role",
        name="Teacher Role",
    )
    ur = UserRole.objects.create(user=audit_env["teacher_a"], role=role)
    assert AuditLog.objects.filter(
        institution=audit_env["inst_a"],
        action=AuditAction.ROLE_CHANGE,
        target_model="UserRole",
        target_object_id=str(ur.id),
    ).exists()


@pytest.mark.django_db
def test_audit_api_rbac_and_tenant_isolation(audit_env):
    log_a = record(
        action=AuditAction.EXPORT,
        module="reports",
        target_model="Student",
        actor=audit_env["auditor_a"],
        institution=audit_env["inst_a"],
    )
    log_b = record(
        action=AuditAction.EXPORT,
        module="reports",
        target_model="Student",
        actor=audit_env["auditor_b"],
        institution=audit_env["inst_b"],
    )
    act_a = record_activity(
        activity_type="login",
        module="accounts",
        description="Auditor A logged in",
        actor=audit_env["auditor_a"],
        institution=audit_env["inst_a"],
    )

    # Teacher without audit.view gets 403
    teacher_client = APIClient()
    teacher_client.force_authenticate(user=audit_env["teacher_a"])
    assert teacher_client.get("/api/v1/audit/logs/").status_code == 403
    assert teacher_client.get("/api/v1/audit/activities/").status_code == 403

    # Auditor A sees only Institution A logs & activities
    auditor_client = APIClient()
    auditor_client.force_authenticate(user=audit_env["auditor_a"])
    logs_resp = auditor_client.get("/api/v1/audit/logs/")
    assert logs_resp.status_code == 200
    ids = {item["id"] for item in logs_resp.data["results"]}
    assert str(log_a.id) in ids
    assert str(log_b.id) not in ids

    act_resp = auditor_client.get("/api/v1/audit/activities/")
    assert act_resp.status_code == 200
    act_ids = {item["id"] for item in act_resp.data["results"]}
    assert str(act_a.id) in act_ids
    assert ActivityLog.objects.filter(id=act_a.id).exists()
