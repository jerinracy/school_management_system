"""API, RBAC, Self-service, PDF, Bank Advice XLSX/CSV, and Tenant Isolation tests."""

import io
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, User, UserRole, UserType
from apps.institutions.models import Institution
from apps.payroll.models import PayrollRun, SalaryPaymentMethod, StaffSalaryProfile
from apps.payroll.services import (
    export_bank_advice_csv,
    export_bank_advice_xlsx,
    generate_payroll_run,
    render_payslip_pdf,
    seed_default_salary_structures,
)
from apps.staff.models import Staff


def _grant_permissions(user: User, codes: list[str]) -> None:
    assert user.institution is not None
    ct = ContentType.objects.get_for_model(PayrollRun)
    role = Role.objects.create(
        institution=user.institution,
        name=f"Role-{user.username}",
        code=f"role_{user.username}",
    )
    for code in codes:
        short_code = code.split(".")[-1]
        perm, _ = Permission.objects.get_or_create(
            codename=short_code,
            content_type=ct,
            defaults={"name": code},
        )
        role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role)


@pytest.mark.django_db
class TestPayrollExportsAndAPI:
    def setup_method(self) -> None:
        self.inst_a = Institution.objects.create(
            name_en="Rajshahi Pilot School",
            name_bn="রাজশাহী পাইলট স্কুল",
        )
        self.inst_b = Institution.objects.create(
            name_en="Khulna Zilla School",
            name_bn="খুলনা জিলা স্কুল",
        )

        self.payroll_mgr = User.objects.create_user(
            username="mgr_a",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801722222201",
            user_type=UserType.STAFF,
        )
        _grant_permissions(
            self.payroll_mgr,
            ["payroll.view", "payroll.manage", "payroll.approve"],
        )

        self.teacher_user = User.objects.create_user(
            username="teacher_a",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801722222202",
            user_type=UserType.TEACHER,
        )
        self.other_teacher_user = User.objects.create_user(
            username="teacher_other",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801722222203",
            user_type=UserType.TEACHER,
        )
        self.tenant_b_mgr = User.objects.create_user(
            username="mgr_b",
            password="Password123!",
            institution=self.inst_b,
            phone="+8801722222204",
            user_type=UserType.STAFF,
        )
        _grant_permissions(self.tenant_b_mgr, ["payroll.view", "payroll.manage"])

        structures = seed_default_salary_structures(self.inst_a)
        teacher_struct = next(s for s in structures if s.code == "TEACHER_STD")

        self.staff1 = Staff.objects.create(
            institution=self.inst_a,
            user=self.teacher_user,
            employee_id="RPS-001",
            full_name_en="Tahmina Akter",
            full_name_bn="তাহমিনা আক্তার",
            phone="+8801722222202",
            dob=date(1991, 2, 14),
            joining_date=date(2021, 1, 1),
        )
        self.staff2 = Staff.objects.create(
            institution=self.inst_a,
            user=self.other_teacher_user,
            employee_id="RPS-002",
            full_name_en="Kamrul Hasan",
            phone="+8801722222203",
            dob=date(1989, 7, 20),
            joining_date=date(2020, 1, 1),
        )
        self.staff_b = Staff.objects.create(
            institution=self.inst_b,
            employee_id="KZS-001",
            full_name_en="Other School Staff",
            phone="+8801722222299",
            dob=date(1990, 1, 1),
            joining_date=date(2022, 1, 1),
        )

        StaffSalaryProfile.objects.create(
            institution=self.inst_a,
            staff=self.staff1,
            structure=teacher_struct,
            basic_salary=Decimal("25000.00"),
            payment_method=SalaryPaymentMethod.BANK_TRANSFER,
            bank_name="Islami Bank Bangladesh PLC",
            bank_branch="Rajshahi",
            bank_account_number="2050123456789",
            bank_routing_number="125811234",
        )
        StaffSalaryProfile.objects.create(
            institution=self.inst_a,
            staff=self.staff2,
            structure=teacher_struct,
            basic_salary=Decimal("20000.00"),
            payment_method=SalaryPaymentMethod.MFS,
            mfs_number="+8801722222203",
        )

        self.run = generate_payroll_run(
            institution=self.inst_a,
            year=2026,
            month=7,
            user=self.payroll_mgr,
            working_days_in_month=22,
        )
        self.slip1 = self.run.payslips.get(staff=self.staff1)
        self.slip2 = self.run.payslips.get(staff=self.staff2)

    def test_payslip_pdf_and_bank_advice_exports(self) -> None:
        pdf_bytes = render_payslip_pdf(self.slip1)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

        csv_bytes = export_bank_advice_csv(self.run)
        csv_text = csv_bytes.decode("utf-8-sig")
        assert "RPS-001" in csv_text
        assert "2050123456789" in csv_text
        assert "TOTAL" in csv_text

        xlsx_bytes = export_bank_advice_xlsx(self.run)
        wb = load_workbook(io.BytesIO(xlsx_bytes))
        ws = wb["Bank Advice"]
        assert ws["B3"].value == "RPS-001"
        assert ws["B4"].value == "RPS-002"
        assert ws["C5"].value == "TOTAL"

    def test_api_permissions_self_service_and_tenant_isolation(self) -> None:
        client = APIClient()

        # 1. Unauthenticated denied
        resp = client.get(reverse("v1_payroll:run-list"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. Teacher cannot access admin payroll runs or other teacher's payslip
        client.force_authenticate(user=self.teacher_user)
        assert client.get(reverse("v1_payroll:run-list")).status_code == status.HTTP_403_FORBIDDEN
        assert (
            client.get(
                reverse("v1_payroll:payslip-detail", kwargs={"pk": self.slip2.id})
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Teacher CAN view own payslips and download own PDF
        my_resp = client.get(reverse("v1_payroll:payslip-my-payslips"))
        assert my_resp.status_code == status.HTTP_200_OK
        assert len(my_resp.data["results"]) == 1
        pdf_resp = client.get(reverse("v1_payroll:payslip-pdf", kwargs={"pk": self.slip1.id}))
        assert pdf_resp.status_code == status.HTTP_200_OK
        assert pdf_resp["Content-Type"] == "application/pdf"
        assert pdf_resp.content.startswith(b"%PDF")

        # 3. Tenant B manager cannot see Tenant A runs or inject Tenant A's staff into a Tenant B profile
        client.force_authenticate(user=self.tenant_b_mgr)
        runs_b = client.get(reverse("v1_payroll:run-list"))
        assert runs_b.status_code == status.HTTP_200_OK
        assert runs_b.data["count"] == 0

        cross_resp = client.post(
            reverse("v1_payroll:profile-list"),
            data={"staff": str(self.staff1.id), "basic_salary": "10000.00"},
            format="json",
        )
        assert cross_resp.status_code == status.HTTP_400_BAD_REQUEST

        # 4. Payroll manager can download BEFTN bank advice XLSX and CSV via API
        client.force_authenticate(user=self.payroll_mgr)
        xlsx_resp = client.get(
            reverse("v1_payroll:run-bank-advice", kwargs={"pk": self.run.id}),
            {"export_format": "xlsx"},
        )
        assert xlsx_resp.status_code == status.HTTP_200_OK
        assert "spreadsheetml" in xlsx_resp["Content-Type"]

        csv_resp = client.get(
            reverse("v1_payroll:run-bank-advice", kwargs={"pk": self.run.id}),
            {"export_format": "csv"},
        )
        assert csv_resp.status_code == status.HTTP_200_OK
        assert "text/csv" in csv_resp["Content-Type"]

    def test_api_workflow_actions_and_role_segregation(self) -> None:
        from apps.accounting.models import FiscalYear

        FiscalYear.objects.create(
            institution=self.inst_a,
            name="FY 2026-2027",
            start_date=date(2026, 7, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )

        # Preparer with ONLY payroll.view + payroll.manage (no payroll.approve)
        preparer = User.objects.create_user(
            username="prep_a",
            password="Password123!",
            institution=self.inst_a,
            phone="+8801722222210",
            user_type=UserType.STAFF,
        )
        _grant_permissions(preparer, ["payroll.view", "payroll.manage"])

        client = APIClient()
        client.force_authenticate(user=preparer)

        # Preparer can apply bonus and review DRAFT run
        bonus_resp = client.post(
            reverse("v1_payroll:run-apply-bonus", kwargs={"pk": self.run.id}),
            {"bonus_title": "Eid Bonus", "fixed_amount": "5000.00"},
            format="json",
        )
        assert bonus_resp.status_code == status.HTTP_200_OK

        review_resp = client.post(reverse("v1_payroll:run-review", kwargs={"pk": self.run.id}))
        assert review_resp.status_code == status.HTTP_200_OK
        assert review_resp.data["status"] == "reviewed"

        # Preparer CANNOT approve (403 Forbidden)
        assert (
            client.post(reverse("v1_payroll:run-approve", kwargs={"pk": self.run.id})).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # Approver can approve, mark paid, post to GL, and lock
        client.force_authenticate(user=self.payroll_mgr)
        assert (
            client.post(reverse("v1_payroll:run-approve", kwargs={"pk": self.run.id})).status_code
            == status.HTTP_200_OK
        )
        assert (
            client.post(
                reverse("v1_payroll:run-mark-paid", kwargs={"pk": self.run.id}),
                {"payment_reference": "BEFTN-01"},
                format="json",
            ).status_code
            == status.HTTP_200_OK
        )
        gl_resp = client.post(
            reverse("v1_payroll:run-post-to-accounting", kwargs={"pk": self.run.id}),
            {"posting_date": "2026-07-30"},
            format="json",
        )
        assert gl_resp.status_code == status.HTTP_200_OK
        assert Decimal(gl_resp.data["total_debit"]) == Decimal(gl_resp.data["total_credit"])

        lock_resp = client.post(reverse("v1_payroll:run-lock", kwargs={"pk": self.run.id}))
        assert lock_resp.status_code == status.HTTP_200_OK
        assert lock_resp.data["is_locked"] is True
