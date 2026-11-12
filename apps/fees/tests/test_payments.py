"""Unit and integration tests for Payment collection and Advance balances."""

from datetime import date, time
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import UserType
from apps.accounts.test_helpers import make_user
from apps.fees.models import (
    AdvanceBalance,
    AdvanceTransaction,
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    MoneyReceipt,
    PaymentAllocation,
    PaymentMethod,
    PaymentStatus,
    RecurrenceType,
)
from apps.fees.services import (
    apply_advance_to_invoice,
    generate_single_student_invoice,
    record_counter_payment,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def fee_payment_fixture(db: None) -> dict:
    client = APIClient()
    inst = Institution.objects.create(name_en="Dhaka Model Academy", name_bn="ঢাকা মডেল একাডেমি")
    branch = Branch.objects.create(institution=inst, name="Main Campus")
    session = AcademicSession.objects.create(
        institution=inst,
        name="Academic Year 2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Day Shift",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 7", code="C7", order=7)
    section = Section.objects.create(
        institution=inst,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )

    admin_user = make_user(
        username="accounts_cashier",
        institution=inst,
        phone="+8801711002233",
    )
    admin_user.is_superuser = True
    admin_user.save()

    student_user = make_user(
        username="student_rahim",
        institution=inst,
        phone="+8801711556677",
        user_type=UserType.STUDENT,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-2026-007",
        name_en="Rahim Uddin",
        name_bn="রহিম উদ্দিন",
        admission_date="2026-01-01",
        dob="2012-05-10",
    )
    student_user.student_profile = student  # type: ignore[attr-defined]
    student_user.save()
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        roll_no=12,
        enrollment_date="2026-01-01",
    )

    fee_tuition = FeeHead.objects.create(
        institution=inst,
        code="TUITION",
        name_en="Monthly Tuition Fee",
        name_bn="মাসিক বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    fee_exam = FeeHead.objects.create(
        institution=inst,
        code="EXAM",
        name_en="Term Exam Fee",
        name_bn="পরীক্ষা ফি",
        fee_type=FeeType.EXAM,
        recurrence=RecurrenceType.TERMLY,
    )

    fee_structure = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=class_level,
        name="Class 7 Standard Fees",
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=fee_structure,
        fee_head=fee_tuition,
        amount=Decimal("1500.00"),
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=fee_structure,
        fee_head=fee_exam,
        amount=Decimal("500.00"),
    )

    invoice = generate_single_student_invoice(
        student=student,
        session=session,
        invoice_type=InvoiceType.MONTHLY,
        billing_year=2026,
        billing_month=3,
        fee_structure=fee_structure,
        due_date=date(2026, 3, 20),
        as_issued=True,
    )

    return {
        "client": client,
        "inst": inst,
        "admin_user": admin_user,
        "student": student,
        "invoice": invoice,
        "fee_tuition": fee_tuition,
        "fee_exam": fee_exam,
    }


@pytest.mark.django_db
def test_record_counter_payment_full_settlement(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    invoice: Invoice = data["invoice"]
    assert invoice.total_payable == Decimal("2000.00")
    assert invoice.due_amount == Decimal("2000.00")

    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("2000.00"),
        payment_method=PaymentMethod.CASH,
        invoice=invoice,
        notes="Cash paid in full at school counter",
    )

    assert payment.status == PaymentStatus.SUCCESSFUL
    assert payment.amount == Decimal("2000.00")
    assert payment.transaction_id.startswith("CASH_")

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.paid_amount == Decimal("2000.00")
    assert invoice.due_amount == Decimal("0.00")
    assert invoice.paid_date == date.today()

    # Verify line item allocations
    allocations = PaymentAllocation.objects.filter(payment=payment)
    assert allocations.count() == 2
    total_allocated = sum(a.allocated_amount for a in allocations)
    assert total_allocated == Decimal("2000.00")

    # Verify money receipt
    receipt = MoneyReceipt.objects.get(payment=payment)
    assert receipt.receipt_number.startswith("REC-2026-")
    assert receipt.total_amount == Decimal("2000.00")
    assert receipt.student == data["student"]


@pytest.mark.django_db
def test_record_counter_payment_partial(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    invoice: Invoice = data["invoice"]

    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1200.00"),
        payment_method=PaymentMethod.BANK,
        invoice=invoice,
        bank_name="Sonali Bank PLC",
        cheque_no="SB-123456",
    )

    assert payment.status == PaymentStatus.SUCCESSFUL
    assert payment.amount == Decimal("1200.00")

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert invoice.paid_amount == Decimal("1200.00")
    assert invoice.due_amount == Decimal("800.00")


@pytest.mark.django_db
def test_record_counter_payment_overpayment_surplus_to_advance(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    invoice: Invoice = data["invoice"]

    # Student pays 2500 for a 2000 invoice (500 surplus)
    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("2500.00"),
        payment_method=PaymentMethod.CASH,
        invoice=invoice,
    )

    assert payment.status == PaymentStatus.SUCCESSFUL
    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.due_amount == Decimal("0.00")
    assert invoice.paid_amount == Decimal("2000.00")

    # Verify student advance balance
    advance = AdvanceBalance.objects.get(student=data["student"])
    assert advance.current_balance == Decimal("500.00")

    tx = AdvanceTransaction.objects.get(advance_balance=advance)
    assert tx.amount == Decimal("500.00")
    assert tx.balance_after == Decimal("500.00")
    assert tx.payment == payment


@pytest.mark.django_db
def test_counter_payment_idempotency_key(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    invoice: Invoice = data["invoice"]
    key = "IDEMP-TEST-KEY-001"

    p1 = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("500.00"),
        payment_method=PaymentMethod.CASH,
        invoice=invoice,
        idempotency_key=key,
    )

    # Calling again with identical key should return p1 without re-allocating
    p2 = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("500.00"),
        payment_method=PaymentMethod.CASH,
        invoice=invoice,
        idempotency_key=key,
    )

    assert p1.id == p2.id
    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("500.00")


@pytest.mark.django_db
def test_apply_advance_to_invoice(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    invoice: Invoice = data["invoice"]

    # Pre-populate advance balance
    advance = AdvanceBalance.objects.create(
        institution=data["inst"],
        student=data["student"],
        current_balance=Decimal("600.00"),
    )
    AdvanceTransaction.objects.create(
        institution=data["inst"],
        advance_balance=advance,
        amount=Decimal("600.00"),
        balance_after=Decimal("600.00"),
        transaction_type="credit_deposit",
        description="Initial advance deposit",
    )

    # Apply 400 from advance to the invoice
    payment = apply_advance_to_invoice(
        student=data["student"],
        invoice=invoice,
        amount=Decimal("400.00"),
    )

    assert payment.payment_method == PaymentMethod.ADVANCE
    assert payment.amount == Decimal("400.00")

    advance.refresh_from_db()
    assert advance.current_balance == Decimal("200.00")

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert invoice.paid_amount == Decimal("400.00")
    assert invoice.due_amount == Decimal("1600.00")


@pytest.mark.django_db
def test_payment_api_counter_endpoint(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    client: APIClient = data["client"]
    client.force_authenticate(user=data["admin_user"])

    payload = {
        "student_id": str(data["student"].id),
        "invoice_id": str(data["invoice"].id),
        "amount": "2000.00",
        "payment_method": "cash",
        "notes": "Counter API payment",
    }
    resp = client.post("/api/v1/fees/payments/counter/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    res_data = resp.json()
    assert res_data["status"] == "successful"
    assert res_data["amount"] == "2000.00"
    assert res_data["receipt_number"] is not None
    assert len(res_data["allocations"]) == 2


@pytest.mark.django_db
def test_daily_collection_endpoint(fee_payment_fixture: dict) -> None:
    data = fee_payment_fixture
    client: APIClient = data["client"]
    client.force_authenticate(user=data["admin_user"])

    # Make a payment first
    record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1000.00"),
        payment_method=PaymentMethod.CASH,
        invoice=data["invoice"],
    )

    today_str = date.today().isoformat()
    resp = client.get(f"/api/v1/fees/payments/daily-collection/?date={today_str}")
    assert resp.status_code == status.HTTP_200_OK
    res_data = resp.json()
    assert res_data["payment_count"] >= 1
    assert Decimal(res_data["total_collected"]) >= Decimal("1000.00")
    assert "cash" in res_data["by_method"]
