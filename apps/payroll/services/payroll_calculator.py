"""Pure salary breakdown, working-day, and attendance-integration calculator."""

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from apps.attendance.models import AttendanceStatus, DailyAttendance
from apps.institutions.models import Branch, Holiday, Institution
from apps.payroll.models import (
    AbsenceDeductionBasis,
    CalculationType,
    ComponentType,
    LoanStatus,
    StaffLoan,
    StaffSalaryProfile,
)
from apps.staff.models import LeaveRequest, LeaveRequestStatus, Staff

TWO_DP = Decimal("0.01")

WEEKDAY_NAME_TO_INT = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def q2(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using standard half-up rounding."""
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def _resolve_weekend_ints(institution: Institution) -> set[int]:
    """Convert Institution.weekend_days configuration into Python weekday integers (0=Mon..6=Sun)."""
    raw = getattr(institution, "weekend_days", None)
    if not raw:
        return {4, 5}
    result: set[int] = set()
    for item in raw:
        if isinstance(item, int):
            result.add(item)
        elif isinstance(item, str):
            mapped = WEEKDAY_NAME_TO_INT.get(item.strip().lower())
            if mapped is not None:
                result.add(mapped)
    return result or {4, 5}


def count_working_days_in_month(
    institution: Institution,
    year: int,
    month: int,
    branch: Branch | None = None,
) -> int:
    """Count scheduled working days in a month excluding institution weekends and holidays."""
    _, num_days = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    weekend_ints = _resolve_weekend_ints(institution)

    holiday_qs = Holiday.objects.filter(
        institution=institution,
        start_date__lte=month_end,
        end_date__gte=month_start,
    )
    holiday_dates: set[date] = set()
    for hol in holiday_qs.prefetch_related("branches"):
        if not hol.applies_to_all_branches and branch is not None:
            if not hol.branches.filter(pk=branch.pk).exists():
                continue
        cur = max(hol.start_date, month_start)
        end = min(hol.end_date, month_end)
        while cur <= end:
            holiday_dates.add(cur)
            cur += timedelta(days=1)

    working = sum(
        1
        for day_num in range(1, num_days + 1)
        if date(year, month, day_num).weekday() not in weekend_ints
        and date(year, month, day_num) not in holiday_dates
    )
    return working if working > 0 else 26


def _collect_approved_leave_dates(
    institution: Institution,
    staff: Staff,
    month_start: date,
    month_end: date,
) -> tuple[set[date], set[date]]:
    """Collect sets of approved paid and unpaid leave dates falling inside the month."""
    paid_leave_dates: set[date] = set()
    unpaid_leave_dates: set[date] = set()

    approved_leaves = LeaveRequest.objects.filter(
        institution=institution,
        staff=staff,
        status=LeaveRequestStatus.APPROVED,
        start_date__lte=month_end,
        end_date__gte=month_start,
    ).select_related("leave_type")

    for leave in approved_leaves:
        cur = max(leave.start_date, month_start)
        end = min(leave.end_date, month_end)
        target_set = paid_leave_dates if leave.leave_type.is_paid else unpaid_leave_dates
        while cur <= end:
            target_set.add(cur)
            cur += timedelta(days=1)
    return paid_leave_dates, unpaid_leave_dates


def get_staff_monthly_attendance_summary(
    institution: Institution,
    staff: Staff,
    year: int,
    month: int,
) -> dict[str, Any]:
    """Aggregate attendance and approved paid/unpaid leaves for a staff member in a month."""
    _, num_days = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)
    paid_leave_dates, unpaid_leave_dates = _collect_approved_leave_dates(
        institution, staff, month_start, month_end
    )

    records = DailyAttendance.objects.filter(
        institution=institution,
        user_type="staff",
        staff=staff,
        is_deleted=False,
        date__range=(month_start, month_end),
    )

    present_days = Decimal("0.0")
    late_days = 0
    half_days = 0
    absent_days = 0
    leave_dates_seen: set[date] = set()
    counted_paid_leave = Decimal("0.0")
    counted_unpaid_leave = Decimal("0.0")

    for rec in records:
        if rec.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            present_days += Decimal("1.0")
            late_days += 1 if rec.status == AttendanceStatus.LATE else 0
        elif rec.status == AttendanceStatus.HALF_DAY:
            present_days += Decimal("0.5")
            half_days += 1
        elif rec.status == AttendanceStatus.ABSENT:
            if rec.date in paid_leave_dates:
                leave_dates_seen.add(rec.date)
                counted_paid_leave += Decimal("1.0")
            elif rec.date in unpaid_leave_dates:
                leave_dates_seen.add(rec.date)
                counted_unpaid_leave += Decimal("1.0")
            else:
                absent_days += 1
        elif rec.status == AttendanceStatus.LEAVE:
            leave_dates_seen.add(rec.date)
            if rec.date in unpaid_leave_dates:
                counted_unpaid_leave += Decimal("1.0")
            else:
                counted_paid_leave += Decimal("1.0")

    counted_paid_leave += Decimal(len(paid_leave_dates - leave_dates_seen))
    counted_unpaid_leave += Decimal(len(unpaid_leave_dates - leave_dates_seen))

    return {
        "present_days": present_days,
        "late_days": late_days,
        "half_days": half_days,
        "paid_leave_days": counted_paid_leave,
        "unpaid_leave_days": counted_unpaid_leave,
        "absent_days": Decimal(absent_days),
    }


def _evaluate_formula(
    calc_type: str,
    value: Decimal,
    basic_salary: Decimal,
    base_gross: Decimal,
) -> Decimal:
    """Compute a component amount given its calculation type and parameter value."""
    if calc_type == CalculationType.PERCENTAGE_OF_BASIC:
        return q2(basic_salary * value / Decimal("100"))
    if calc_type == CalculationType.PERCENTAGE_OF_GROSS:
        return q2(base_gross * value / Decimal("100"))
    return q2(value)


def _resolve_effective_component_specs(profile: StaffSalaryProfile) -> list[dict[str, Any]]:
    """Merge SalaryStructure lines with per-employee StaffSalaryOverrides."""
    effective_specs: dict[str, dict[str, Any]] = {}
    if profile.structure is not None:
        for line in profile.structure.lines.select_related("component").all():
            if not line.component.is_active or line.component.is_deleted:
                continue
            effective_specs[line.component.code] = {
                "component": line.component,
                "calculation_type": line.calculation_type,
                "value": line.value,
            }

    for ovr in profile.overrides.select_related("component").all():
        if not ovr.component.is_active or ovr.component.is_deleted:
            continue
        effective_specs[ovr.component.code] = {
            "component": ovr.component,
            "calculation_type": ovr.calculation_type,
            "value": ovr.value,
        }

    return sorted(
        effective_specs.values(),
        key=lambda item: (
            item["component"].component_type,
            item["component"].display_order,
            item["component"].code,
        ),
    )


def _compute_earnings(
    profile: StaffSalaryProfile,
    ordered_specs: list[dict[str, Any]],
    basic_salary: Decimal,
    overtime_hours: Decimal,
    bonus_amount: Decimal,
    bonus_notes: str,
) -> tuple[list[dict[str, Any]], Decimal, Decimal, Decimal, Decimal]:
    """Build earning lines and compute regular earnings, overtime, bonus, and gross earnings."""
    earning_lines: list[dict[str, Any]] = [
        {
            "component": None,
            "code": "BASIC",
            "name_en": "Basic Salary",
            "name_bn": "মূল বেতন",
            "line_type": ComponentType.EARNING,
            "amount": basic_salary,
            "notes": "",
        }
    ]
    regular_earnings = basic_salary
    deferred: list[dict[str, Any]] = []

    for spec in ordered_specs:
        comp = spec["component"]
        if comp.component_type != ComponentType.EARNING or comp.code == "BASIC":
            continue
        if spec["calculation_type"] == CalculationType.PERCENTAGE_OF_GROSS:
            deferred.append(spec)
            continue
        amt = _evaluate_formula(spec["calculation_type"], spec["value"], basic_salary, basic_salary)
        if amt > Decimal("0.00"):
            regular_earnings += amt
            earning_lines.append(
                {
                    "component": comp,
                    "code": comp.code,
                    "name_en": comp.name_en,
                    "name_bn": comp.name_bn,
                    "line_type": ComponentType.EARNING,
                    "amount": amt,
                    "notes": "",
                }
            )

    for spec in deferred:
        comp = spec["component"]
        amt = _evaluate_formula(
            spec["calculation_type"], spec["value"], basic_salary, regular_earnings
        )
        if amt > Decimal("0.00"):
            regular_earnings += amt
            earning_lines.append(
                {
                    "component": comp,
                    "code": comp.code,
                    "name_en": comp.name_en,
                    "name_bn": comp.name_bn,
                    "line_type": ComponentType.EARNING,
                    "amount": amt,
                    "notes": "",
                }
            )

    overtime_amt = q2(overtime_hours * profile.overtime_hourly_rate)
    if overtime_amt > Decimal("0.00"):
        earning_lines.append(
            {
                "component": None,
                "code": "OVERTIME",
                "name_en": "Overtime Allowance",
                "name_bn": "অতিরিক্ত সময় ভাতা",
                "line_type": ComponentType.EARNING,
                "amount": overtime_amt,
                "notes": f"{overtime_hours} hrs @ ৳{profile.overtime_hourly_rate}/hr",
            }
        )

    bonus_amt = q2(bonus_amount)
    if bonus_amt > Decimal("0.00"):
        earning_lines.append(
            {
                "component": None,
                "code": "BONUS",
                "name_en": "Festival / Performance Bonus",
                "name_bn": "উৎসব / বিশেষ বোনাস",
                "line_type": ComponentType.EARNING,
                "amount": bonus_amt,
                "notes": bonus_notes,
            }
        )

    gross_earnings = q2(regular_earnings + overtime_amt + bonus_amt)
    return earning_lines, regular_earnings, overtime_amt, bonus_amt, gross_earnings


def _compute_absence_deduction(
    profile: StaffSalaryProfile,
    working_days: int,
    attendance_summary: dict[str, Any],
    absence_deduction_basis: str,
    basic_salary: Decimal,
    regular_earnings: Decimal,
) -> tuple[Decimal, dict[str, Any] | None]:
    """Compute pro-rata absence, LWP, half-day, and late-conversion deduction."""
    absent_days = Decimal(str(attendance_summary.get("absent_days", 0)))
    unpaid_leave_days = Decimal(str(attendance_summary.get("unpaid_leave_days", 0)))
    half_days = int(attendance_summary.get("half_days", 0))
    late_days = int(attendance_summary.get("late_days", 0))

    late_equiv = (
        Decimal(late_days // profile.late_days_per_absent)
        if profile.late_deduction_enabled and profile.late_days_per_absent > 0
        else Decimal("0.0")
    )
    total_absent_equiv = (
        absent_days + unpaid_leave_days + (Decimal(half_days) * Decimal("0.5")) + late_equiv
    )
    if total_absent_equiv <= Decimal("0.0") or working_days <= 0:
        return Decimal("0.00"), None

    basis_amount = (
        regular_earnings if absence_deduction_basis == AbsenceDeductionBasis.GROSS else basic_salary
    )
    capped_days = min(total_absent_equiv, Decimal(working_days))
    amount = q2((basis_amount * capped_days) / Decimal(working_days))
    if amount <= Decimal("0.00"):
        return Decimal("0.00"), None

    line = {
        "component": None,
        "code": "ABSENCE",
        "name_en": "Absence / LWP / Late Deduction",
        "name_bn": "অনুপস্থিতি ও বিলম্ব কর্তন",
        "line_type": ComponentType.DEDUCTION,
        "amount": amount,
        "notes": f"{capped_days} equiv. day(s) of {working_days}",
    }
    return amount, line


def _compute_statutory_and_pf_deductions(
    profile: StaffSalaryProfile,
    ordered_specs: list[dict[str, Any]],
    basic_salary: Decimal,
    regular_earnings: Decimal,
) -> tuple[list[dict[str, Any]], Decimal, Decimal, Decimal]:
    """Compute configured deduction components plus Provident Fund contributions."""
    lines: list[dict[str, Any]] = []
    pf_employee_amount = Decimal("0.00")
    has_explicit_pf = False
    other_deductions_total = Decimal("0.00")

    for spec in ordered_specs:
        comp = spec["component"]
        if comp.component_type != ComponentType.DEDUCTION or comp.code in ("ABSENCE", "LOAN_REC"):
            continue
        amt = _evaluate_formula(
            spec["calculation_type"], spec["value"], basic_salary, regular_earnings
        )
        if comp.code == "PF_EMP":
            has_explicit_pf = True
            pf_employee_amount = amt
        if amt > Decimal("0.00"):
            other_deductions_total += amt
            lines.append(
                {
                    "component": comp,
                    "code": comp.code,
                    "name_en": comp.name_en,
                    "name_bn": comp.name_bn,
                    "line_type": ComponentType.DEDUCTION,
                    "amount": amt,
                    "notes": "",
                }
            )

    pf_employer_amount = Decimal("0.00")
    if profile.pf_enrolled:
        if not has_explicit_pf and profile.pf_employee_percent > Decimal("0.00"):
            pf_employee_amount = q2((basic_salary * profile.pf_employee_percent) / Decimal("100"))
            if pf_employee_amount > Decimal("0.00"):
                other_deductions_total += pf_employee_amount
                lines.append(
                    {
                        "component": None,
                        "code": "PF_EMP",
                        "name_en": "Provident Fund (Employee)",
                        "name_bn": "ভবিষ্যৎ তহবিল (কর্মী)",
                        "line_type": ComponentType.DEDUCTION,
                        "amount": pf_employee_amount,
                        "notes": f"{profile.pf_employee_percent}% of Basic",
                    }
                )
        if profile.pf_employer_percent > Decimal("0.00"):
            pf_employer_amount = q2((basic_salary * profile.pf_employer_percent) / Decimal("100"))

    return lines, pf_employee_amount, pf_employer_amount, q2(other_deductions_total)


def _compute_loan_recoveries(
    active_loans: list[StaffLoan] | None,
    available_for_loan: Decimal,
) -> tuple[Decimal, list[tuple[StaffLoan, Decimal]], dict[str, Any] | None]:
    """Compute installment recoveries for active loans capped by balance and disposable pay."""
    if not active_loans or available_for_loan <= Decimal("0.00"):
        return Decimal("0.00"), [], None

    loan_deduction_amount = Decimal("0.00")
    loan_recoveries: list[tuple[StaffLoan, Decimal]] = []
    for loan in active_loans:
        if loan.status != LoanStatus.ACTIVE or loan.remaining_balance <= Decimal("0.00"):
            continue
        installment = q2(
            min(
                loan.monthly_installment,
                loan.remaining_balance,
                available_for_loan - loan_deduction_amount,
            )
        )
        if installment > Decimal("0.00"):
            loan_deduction_amount += installment
            loan_recoveries.append((loan, installment))
        if loan_deduction_amount >= available_for_loan:
            break

    if loan_deduction_amount <= Decimal("0.00"):
        return Decimal("0.00"), [], None

    line = {
        "component": None,
        "code": "LOAN_REC",
        "name_en": "Loan / Advance Recovery",
        "name_bn": "ঋণ / অগ্রিম কর্তন",
        "line_type": ComponentType.DEDUCTION,
        "amount": loan_deduction_amount,
        "notes": f"{len(loan_recoveries)} active loan/advance(s)",
    }
    return q2(loan_deduction_amount), loan_recoveries, line


def calculate_payslip_breakdown(
    profile: StaffSalaryProfile,
    working_days: int,
    attendance_summary: dict[str, Any],
    absence_deduction_basis: str = AbsenceDeductionBasis.BASIC,
    active_loans: list[StaffLoan] | None = None,
    overtime_hours: Decimal = Decimal("0.00"),
    bonus_amount: Decimal = Decimal("0.00"),
    bonus_notes: str = "",
) -> dict[str, Any]:
    """Compute itemized earnings, deductions, PF, loan recoveries, and net payable."""
    basic_salary = q2(profile.basic_salary)
    ordered_specs = _resolve_effective_component_specs(profile)

    earning_lines, regular_earnings, overtime_amt, bonus_amt, gross_earnings = _compute_earnings(
        profile, ordered_specs, basic_salary, overtime_hours, bonus_amount, bonus_notes
    )

    deduction_lines: list[dict[str, Any]] = []
    absence_deduction_amount, abs_line = _compute_absence_deduction(
        profile,
        working_days,
        attendance_summary,
        absence_deduction_basis,
        basic_salary,
        regular_earnings,
    )
    if abs_line:
        deduction_lines.append(abs_line)

    stat_lines, pf_emp_amt, pf_empr_amt, other_deductions_total = (
        _compute_statutory_and_pf_deductions(profile, ordered_specs, basic_salary, regular_earnings)
    )
    deduction_lines.extend(stat_lines)

    available_for_loan = max(
        Decimal("0.00"),
        q2(gross_earnings - absence_deduction_amount - other_deductions_total),
    )
    loan_deduction_amount, loan_recoveries, loan_line = _compute_loan_recoveries(
        active_loans, available_for_loan
    )
    if loan_line:
        deduction_lines.append(loan_line)

    total_deductions = q2(absence_deduction_amount + other_deductions_total + loan_deduction_amount)
    net_payable = max(Decimal("0.00"), q2(gross_earnings - total_deductions))

    return {
        "basic_salary": basic_salary,
        "overtime_amount": overtime_amt,
        "bonus_amount": bonus_amt,
        "gross_earnings": gross_earnings,
        "absence_deduction_amount": absence_deduction_amount,
        "pf_employee_amount": pf_emp_amt,
        "pf_employer_amount": pf_empr_amt,
        "loan_deduction_amount": loan_deduction_amount,
        "total_deductions": total_deductions,
        "net_payable": net_payable,
        "lines": earning_lines + deduction_lines,
        "loan_recoveries": loan_recoveries,
    }
