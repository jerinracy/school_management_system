"""Unit tests for Fee models and database constraints."""

from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.academics.models import ClassLevel
from apps.fees.models import (
    DiscountType,
    FeeHead,
    FeeStructure,
    FeeStructureItem,
    FeeType,
    FineRule,
    FineType,
    Invoice,
    InvoiceLine,
    InvoiceType,
    RecurrenceType,
    StudentWaiver,
    WaiverApprovalStatus,
    WaiverCategory,
    WaiverRule,
)
from apps.institutions.models import AcademicSession, Branch, Institution
from apps.students.models import Student


@pytest.fixture
def base_fee_data(db: None) -> dict:
    inst = Institution.objects.create(name_en="Fee Model High School", name_bn="ফি মডেল হাই স্কুল")
    branch = Branch.objects.create(institution=inst, name="Main Campus")
    session = AcademicSession.objects.create(
        institution=inst,
        name="2026 Academic Session",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    class_level = ClassLevel.objects.create(institution=inst, name="Class 8", code="C8", order=8)
    student = Student.objects.create(
        institution=inst,
        student_id="STU-FEE-01",
        name_en="Sakib Khan",
        name_bn="সাকিব খান",
        admission_date="2026-01-01",
        dob="2011-05-10",
    )
    return {
        "inst": inst,
        "branch": branch,
        "session": session,
        "class_level": class_level,
        "student": student,
    }


@pytest.mark.django_db
def test_fee_head_creation_and_uniqueness(base_fee_data: dict) -> None:
    inst = base_fee_data["inst"]
    head = FeeHead.objects.create(
        institution=inst,
        code="TUITION_MONTHLY",
        name_en="Monthly Tuition Fee",
        name_bn="মাসিক বেতন",
        fee_type=FeeType.TUITION,
        recurrence=RecurrenceType.MONTHLY,
    )
    assert str(head) == "Monthly Tuition Fee (মাসিক বেতন) [TUITION_MONTHLY]"

    # Duplicate code for same institution must violate unique constraint
    with pytest.raises(IntegrityError):
        FeeHead.objects.create(
            institution=inst,
            code="TUITION_MONTHLY",
            name_en="Duplicate Fee",
            name_bn="ডুপ্লিকেট ফি",
        )


@pytest.mark.django_db
def test_fee_structure_and_items(base_fee_data: dict) -> None:
    inst = base_fee_data["inst"]
    session = base_fee_data["session"]
    cls = base_fee_data["class_level"]

    head1 = FeeHead.objects.create(
        institution=inst, code="TUITION", name_en="Tuition", name_bn="বেতন"
    )
    FeeHead.objects.create(
        institution=inst, code="LAB", name_en="Computer Lab", name_bn="কম্পিউটার ল্যাব"
    )

    structure = FeeStructure.objects.create(
        institution=inst,
        session=session,
        class_level=cls,
        name="Class 8 Standard 2026",
    )
    assert "Class 8 Standard 2026" in str(structure)

    item1 = FeeStructureItem.objects.create(
        institution=inst,
        fee_structure=structure,
        fee_head=head1,
        amount=Decimal("1500.00"),
        due_day=10,
    )
    assert item1.amount == Decimal("1500.00")

    # Duplicate head on same structure should raise IntegrityError
    with pytest.raises(IntegrityError):
        FeeStructureItem.objects.create(
            institution=inst,
            fee_structure=structure,
            fee_head=head1,
            amount=Decimal("1200.00"),
        )


@pytest.mark.django_db
def test_waiver_and_fine_rules(base_fee_data: dict) -> None:
    inst = base_fee_data["inst"]
    student = base_fee_data["student"]

    w_rule = WaiverRule.objects.create(
        institution=inst,
        name="Sibling Discount",
        category=WaiverCategory.SIBLING,
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("50.00"),
    )
    assert "50.00%" in str(w_rule)

    sw = StudentWaiver.objects.create(
        institution=inst,
        student=student,
        waiver_rule=w_rule,
        title="Sibling Discount 50%",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("50.00"),
    )
    assert sw.status == WaiverApprovalStatus.PENDING

    f_rule = FineRule.objects.create(
        institution=inst,
        name="Class 8 Late Fine",
        fine_type=FineType.FIXED,
        grace_period_days=5,
        amount=Decimal("100.00"),
    )
    assert "Grace: 5d" in str(f_rule)


@pytest.mark.django_db
def test_invoice_creation_and_clean(base_fee_data: dict) -> None:
    inst = base_fee_data["inst"]
    session = base_fee_data["session"]
    student = base_fee_data["student"]

    head = FeeHead.objects.create(
        institution=inst, code="TUITION_C8", name_en="Tuition", name_bn="বেতন"
    )

    inv = Invoice.objects.create(
        institution=inst,
        invoice_number="INV-2026-000001",
        student=student,
        session=session,
        invoice_type=InvoiceType.MONTHLY,
        billing_month=3,
        billing_year=2026,
        subtotal_amount=Decimal("1500.00"),
        waiver_amount=Decimal("500.00"),
        fine_amount=Decimal("50.00"),
        total_payable=Decimal("1050.00"),
        paid_amount=Decimal("0.00"),
        due_amount=Decimal("1050.00"),
        issue_date="2026-03-01",
        due_date="2026-03-15",
    )
    assert inv.due_amount == Decimal("1050.00")

    line = InvoiceLine.objects.create(
        institution=inst,
        invoice=inv,
        fee_head=head,
        description="Monthly Tuition",
        amount=Decimal("1500.00"),
        waiver_amount=Decimal("500.00"),
        payable_amount=Decimal("1000.00"),
    )
    assert line.payable_amount == Decimal("1000.00")
