"""Unit tests for payroll calculator, working days, attendance, and overrides."""

from datetime import date
from decimal import Decimal

import pytest

from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.institutions.models import AcademicSession, Holiday, HolidayType, Institution
from apps.payroll.models import (
    AbsenceDeductionBasis,
    CalculationType,
    ComponentType,
    LoanStatus,
    LoanType,
    SalaryComponent,
    StaffLoan,
    StaffSalaryOverride,
    StaffSalaryProfile,
)
from apps.payroll.services import (
    calculate_payslip_breakdown,
    count_working_days_in_month,
    get_staff_monthly_attendance_summary,
    seed_default_salary_components,
    seed_default_salary_structures,
)
from apps.staff.models import LeaveRequest, LeaveRequestStatus, LeaveType, Staff


@pytest.mark.django_db
class TestPayrollCalculator:
    def setup_method(self) -> None:
        self.inst = Institution.objects.create(
            name_en="Dhaka Model School",
            name_bn="ঢাকা মডেল স্কুল",
            weekend_days=["friday", "saturday"],
        )
        self.components = seed_default_salary_components(self.inst)
        self.structures = seed_default_salary_structures(self.inst)
        self.teacher_structure = next(s for s in self.structures if s.code == "TEACHER_STD")
        self.staff = Staff.objects.create(
            institution=self.inst,
            employee_id="EMP-001",
            full_name_en="Md. Karim Uddin",
            full_name_bn="মোঃ করিম উদ্দিন",
            phone="+8801711111111",
            dob=date(1990, 1, 1),
            joining_date=date(2020, 1, 1),
        )
        self.profile = StaffSalaryProfile.objects.create(
            institution=self.inst,
            staff=self.staff,
            structure=self.teacher_structure,
            basic_salary=Decimal("20000.00"),
            pf_enrolled=True,
            pf_employee_percent=Decimal("10.00"),
            pf_employer_percent=Decimal("10.00"),
            late_deduction_enabled=True,
            late_days_per_absent=3,
            overtime_hourly_rate=Decimal("250.00"),
        )

    def test_count_working_days_excludes_weekends_and_holidays(self) -> None:
        # July 2026: 31 days; Fridays: 3, 10, 17, 24, 31 (5); Saturdays: 4, 11, 18, 25 (4) => 22 working days
        assert count_working_days_in_month(self.inst, 2026, 7) == 22

        # Add a 2-day weekday holiday (Sun Jul 5 - Mon Jul 6)
        Holiday.objects.create(
            institution=self.inst,
            name="Ashura Holiday",
            type=HolidayType.GOVT,
            start_date=date(2026, 7, 5),
            end_date=date(2026, 7, 6),
        )
        assert count_working_days_in_month(self.inst, 2026, 7) == 20

    def test_attendance_summary_counts_late_half_day_absent_and_leaves(self) -> None:
        session = AcademicSession.objects.create(
            institution=self.inst,
            name="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        paid_type = LeaveType.objects.create(
            institution=self.inst, name="Casual Leave", code="CL", is_paid=True
        )
        unpaid_type = LeaveType.objects.create(
            institution=self.inst, name="Leave Without Pay", code="LWP", is_paid=False
        )
        LeaveRequest.objects.create(
            institution=self.inst,
            staff=self.staff,
            session=session,
            leave_type=paid_type,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            days_count=Decimal("1.0"),
            reason="Family",
            status=LeaveRequestStatus.APPROVED,
        )
        LeaveRequest.objects.create(
            institution=self.inst,
            staff=self.staff,
            session=session,
            leave_type=unpaid_type,
            start_date=date(2026, 7, 2),
            end_date=date(2026, 7, 2),
            days_count=Decimal("1.0"),
            reason="Personal",
            status=LeaveRequestStatus.APPROVED,
        )
        # 4 late days, 1 half day, 1 unexcused absent
        for day_num in (5, 6, 7, 8):
            DailyAttendance.objects.create(
                institution=self.inst,
                date=date(2026, 7, day_num),
                user_type="staff",
                staff=self.staff,
                status=AttendanceStatus.LATE,
            )
        DailyAttendance.objects.create(
            institution=self.inst,
            date=date(2026, 7, 9),
            user_type="staff",
            staff=self.staff,
            status=AttendanceStatus.HALF_DAY,
        )
        DailyAttendance.objects.create(
            institution=self.inst,
            date=date(2026, 7, 12),
            user_type="staff",
            staff=self.staff,
            status=AttendanceStatus.ABSENT,
        )

        summary = get_staff_monthly_attendance_summary(self.inst, self.staff, 2026, 7)
        assert summary["late_days"] == 4
        assert summary["half_days"] == 1
        assert summary["absent_days"] == Decimal("1")
        assert summary["paid_leave_days"] == Decimal("1.0")
        assert summary["unpaid_leave_days"] == Decimal("1.0")
        assert summary["present_days"] == Decimal("4.5")

    def test_payslip_breakdown_with_absence_late_pf_overtime_override_and_loan(self) -> None:
        # Override TDS deduction = 500
        StaffSalaryOverride.objects.create(
            institution=self.inst,
            profile=self.profile,
            component=self.components["TDS"],
            calculation_type=CalculationType.FIXED,
            value=Decimal("500.00"),
        )
        # Custom allowance override = 10% of Gross
        special_comp = SalaryComponent.objects.create(
            institution=self.inst,
            code="SPEC",
            name_en="Special Allowance",
            component_type=ComponentType.EARNING,
            calculation_type=CalculationType.PERCENTAGE_OF_GROSS,
            default_value=Decimal("10.00"),
        )
        StaffSalaryOverride.objects.create(
            institution=self.inst,
            profile=self.profile,
            component=special_comp,
            calculation_type=CalculationType.PERCENTAGE_OF_GROSS,
            value=Decimal("10.00"),
        )
        loan = StaffLoan.objects.create(
            institution=self.inst,
            staff=self.staff,
            loan_type=LoanType.ADVANCE,
            principal_amount=Decimal("5000.00"),
            monthly_installment=Decimal("2000.00"),
            remaining_balance=Decimal("1500.00"),  # Should cap recovery at remaining 1500
            status=LoanStatus.ACTIVE,
        )

        # Basic 20000 + HRA(40%=8000) + MED(1500) + CONV(1000) = 30500 base gross
        # + SPEC (10% of 30500 = 3050) = 33550 regular earnings
        # + Overtime 4 hrs * 250 = 1000 + Bonus 2000 => Gross = 36550.00
        # Absence equiv: 1 absent + 1 unpaid_leave + 3 late (=1 absent) = 3 days out of 20 working days
        # Basic basis absence deduction = 20000 * 3 / 20 = 3000.00
        # PF Emp = 10% of 20000 = 2000.00; PF Employer = 2000.00; TDS = 500.00; Loan = 1500.00
        # Total deductions = 3000 + 2000 + 500 + 1500 = 7000.00; Net = 36550 - 7000 = 29550.00
        breakdown = calculate_payslip_breakdown(
            profile=self.profile,
            working_days=20,
            attendance_summary={
                "absent_days": Decimal("1"),
                "unpaid_leave_days": Decimal("1"),
                "half_days": 0,
                "late_days": 3,
            },
            absence_deduction_basis=AbsenceDeductionBasis.BASIC,
            active_loans=[loan],
            overtime_hours=Decimal("4.00"),
            bonus_amount=Decimal("2000.00"),
        )

        assert breakdown["gross_earnings"] == Decimal("36550.00")
        assert breakdown["absence_deduction_amount"] == Decimal("3000.00")
        assert breakdown["pf_employee_amount"] == Decimal("2000.00")
        assert breakdown["pf_employer_amount"] == Decimal("2000.00")
        assert breakdown["loan_deduction_amount"] == Decimal("1500.00")
        assert breakdown["total_deductions"] == Decimal("7000.00")
        assert breakdown["net_payable"] == Decimal("29550.00")
