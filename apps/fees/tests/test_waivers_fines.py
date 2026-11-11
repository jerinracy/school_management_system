"""Unit tests for fee waivers, scholarships, and late payment fine calculations."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.accounts.test_helpers import make_user
from apps.fees.models import (
    DiscountType,
    FeeHead,
    FeeType,
    FineRule,
    FineType,
    Invoice,
    InvoiceStatus,
    RecurrenceType,
    StudentWaiver,
    WaiverApprovalStatus,
    WaiverCategory,
    WaiverRule,
)
from apps.fees.services import (
    apply_invoice_fine,
    approve_student_waiver,
    calculate_applicable_waiver,
    calculate_invoice_late_fine,
    evaluate_overdue_invoices_batch,
    reject_student_waiver,
)
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import Student


@pytest.fixture
def waiver_fine_data(db: None) -> dict:
    inst = Institution.objects.create(name_en="Waiver Fine Academy", name_bn="ওয়েভার ফাইন একাডেমি")
    session = AcademicSession.objects.create(
        institution=inst,
        name="Session 2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-WF-001",
        name_en="Imtiaz Ahmed",
        name_bn="ইমতিয়াজ আহমেদ",
        admission_date="2026-01-01",
        dob="2010-06-15",
    )
    admin_user = make_user(
        username="wf_admin",
        institution=inst,
        phone="+8801700999888",
    )
    admin_user.is_superuser = True
    admin_user.save()

    fh_tuition = FeeHead.objects.create(
        institution=inst,
        code="TUITION",
        name_en="Tuition Fee",
        name_bn="বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    fh_exam = FeeHead.objects.create(
        institution=inst,
        code="EXAM",
        name_en="Exam Fee",
        name_bn="পরীক্ষার ফি",
        fee_type=FeeType.EXAM,
        recurrence=RecurrenceType.TERMLY,
    )

    return {
        "inst": inst,
        "session": session,
        "student": student,
        "admin_user": admin_user,
        "fh_tuition": fh_tuition,
        "fh_exam": fh_exam,
    }


@pytest.mark.django_db
def test_waiver_lifecycle_and_calculation(waiver_fine_data: dict) -> None:
    data = waiver_fine_data
    inst = data["inst"]
    student = data["student"]
    admin_user = data["admin_user"]
    fh_tuition = data["fh_tuition"]
    fh_exam = data["fh_exam"]

    # 1. Create waiver with pending status
    w_rule = WaiverRule.objects.create(
        institution=inst,
        name="Merit 50% Scholarship",
        category=WaiverCategory.MERIT,
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("50.00"),
        max_discount_amount=Decimal("600.00"),
    )
    sw = StudentWaiver.objects.create(
        institution=inst,
        student=student,
        waiver_rule=w_rule,
        title="Merit 50%",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("50.00"),
        max_discount_amount=Decimal("600.00"),
        status=WaiverApprovalStatus.PENDING,
    )

    # Pending waiver should not calculate any deduction
    ded_pending = calculate_applicable_waiver(student, fh_tuition, Decimal("1500.00"))
    assert ded_pending == Decimal("0.00")

    # 2. Approve waiver
    approved_sw = approve_student_waiver(sw.id, approver=admin_user)
    assert approved_sw.status == WaiverApprovalStatus.APPROVED

    # Now calculates: 50% of 1500 is 750, but capped at max 600.00
    ded_approved = calculate_applicable_waiver(student, fh_tuition, Decimal("1500.00"))
    assert ded_approved == Decimal("600.00")

    # Does not apply to exam fee because default empty fee heads applies to Tuition only
    ded_exam = calculate_applicable_waiver(student, fh_exam, Decimal("800.00"))
    assert ded_exam == Decimal("0.00")

    # 3. Reject waiver workflow
    sw2 = StudentWaiver.objects.create(
        institution=inst,
        student=student,
        title="Invalid Request",
        discount_type=DiscountType.FLAT,
        discount_value=Decimal("300.00"),
        status=WaiverApprovalStatus.PENDING,
    )
    rej = reject_student_waiver(sw2.id, approver=admin_user, reason="Incomplete documents")
    assert rej.status == WaiverApprovalStatus.REJECTED
    assert rej.rejection_reason == "Incomplete documents"


@pytest.mark.django_db
def test_fine_calculations_fixed_and_daily(waiver_fine_data: dict) -> None:
    data = waiver_fine_data
    inst = data["inst"]
    session = data["session"]
    student = data["student"]

    # Rule: 5 days grace, fixed 100 BDT
    rule_fixed = FineRule.objects.create(
        institution=inst,
        name="Fixed 100 BDT Late Fine",
        fine_type=FineType.FIXED,
        grace_period_days=5,
        amount=Decimal("100.00"),
    )

    today = date(2026, 3, 20)
    due = date(2026, 3, 10)  # 10 days overdue

    inv = Invoice.objects.create(
        institution=inst,
        invoice_number="INV-2026-F01",
        student=student,
        session=session,
        subtotal_amount=Decimal("1000.00"),
        total_payable=Decimal("1000.00"),
        due_amount=Decimal("1000.00"),
        status=InvoiceStatus.ISSUED,
        issue_date=date(2026, 3, 1),
        due_date=due,
        fine_rule=rule_fixed,
    )

    # 1. Calculation within grace period (due + 3 days) -> 0 fine
    fine_in_grace = calculate_invoice_late_fine(inv, evaluation_date=due + timedelta(days=3))
    assert fine_in_grace == Decimal("0.00")

    # 2. Calculation past grace period (10 days past due) -> 100 BDT fixed
    fine_past_grace = calculate_invoice_late_fine(inv, evaluation_date=today)
    assert fine_past_grace == Decimal("100.00")

    # Apply fine to invoice
    updated_inv = apply_invoice_fine(inv, evaluation_date=today)
    assert updated_inv.fine_amount == Decimal("100.00")
    assert updated_inv.total_payable == Decimal("1100.00")
    assert updated_inv.due_amount == Decimal("1100.00")
    assert updated_inv.status == InvoiceStatus.OVERDUE

    # 3. Daily accrual rule: 10 BDT per day after 5 days grace, max 200
    rule_daily = FineRule.objects.create(
        institution=inst,
        name="Daily Accrual Fine",
        fine_type=FineType.DAILY,
        grace_period_days=5,
        amount=Decimal("10.00"),
        max_fine_amount=Decimal("200.00"),
    )
    # 15 days overdue -> 15 - 5 = 10 effective days * 10 = 100
    fine_daily = calculate_invoice_late_fine(
        inv, evaluation_date=due + timedelta(days=15), rule=rule_daily
    )
    assert fine_daily == Decimal("100.00")

    # 4. Batch evaluation
    batch_count = evaluate_overdue_invoices_batch(institution_id=inst.id, evaluation_date=today)
    assert batch_count >= 1
