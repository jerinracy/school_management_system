"""Unit and integration tests for Money Receipts (PDF & numbering) and Refunds."""

from datetime import date, time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import ClassLevel, Section
from apps.accounts.models import UserType
from apps.accounts.test_helpers import make_user
from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    MoneyReceipt,
    PaymentMethod,
    RecurrenceType,
    RefundStatus,
)
from apps.fees.services import (
    approve_refund,
    generate_money_receipt_pdf,
    generate_single_student_invoice,
    get_next_receipt_number,
    process_refund,
    record_counter_payment,
    reject_refund,
    request_refund,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def receipt_refund_fixture(db: None) -> dict:
    client = APIClient()
    inst = Institution.objects.create(name_en="Sylhet Public School", name_bn="সিলেট পাবলিক স্কুল")
    branch = Branch.objects.create(institution=inst, name="Campus")
    session = AcademicSession.objects.create(
        institution=inst,
        name="Session 2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    shift = Shift.objects.create(
        institution=inst,
        branch=branch,
        name="Morning",
        start_time=time(8, 0),
        end_time=time(13, 0),
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 9", code="C9", order=9)
    section = Section.objects.create(
        institution=inst,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Science A",
    )

    admin_user = make_user(
        username="receipt_admin",
        institution=inst,
        phone="+8801811223344",
    )
    admin_user.is_superuser = True
    admin_user.save()

    student_user = make_user(
        username="stu_tanvir",
        institution=inst,
        phone="+8801811554433",
        user_type=UserType.STUDENT,
    )
    student = Student.objects.create(
        institution=inst,
        student_id="STU-2026-099",
        name_en="Tanvir Ahmed",
        name_bn="তানভীর আহমেদ",
        admission_date="2026-01-01",
        dob="2010-08-20",
    )
    student_user.student_profile = student  # type: ignore[attr-defined]
    student_user.save()
    StudentEnrollment.objects.create(
        institution=inst,
        student=student,
        session=session,
        class_level=class_level,
        section=section,
        roll_no=3,
        enrollment_date="2026-01-01",
    )

    fee_head = FeeHead.objects.create(
        institution=inst,
        code="TUITION_9",
        name_en="Class 9 Tuition Fee",
        name_bn="নবম শ্রেণির বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    structure = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=class_level,
        name="Class 9 Science Fees",
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=structure,
        fee_head=fee_head,
        amount=Decimal("1800.00"),
    )

    invoice = generate_single_student_invoice(
        student=student,
        session=session,
        invoice_type=InvoiceType.MONTHLY,
        billing_year=2026,
        billing_month=5,
        fee_structure=structure,
        due_date=date(2026, 5, 25),
        as_issued=True,
    )

    return {
        "client": client,
        "inst": inst,
        "admin_user": admin_user,
        "student": student,
        "invoice": invoice,
    }


@pytest.mark.django_db
def test_receipt_sequence_gap_free(receipt_refund_fixture: dict) -> None:
    inst = receipt_refund_fixture["inst"]
    r1 = get_next_receipt_number(inst, 2026)
    r2 = get_next_receipt_number(inst, 2026)
    r3 = get_next_receipt_number(inst, 2026)

    assert r1 == "REC-2026-000001"
    assert r2 == "REC-2026-000002"
    assert r3 == "REC-2026-000003"


@pytest.mark.django_db
def test_money_receipt_pdf_generation(receipt_refund_fixture: dict) -> None:
    data = receipt_refund_fixture
    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1800.00"),
        payment_method=PaymentMethod.CASH,
        invoice=data["invoice"],
    )

    receipt = MoneyReceipt.objects.get(payment=payment)
    pdf_bytes = generate_money_receipt_pdf(receipt)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


@pytest.mark.django_db
def test_money_receipt_pdf_download_endpoint(receipt_refund_fixture: dict) -> None:
    data = receipt_refund_fixture
    client: APIClient = data["client"]
    client.force_authenticate(user=data["admin_user"])

    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1800.00"),
        payment_method=PaymentMethod.CASH,
        invoice=data["invoice"],
    )
    receipt = MoneyReceipt.objects.get(payment=payment)

    resp = client.get(f"/api/v1/fees/receipts/{receipt.id}/pdf/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_refund_lifecycle_unwinds_invoice(receipt_refund_fixture: dict) -> None:
    data = receipt_refund_fixture
    invoice: Invoice = data["invoice"]

    # 1. Pay invoice in full
    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1800.00"),
        payment_method=PaymentMethod.CASH,
        invoice=invoice,
    )
    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.due_amount == Decimal("0.00")

    # 2. Request partial refund of 600
    refund = request_refund(
        payment=payment,
        amount=Decimal("600.00"),
        reason="Mistaken duplicate tuition collection",
        requested_by=data["admin_user"],
    )
    assert refund.status == RefundStatus.PENDING

    # 3. Approve refund
    approve_refund(refund, approved_by=data["admin_user"])
    assert refund.status == RefundStatus.APPROVED

    # 4. Process refund
    processed = process_refund(refund, processed_by=data["admin_user"])
    assert processed.status == RefundStatus.PROCESSED
    assert processed.processed_at is not None

    # Verify invoice allocations unwound
    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert invoice.paid_amount == Decimal("1200.00")
    assert invoice.due_amount == Decimal("600.00")


@pytest.mark.django_db
def test_refund_reject(receipt_refund_fixture: dict) -> None:
    data = receipt_refund_fixture
    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1800.00"),
        payment_method=PaymentMethod.CASH,
        invoice=data["invoice"],
    )

    refund = request_refund(
        payment=payment,
        amount=Decimal("500.00"),
        reason="Requested waiver late",
        requested_by=data["admin_user"],
    )

    rejected = reject_refund(
        refund=refund,
        rejected_by=data["admin_user"],
        rejection_reason="Waivers cannot be applied retroactively after final term",
    )
    assert rejected.status == RefundStatus.REJECTED
    assert rejected.rejection_reason != ""


@pytest.mark.django_db
def test_refund_amount_exceeding_payment_raises_error(receipt_refund_fixture: dict) -> None:
    data = receipt_refund_fixture
    payment = record_counter_payment(
        institution=data["inst"],
        collected_by=data["admin_user"],
        student=data["student"],
        amount=Decimal("1800.00"),
        payment_method=PaymentMethod.CASH,
        invoice=data["invoice"],
    )

    with pytest.raises(ValidationError):
        request_refund(
            payment=payment,
            amount=Decimal("2500.00"),  # > 1800
            reason="Exceeding amount",
            requested_by=data["admin_user"],
        )
