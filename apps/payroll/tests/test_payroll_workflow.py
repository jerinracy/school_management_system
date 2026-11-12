"""Integration tests for PayrollRun lifecycle, loan recovery, and accounting GL posting."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounting.models import FiscalYear, VoucherStatus
from apps.accounts.models import User, UserType
from apps.institutions.models import Institution
from apps.payroll.models import (
    LoanStatus,
    LoanType,
    PayrollRunStatus,
    SalaryPaymentMethod,
    StaffLoan,
    StaffSalaryProfile,
)
from apps.payroll.services import (
    apply_bonus_to_run,
    approve_payroll_run,
    generate_payroll_run,
    lock_payroll_run,
    mark_payroll_run_paid,
    post_payroll_to_accounting,
    review_payroll_run,
    seed_default_salary_structures,
)
from apps.staff.models import Staff


@pytest.mark.django_db
class TestPayrollWorkflowAndAccounting:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Chittagong Collegiate School",
            name_bn="চট্টগ্রাম কলেজিয়েট স্কুল",
        )
        self.admin_user = User.objects.create_user(
            username="payroll_admin",
            password="StrongPassword123!",
            institution=self.inst,
            phone="+8801700000001",
            user_type=UserType.ADMIN,
        )
        self.fiscal_year = FiscalYear.objects.create(
            institution=self.inst,
            name="FY 2026-2027",
            start_date=date(2026, 7, 1),
            end_date=date(2027, 6, 30),
            is_current=True,
        )
        structures = seed_default_salary_structures(self.inst)
        self.teacher_struct = next(s for s in structures if s.code == "TEACHER_STD")

        self.staff1 = Staff.objects.create(
            institution=self.inst,
            employee_id="T-101",
            full_name_en="Amina Begum",
            phone="+8801711111101",
            dob=date(1988, 5, 10),
            joining_date=date(2019, 1, 1),
        )
        self.staff2 = Staff.objects.create(
            institution=self.inst,
            employee_id="S-102",
            full_name_en="Rafiqul Islam",
            phone="+8801711111102",
            dob=date(1992, 3, 15),
            joining_date=date(2021, 1, 1),
        )
        self.profile1 = StaffSalaryProfile.objects.create(
            institution=self.inst,
            staff=self.staff1,
            structure=self.teacher_struct,
            basic_salary=Decimal("30000.00"),
            payment_method=SalaryPaymentMethod.BANK_TRANSFER,
            bank_name="Sonali Bank PLC",
            bank_account_number="1234567890",
            bank_routing_number="200260123",
            pf_enrolled=True,
            pf_employee_percent=Decimal("10.00"),
            pf_employer_percent=Decimal("10.00"),
        )
        self.profile2 = StaffSalaryProfile.objects.create(
            institution=self.inst,
            staff=self.staff2,
            structure=self.teacher_struct,
            basic_salary=Decimal("15000.00"),
            payment_method=SalaryPaymentMethod.CASH,
            pf_enrolled=False,
        )
        self.loan = StaffLoan.objects.create(
            institution=self.inst,
            staff=self.staff1,
            loan_type=LoanType.LOAN,
            principal_amount=Decimal("4000.00"),
            monthly_installment=Decimal("4000.00"),
            remaining_balance=Decimal("4000.00"),
            status=LoanStatus.ACTIVE,
        )

    def test_full_payroll_lifecycle_bonus_loan_settlement_and_gl_posting(self) -> None:
        # 1. Generate draft payroll run
        run = generate_payroll_run(
            institution=self.inst,
            year=2026,
            month=7,
            user=self.admin_user,
            working_days_in_month=22,
        )
        assert run.status == PayrollRunStatus.DRAFT
        assert run.payslips.count() == 2

        # 2. Apply 50% Eid bonus on basic salary
        run = apply_bonus_to_run(
            payroll_run=run,
            bonus_title="Eid-ul-Azha Bonus",
            percentage_of_basic=Decimal("50.00"),
        )
        slip1 = run.payslips.get(staff=self.staff1)
        assert slip1.bonus_amount == Decimal("15000.00")
        assert slip1.loan_deduction_amount == Decimal("4000.00")

        # 3. Review -> Approve -> Mark Paid (loan settles) -> Lock
        run = review_payroll_run(run, self.admin_user)
        assert run.status == PayrollRunStatus.REVIEWED

        run = approve_payroll_run(run, self.admin_user)
        assert run.status == PayrollRunStatus.APPROVED

        run = mark_payroll_run_paid(run, self.admin_user, payment_reference="BEFTN-2026-07")
        assert run.status == PayrollRunStatus.PAID
        assert run.payslips.filter(is_paid=True).count() == 2

        self.loan.refresh_from_db()
        assert self.loan.total_recovered == Decimal("4000.00")
        assert self.loan.remaining_balance == Decimal("0.00")
        assert self.loan.status == LoanStatus.COMPLETED

        # 4. Post to Accounting General Ledger (double-entry balanced)
        entry = post_payroll_to_accounting(run, self.admin_user, posting_date=date(2026, 7, 30))
        assert entry.status == VoucherStatus.POSTED
        assert entry.total_debit == entry.total_credit
        assert entry.total_debit > Decimal("0.00")

        run.refresh_from_db()
        assert run.journal_entry_id == entry.id

        # Duplicate GL posting must be blocked
        with pytest.raises(ValidationError):
            post_payroll_to_accounting(run, self.admin_user)

        # 5. Lock run and verify regeneration is blocked
        run = lock_payroll_run(run, self.admin_user)
        assert run.is_locked is True
        assert run.status == PayrollRunStatus.LOCKED

        with pytest.raises(ValidationError):
            generate_payroll_run(self.inst, 2026, 7, user=self.admin_user)
