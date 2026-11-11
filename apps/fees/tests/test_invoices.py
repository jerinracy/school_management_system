"""Unit and integration tests for Invoice generation, sequencing, and PDF generation."""

from datetime import time
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassLevel, Section
from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    InvoiceStatus,
    InvoiceType,
    RecurrenceType,
    StudentFeeAssignment,
)
from apps.fees.services import (
    cancel_invoice,
    create_or_update_invoice_pdf,
    generate_bulk_invoices,
    generate_invoice_pdf,
    generate_single_student_invoice,
    get_next_invoice_number,
    issue_invoice,
    preview_bulk_invoices,
)
from apps.institutions.models import AcademicSession, Branch, Institution, Shift
from apps.students.models import Student, StudentEnrollment


@pytest.fixture
def invoice_test_setup(db: None) -> dict:
    inst = Institution.objects.create(name_en="Invoice Test Academy", name_bn="ইনভয়েস টেস্ট একাডেমি")
    branch = Branch.objects.create(institution=inst, name="Main")
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
    class_level = ClassLevel.objects.create(institution=inst, name="Class 7", code="C7", order=7)
    section = Section.objects.create(
        institution=inst,
        class_level=class_level,
        session=session,
        shift=shift,
        name="Section A",
    )

    # Fee Heads
    fh_tuition = FeeHead.objects.create(
        institution=inst,
        code="TUITION",
        name_en="Monthly Tuition",
        name_bn="মাসিক বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    fh_lab = FeeHead.objects.create(
        institution=inst,
        code="LAB",
        name_en="Science Lab",
        name_bn="বিজ্ঞান ল্যাব",
        fee_type=FeeType.LAB,
        recurrence=RecurrenceType.MONTHLY,
    )
    fh_transport = FeeHead.objects.create(
        institution=inst,
        code="TRANS",
        name_en="Bus Transport",
        name_bn="বাস ভাড়া",
        fee_type=FeeType.TRANSPORT,
        recurrence=RecurrenceType.MONTHLY,
        is_optional=True,
    )

    # Fee Structure
    structure = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=class_level,
        name="Class 7 Regular 2026",
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=structure,
        fee_head=fh_tuition,
        amount=Decimal("1200.00"),
        due_day=10,
    )
    FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=structure,
        fee_head=fh_lab,
        amount=Decimal("300.00"),
        due_day=10,
    )

    # 3 Students
    students = []
    for i in range(1, 4):
        s = Student.objects.create(
            institution=inst,
            student_id=f"STU-2026-0{i}",
            name_en=f"Student {i}",
            name_bn=f"শিক্ষার্থী {i}",
            admission_date="2026-01-01",
            dob="2012-01-01",
        )
        StudentEnrollment.objects.create(
            institution=inst,
            student=s,
            session=session,
            class_level=class_level,
            section=section,
            roll_no=i,
            enrollment_date="2026-01-01",
        )
        students.append(s)

    return {
        "inst": inst,
        "branch": branch,
        "session": session,
        "class_level": class_level,
        "section": section,
        "structure": structure,
        "fh_tuition": fh_tuition,
        "fh_lab": fh_lab,
        "fh_transport": fh_transport,
        "students": students,
    }


@pytest.mark.django_db
def test_invoice_sequencer(invoice_test_setup: dict) -> None:
    inst = invoice_test_setup["inst"]
    num1 = get_next_invoice_number(inst, 2026)
    num2 = get_next_invoice_number(inst, 2026)
    num3 = get_next_invoice_number(inst, 2026)

    assert num1 == "INV-2026-000001"
    assert num2 == "INV-2026-000002"
    assert num3 == "INV-2026-000003"


@pytest.mark.django_db
def test_single_invoice_generation_and_deduplication(invoice_test_setup: dict) -> None:
    data = invoice_test_setup
    student = data["students"][0]
    session = data["session"]

    inv = generate_single_student_invoice(
        student=student,
        session=session,
        invoice_type=InvoiceType.MONTHLY,
        billing_month=3,
        billing_year=2026,
    )

    assert inv.invoice_number.startswith("INV-2026-")
    assert inv.subtotal_amount == Decimal("1500.00")  # 1200 + 300
    assert inv.total_payable == Decimal("1500.00")
    assert inv.due_amount == Decimal("1500.00")
    assert inv.status == InvoiceStatus.ISSUED
    assert inv.lines.count() == 2

    # Generating duplicate for same month should fail with ValidationError
    with pytest.raises(ValidationError):
        generate_single_student_invoice(
            student=student,
            session=session,
            invoice_type=InvoiceType.MONTHLY,
            billing_month=3,
            billing_year=2026,
        )


@pytest.mark.django_db
def test_student_fee_assignment_override_and_opt_in(invoice_test_setup: dict) -> None:
    data = invoice_test_setup
    student = data["students"][1]
    session = data["session"]
    fh_lab = data["fh_lab"]
    fh_transport = data["fh_transport"]

    # Exempt student from lab fee
    StudentFeeAssignment.objects.create(
        institution=data["inst"],
        student=student,
        fee_head=fh_lab,
        is_exempt=True,
    )
    # Opt in to transport fee at 800 BDT
    StudentFeeAssignment.objects.create(
        institution=data["inst"],
        student=student,
        fee_head=fh_transport,
        custom_amount=Decimal("800.00"),
    )

    inv = generate_single_student_invoice(
        student=student,
        session=session,
        billing_month=4,
        billing_year=2026,
    )

    # Expected: Tuition 1200 + Transport 800 (Lab 300 is exempt) = 2000
    assert inv.subtotal_amount == Decimal("2000.00")
    assert inv.total_payable == Decimal("2000.00")
    assert inv.lines.count() == 2


@pytest.mark.django_db
def test_bulk_invoice_preview_and_generation(invoice_test_setup: dict) -> None:
    data = invoice_test_setup
    inst = data["inst"]
    session = data["session"]
    cls = data["class_level"]

    # 1. Preview
    preview = preview_bulk_invoices(
        institution=inst,
        session=session,
        class_level=cls,
        billing_month=5,
        billing_year=2026,
    )
    assert preview["total_active_students"] == 3
    assert preview["already_invoiced_count"] == 0
    assert preview["new_invoices_to_create"] == 3
    assert preview["estimated_total_bdt"] == Decimal("4500.00")  # 3 * 1500

    # 2. Execute Bulk Generate
    gen_result = generate_bulk_invoices(
        institution=inst,
        session=session,
        class_level=cls,
        billing_month=5,
        billing_year=2026,
    )
    assert gen_result["created_count"] == 3
    assert gen_result["skipped_duplicate_count"] == 0
    assert gen_result["total_billed_bdt"] == Decimal("4500.00")

    # 3. Second run for same month skips duplicates
    gen_result2 = generate_bulk_invoices(
        institution=inst,
        session=session,
        class_level=cls,
        billing_month=5,
        billing_year=2026,
    )
    assert gen_result2["created_count"] == 0
    assert gen_result2["skipped_duplicate_count"] == 3


@pytest.mark.django_db
def test_invoice_lifecycle_and_pdf(invoice_test_setup: dict) -> None:
    data = invoice_test_setup
    student = data["students"][2]
    session = data["session"]

    # Generate draft
    inv = generate_single_student_invoice(
        student=student,
        session=session,
        billing_month=6,
        billing_year=2026,
        as_issued=False,
    )
    assert inv.status == InvoiceStatus.DRAFT

    # Issue
    issued_inv = issue_invoice(inv)
    assert issued_inv.status == InvoiceStatus.ISSUED

    # PDF generation
    pdf_bytes = generate_invoice_pdf(issued_inv)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # Save to model
    updated_inv = create_or_update_invoice_pdf(issued_inv)
    assert bool(updated_inv.pdf_receipt)

    # Cancel
    cancelled_inv = cancel_invoice(updated_inv, reason="Incorrect class assigned")
    assert cancelled_inv.status == InvoiceStatus.CANCELLED
    assert cancelled_inv.cancellation_reason == "Incorrect class assigned"
