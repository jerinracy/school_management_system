"""Tests for Dashboard KPIs, Whitelisted Report Builder, CSV/XLSX/PDF Exports, Bulk Imports & RBAC."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.audit.models import AuditAction, AuditLog
from apps.devices.models import Device, DeviceStatus
from apps.fees.models import Payment, PaymentMethod, PaymentStatus
from apps.institutions.models import Institution
from apps.reports.models import BulkImportStatus, ReportDefinition
from apps.students.models import Student


def _grant_reports_perms(user: User, codenames: list[str]) -> None:
    ct = ContentType.objects.get_for_model(ReportDefinition)
    role, _ = Role.objects.get_or_create(
        institution=user.institution,
        code=f"role_reports_{user.username}",
        defaults={"name": f"Reports-{user.username}"},
    )
    for code in codenames:
        perm, _ = Permission.objects.get_or_create(
            codename=code,
            content_type=ct,
            defaults={"name": f"reports.{code}"},
        )
        role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role)


@pytest.fixture
def reports_env(db):
    inst = Institution.objects.create(
        name_en="Comilla High School",
        name_bn="কুমিল্লা উচ্চ বিদ্যালয়",
        eiin="107701",
    )
    other_inst = Institution.objects.create(
        name_en="Other High School",
        name_bn="অন্য উচ্চ বিদ্যালয়",
        eiin="107702",
    )
    admin = User.objects.create_user(
        username="rep_admin",
        password="Password123!",
        phone="+8801711000031",
        institution=inst,
        user_type=UserType.ADMIN,
    )
    _grant_reports_perms(admin, ["view", "manage"])

    teacher = User.objects.create_user(
        username="rep_teacher",
        password="Password123!",
        phone="+8801711000032",
        institution=inst,
        user_type=UserType.TEACHER,
    )
    _grant_reports_perms(teacher, ["view"])

    guardian = User.objects.create_user(
        username="rep_guardian",
        password="Password123!",
        phone="+8801711000033",
        institution=inst,
        user_type=UserType.GUARDIAN,
    )

    student = Student.objects.create(
        institution=inst,
        student_id="STU-REP-001",
        name_en="Nadia Islam",
        name_bn="নাদিয়া ইসলাম",
        dob=date(2011, 5, 10),
        gender="female",
        admission_date=date(2024, 1, 10),
        emergency_contact_name="Islam Mia",
        emergency_contact_phone="+8801711000033",
    )
    DailyAttendance.objects.create(
        institution=inst,
        date=date.today(),
        user_type="student",
        student=student,
        status=AttendanceStatus.PRESENT,
    )
    Device.objects.create(
        institution=inst,
        name="Gate Scanner",
        serial_no="SN-REP-001",
        status=DeviceStatus.ONLINE,
        is_active=True,
    )
    Payment.objects.create(
        institution=inst,
        student=student,
        payment_method=PaymentMethod.CASH,
        amount=Decimal("1500.00"),
        status=PaymentStatus.SUCCESSFUL,
        idempotency_key="rep-pay-1",
        payment_date=timezone.now(),
    )

    return {
        "inst": inst,
        "other_inst": other_inst,
        "admin": admin,
        "teacher": teacher,
        "guardian": guardian,
        "student": student,
    }


@pytest.mark.django_db
def test_dashboard_kpis_and_role_variants(reports_env):
    admin_client = APIClient()
    admin_client.force_authenticate(user=reports_env["admin"])
    resp = admin_client.get("/api/v1/reports/dashboard/kpis/")
    assert resp.status_code == 200
    assert resp.data["attendance"]["student"]["present"] == 1
    assert resp.data["devices"]["online"] == 1
    assert resp.data["finance"]["collected_today"] == "1500.00"
    assert "headcount" in resp.data
    assert "total_students" in resp.data["headcount"]
    assert "total_teachers" in resp.data["headcount"]
    assert "morning_shift_students" in resp.data["headcount"]
    assert "day_shift_students" in resp.data["headcount"]
    assert "attendance_rates" in resp.data
    assert "student_present_pct" in resp.data["attendance_rates"]

    # Teacher gets attendance/devices KPIs but NOT financial KPIs
    teacher_client = APIClient()
    teacher_client.force_authenticate(user=reports_env["teacher"])
    t_resp = teacher_client.get("/api/v1/reports/dashboard/kpis/")
    assert t_resp.status_code == 200
    assert "finance" not in t_resp.data

    # Guardian without reports.view gets 403
    g_client = APIClient()
    g_client.force_authenticate(user=reports_env["guardian"])
    assert g_client.get("/api/v1/reports/dashboard/kpis/").status_code == 403


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/sms_test_reports_media")
def test_report_whitelist_and_csv_xlsx_pdf_exports(reports_env):
    client = APIClient()
    client.force_authenticate(user=reports_env["admin"])

    # Disallowed column rejected
    bad_col = client.post(
        "/api/v1/reports/exports/run/",
        {
            "dataset": "students",
            "selected_columns": ["student_id", "secret_sql_col"],
            "export_format": "csv",
        },
        format="json",
    )
    assert bad_col.status_code == 400

    # Valid CSV, XLSX, PDF exports
    for fmt, prefix in [("csv", b"student_id,name_en"), ("xlsx", b"PK"), ("pdf", b"%PDF")]:
        run_resp = client.post(
            "/api/v1/reports/exports/run/",
            {
                "dataset": "students",
                "selected_columns": ["student_id", "name_en"],
                "export_format": fmt,
            },
            format="json",
        )
        assert run_resp.status_code == 201
        assert run_resp.data["row_count"] == 1
        job_id = run_resp.data["id"]

        dl_resp = client.get(f"/api/v1/reports/exports/{job_id}/download/")
        assert dl_resp.status_code == 200
        assert dl_resp.content.startswith(prefix)

    assert (
        AuditLog.objects.filter(
            institution=reports_env["inst"],
            action=AuditAction.EXPORT,
            module="reports",
        ).count()
        >= 3
    )


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/sms_test_reports_media")
def test_bulk_import_dry_run_and_commit(reports_env):
    client = APIClient()
    client.force_authenticate(user=reports_env["admin"])

    # Template download
    tpl = client.get("/api/v1/reports/imports/template/?target_type=students")
    assert tpl.status_code == 200
    assert b"student_id,name_en" in tpl.content

    csv_body = (
        "student_id,name_en,name_bn,gender,dob,admission_date,emergency_contact_name,emergency_contact_phone\n"
        "STU-IMP-01,Rafi Ahmed,রাফি আহমেদ,male,2012-06-01,2026-01-05,Karim,+8801711999999\n"
    ).encode("utf-8")

    # Dry run validates without creating Student
    dry_resp = client.post(
        "/api/v1/reports/imports/upload/",
        {
            "target_type": "students",
            "dry_run": "true",
            "file": SimpleUploadedFile("students.csv", csv_body, content_type="text/csv"),
        },
        format="multipart",
    )
    assert dry_resp.status_code == 201
    assert dry_resp.data["status"] == BulkImportStatus.VALIDATED
    assert dry_resp.data["valid_rows"] == 1
    assert not Student.objects.filter(
        institution=reports_env["inst"], student_id="STU-IMP-01"
    ).exists()

    # Commit creates Student
    commit_resp = client.post(
        "/api/v1/reports/imports/upload/",
        {
            "target_type": "students",
            "dry_run": "false",
            "file": SimpleUploadedFile("students.csv", csv_body, content_type="text/csv"),
        },
        format="multipart",
    )
    assert commit_resp.status_code == 201
    assert commit_resp.data["status"] == BulkImportStatus.COMMITTED
    assert Student.objects.filter(institution=reports_env["inst"], student_id="STU-IMP-01").exists()
