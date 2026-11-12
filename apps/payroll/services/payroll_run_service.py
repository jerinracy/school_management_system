"""Monthly payroll batch generation, festival bonus, workflow, and loan settlement."""

import calendar
import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.institutions.models import Institution
from apps.payroll.models import (
    AbsenceDeductionBasis,
    ComponentType,
    LoanStatus,
    PayrollRun,
    PayrollRunStatus,
    Payslip,
    PayslipLine,
    StaffLoan,
    StaffSalaryProfile,
)
from apps.payroll.services.payroll_calculator import (
    calculate_payslip_breakdown,
    count_working_days_in_month,
    get_staff_monthly_attendance_summary,
    q2,
)
from apps.staff.models import StaffStatus

logger = logging.getLogger(__name__)


def _recalculate_run_totals(payroll_run: PayrollRun) -> PayrollRun:
    """Recompute aggregate totals on PayrollRun from its Payslip rows."""
    agg = payroll_run.payslips.aggregate(
        total_gross=Sum("gross_earnings"),
        total_deductions=Sum("total_deductions"),
        total_net_pay=Sum("net_payable"),
        total_employer_pf=Sum("pf_employer_amount"),
    )
    payroll_run.total_gross = agg["total_gross"] or Decimal("0.00")
    payroll_run.total_deductions = agg["total_deductions"] or Decimal("0.00")
    payroll_run.total_net_pay = agg["total_net_pay"] or Decimal("0.00")
    payroll_run.total_employer_pf = agg["total_employer_pf"] or Decimal("0.00")
    payroll_run.save(
        update_fields=[
            "total_gross",
            "total_deductions",
            "total_net_pay",
            "total_employer_pf",
            "updated_at",
        ]
    )
    return payroll_run


def _rebuild_payslip_from_breakdown(
    institution: Institution,
    payroll_run: PayrollRun,
    profile: StaffSalaryProfile,
    overtime_hours: Decimal = Decimal("0.00"),
    bonus_amount: Decimal = Decimal("0.00"),
    bonus_notes: str = "",
) -> Payslip:
    """Calculate and persist a single Payslip and its PayslipLines."""
    summary = get_staff_monthly_attendance_summary(
        institution=institution,
        staff=profile.staff,
        year=payroll_run.year,
        month=payroll_run.month,
    )
    active_loans = list(
        StaffLoan.objects.filter(
            institution=institution,
            staff=profile.staff,
            status=LoanStatus.ACTIVE,
            is_deleted=False,
            remaining_balance__gt=Decimal("0.00"),
        ).order_by("disbursed_date", "created_at")
    )

    breakdown = calculate_payslip_breakdown(
        profile=profile,
        working_days=payroll_run.working_days_in_month,
        attendance_summary=summary,
        absence_deduction_basis=payroll_run.absence_deduction_basis,
        active_loans=active_loans,
        overtime_hours=overtime_hours,
        bonus_amount=bonus_amount,
        bonus_notes=bonus_notes,
    )

    payslip, _ = Payslip.objects.update_or_create(
        institution=institution,
        payroll_run=payroll_run,
        staff=profile.staff,
        defaults={
            "working_days": payroll_run.working_days_in_month,
            "present_days": summary["present_days"],
            "late_days": summary["late_days"],
            "half_days": summary["half_days"],
            "paid_leave_days": summary["paid_leave_days"],
            "unpaid_leave_days": summary["unpaid_leave_days"],
            "absent_days": summary["absent_days"],
            "overtime_hours": overtime_hours,
            "basic_salary": breakdown["basic_salary"],
            "overtime_amount": breakdown["overtime_amount"],
            "bonus_amount": breakdown["bonus_amount"],
            "gross_earnings": breakdown["gross_earnings"],
            "absence_deduction_amount": breakdown["absence_deduction_amount"],
            "pf_employee_amount": breakdown["pf_employee_amount"],
            "pf_employer_amount": breakdown["pf_employer_amount"],
            "loan_deduction_amount": breakdown["loan_deduction_amount"],
            "total_deductions": breakdown["total_deductions"],
            "net_payable": breakdown["net_payable"],
            "payment_method": profile.payment_method,
            "notes": bonus_notes,
        },
    )

    payslip.lines.all().delete()
    PayslipLine.objects.bulk_create(
        [
            PayslipLine(
                institution=institution,
                payslip=payslip,
                component=line["component"],
                name_en=line["name_en"],
                name_bn=line["name_bn"],
                line_type=line["line_type"],
                amount=line["amount"],
                notes=line["notes"],
            )
            for line in breakdown["lines"]
        ]
    )
    return payslip


@transaction.atomic
def generate_payroll_run(
    institution: Institution,
    year: int,
    month: int,
    user: User | None = None,
    working_days_in_month: int | None = None,
    absence_deduction_basis: str = AbsenceDeductionBasis.BASIC,
    title: str = "",
) -> PayrollRun:
    """Create or recalculate a DRAFT monthly PayrollRun for all active profiled staff."""
    existing = PayrollRun.objects.filter(
        institution=institution,
        year=year,
        month=month,
        is_deleted=False,
    ).first()

    if existing:
        if existing.is_locked or existing.status != PayrollRunStatus.DRAFT:
            raise ValidationError(
                f"Payroll for {year}-{month:02d} is '{existing.status}' (locked={existing.is_locked}) and cannot be regenerated."
            )
        payroll_run = existing
        if working_days_in_month is not None:
            payroll_run.working_days_in_month = working_days_in_month
        payroll_run.absence_deduction_basis = absence_deduction_basis
        if title:
            payroll_run.title = title
        payroll_run.save()
    else:
        computed_working_days = working_days_in_month or count_working_days_in_month(
            institution=institution,
            year=year,
            month=month,
        )
        month_name = calendar.month_name[month]
        payroll_run = PayrollRun.objects.create(
            institution=institution,
            year=year,
            month=month,
            title=title or f"Salary Sheet - {month_name} {year}",
            status=PayrollRunStatus.DRAFT,
            working_days_in_month=computed_working_days,
            absence_deduction_basis=absence_deduction_basis,
            prepared_by=user,
        )

    existing_adjustments: dict[Any, tuple[Decimal, Decimal, str]] = {
        p.staff_id: (p.overtime_hours, p.bonus_amount, p.notes) for p in payroll_run.payslips.all()
    }

    profiles = (
        StaffSalaryProfile.objects.filter(
            institution=institution,
            is_deleted=False,
            is_active=True,
            staff__is_deleted=False,
            staff__status=StaffStatus.ACTIVE,
        )
        .select_related("staff", "structure")
        .prefetch_related("structure__lines__component", "overrides__component")
    )

    if not profiles.exists():
        raise ValidationError("No active staff salary profiles found for this institution.")

    active_staff_ids = []
    for profile in profiles:
        active_staff_ids.append(profile.staff_id)
        ot_hrs, bonus_amt, b_notes = existing_adjustments.get(
            profile.staff_id, (Decimal("0.00"), Decimal("0.00"), "")
        )
        _rebuild_payslip_from_breakdown(
            institution=institution,
            payroll_run=payroll_run,
            profile=profile,
            overtime_hours=ot_hrs,
            bonus_amount=bonus_amt,
            bonus_notes=b_notes,
        )

    # Remove payslips for staff who are no longer active/profiled in draft recalculation
    payroll_run.payslips.exclude(staff_id__in=active_staff_ids).delete()
    return _recalculate_run_totals(payroll_run)


def _sync_bonus_line_on_payslip(
    payroll_run: PayrollRun,
    payslip: Payslip,
    new_bonus: Decimal,
    bonus_title: str,
) -> None:
    """Create, update, or remove the bonus line item on a Payslip."""
    bonus_line = payslip.lines.filter(
        component__isnull=True,
        line_type=ComponentType.EARNING,
        name_en="Festival / Performance Bonus",
    ).first()
    if new_bonus > Decimal("0.00"):
        if bonus_line:
            bonus_line.amount = new_bonus
            bonus_line.notes = bonus_title
            bonus_line.save(update_fields=["amount", "notes", "updated_at"])
        else:
            PayslipLine.objects.create(
                institution=payroll_run.institution,
                payslip=payslip,
                component=None,
                name_en="Festival / Performance Bonus",
                name_bn="উৎসব / বিশেষ বোনাস",
                line_type=ComponentType.EARNING,
                amount=new_bonus,
                notes=bonus_title,
            )
    elif bonus_line:
        bonus_line.delete()


@transaction.atomic
def apply_bonus_to_run(
    payroll_run: PayrollRun,
    bonus_title: str = "Eid Festival Bonus",
    percentage_of_basic: Decimal | None = None,
    fixed_amount: Decimal | None = None,
    staff_type: str | None = None,
) -> PayrollRun:
    """Apply a batch festival/Eid bonus across a DRAFT PayrollRun."""
    if payroll_run.is_locked or payroll_run.status != PayrollRunStatus.DRAFT:
        raise ValidationError("Bonuses can only be applied while payroll run is in DRAFT status.")
    if percentage_of_basic is None and fixed_amount is None:
        raise ValidationError("Specify either percentage_of_basic or fixed_amount.")
    if (percentage_of_basic is not None and percentage_of_basic < Decimal("0.00")) or (
        fixed_amount is not None and fixed_amount < Decimal("0.00")
    ):
        raise ValidationError("Bonus value cannot be negative.")

    payslips = payroll_run.payslips.select_related("staff").all()
    if staff_type:
        payslips = payslips.filter(staff__staff_type=staff_type)

    for payslip in payslips:
        new_bonus = (
            q2((payslip.basic_salary * percentage_of_basic) / Decimal("100"))
            if percentage_of_basic is not None
            else q2(fixed_amount or Decimal("0.00"))
        )
        delta = new_bonus - payslip.bonus_amount
        payslip.bonus_amount = new_bonus
        payslip.gross_earnings = q2(payslip.gross_earnings + delta)
        payslip.net_payable = max(
            Decimal("0.00"), q2(payslip.gross_earnings - payslip.total_deductions)
        )
        payslip.notes = bonus_title
        payslip.save(
            update_fields=[
                "bonus_amount",
                "gross_earnings",
                "net_payable",
                "notes",
                "updated_at",
            ]
        )
        _sync_bonus_line_on_payslip(payroll_run, payslip, new_bonus, bonus_title)

    return _recalculate_run_totals(payroll_run)


@transaction.atomic
def review_payroll_run(payroll_run: PayrollRun, user: User) -> PayrollRun:
    """Move a DRAFT PayrollRun to REVIEWED."""
    if payroll_run.is_locked or payroll_run.status != PayrollRunStatus.DRAFT:
        raise ValidationError("Only unlocked DRAFT payroll runs can be marked as reviewed.")
    if not payroll_run.payslips.exists():
        raise ValidationError("Cannot review a payroll run with no payslips.")

    payroll_run.status = PayrollRunStatus.REVIEWED
    payroll_run.reviewed_by = user
    payroll_run.reviewed_at = timezone.now()
    payroll_run.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    logger.info("PayrollRun %s reviewed by user %s", payroll_run.id, user.id)
    return payroll_run


@transaction.atomic
def approve_payroll_run(payroll_run: PayrollRun, user: User) -> PayrollRun:
    """Approve a DRAFT or REVIEWED PayrollRun for disbursement."""
    if payroll_run.is_locked:
        raise ValidationError("Locked payroll runs cannot be modified.")
    if payroll_run.status not in (PayrollRunStatus.DRAFT, PayrollRunStatus.REVIEWED):
        raise ValidationError(
            f"Payroll run must be DRAFT or REVIEWED to approve (current: {payroll_run.status})."
        )
    if not payroll_run.payslips.exists():
        raise ValidationError("Cannot approve a payroll run with no payslips.")

    payroll_run.status = PayrollRunStatus.APPROVED
    payroll_run.approved_by = user
    payroll_run.approved_at = timezone.now()
    payroll_run.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    logger.info("PayrollRun %s approved by user %s", payroll_run.id, user.id)
    return payroll_run


@transaction.atomic
def mark_payroll_run_paid(
    payroll_run: PayrollRun,
    user: User,
    payment_reference: str = "",
) -> PayrollRun:
    """Disburse an APPROVED PayrollRun and settle deducted StaffLoan installments."""
    if payroll_run.is_locked:
        raise ValidationError("Locked payroll runs cannot be modified.")
    if payroll_run.status != PayrollRunStatus.APPROVED:
        raise ValidationError("Payroll run must be APPROVED before marking as PAID.")

    now = timezone.now()
    payslips = list(payroll_run.payslips.select_related("staff").all())

    # Settle active loans up to each payslip's loan_deduction_amount atomically
    for payslip in payslips:
        remaining_to_settle = payslip.loan_deduction_amount
        if remaining_to_settle > Decimal("0.00"):
            active_loans = (
                StaffLoan.objects.select_for_update()
                .filter(
                    institution=payroll_run.institution,
                    staff=payslip.staff,
                    status=LoanStatus.ACTIVE,
                    is_deleted=False,
                    remaining_balance__gt=Decimal("0.00"),
                )
                .order_by("disbursed_date", "created_at")
            )
            for loan in active_loans:
                if remaining_to_settle <= Decimal("0.00"):
                    break
                recover = min(
                    loan.monthly_installment,
                    loan.remaining_balance,
                    remaining_to_settle,
                )
                if recover > Decimal("0.00"):
                    loan.total_recovered = q2(loan.total_recovered + recover)
                    loan.remaining_balance = q2(loan.remaining_balance - recover)
                    if loan.remaining_balance <= Decimal("0.00"):
                        loan.remaining_balance = Decimal("0.00")
                        loan.status = LoanStatus.COMPLETED
                    loan.save(
                        update_fields=[
                            "total_recovered",
                            "remaining_balance",
                            "status",
                            "updated_at",
                        ]
                    )
                    remaining_to_settle = q2(remaining_to_settle - recover)

        payslip.is_paid = True
        payslip.paid_at = now
        if payment_reference:
            payslip.payment_reference = payment_reference
        payslip.save(update_fields=["is_paid", "paid_at", "payment_reference", "updated_at"])

    payroll_run.status = PayrollRunStatus.PAID
    payroll_run.paid_at = now
    payroll_run.save(update_fields=["status", "paid_at", "updated_at"])
    logger.info("PayrollRun %s marked PAID by user %s", payroll_run.id, user.id)
    return payroll_run


@transaction.atomic
def lock_payroll_run(payroll_run: PayrollRun, user: User) -> PayrollRun:
    """Permanently lock a PAID PayrollRun to prevent post-disbursement edits."""
    if payroll_run.is_locked or payroll_run.status == PayrollRunStatus.LOCKED:
        raise ValidationError("Payroll run is already locked.")
    if payroll_run.status != PayrollRunStatus.PAID:
        raise ValidationError("Only PAID payroll runs can be locked.")

    payroll_run.status = PayrollRunStatus.LOCKED
    payroll_run.is_locked = True
    payroll_run.save(update_fields=["status", "is_locked", "updated_at"])
    logger.info("PayrollRun %s locked by user %s", payroll_run.id, user.id)
    return payroll_run
