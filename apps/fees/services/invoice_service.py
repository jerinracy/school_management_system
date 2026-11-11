"""Invoice creation, bulk generation, deduplication, and lifecycle management."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import ClassLevel
from apps.fees.models import (
    FeeHead,
    FeeStructure,
    FineRule,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    InvoiceType,
    StudentFeeAssignment,
)
from apps.fees.services.invoice_number_service import get_next_invoice_number
from apps.fees.services.waiver_service import calculate_applicable_waiver
from apps.institutions.models import AcademicSession, Institution
from apps.students.models import EnrollmentStatus, Student, StudentEnrollment


def _check_duplicate_invoice(
    institution: Institution,
    student: Student,
    session: AcademicSession,
    invoice_type: str,
    billing_year: int,
    billing_month: int | None,
) -> None:
    """Ensure student does not already have an active invoice for the same month/year."""
    if billing_month and invoice_type == InvoiceType.MONTHLY:
        existing = (
            Invoice.objects.filter(
                institution=institution,
                student=student,
                session=session,
                invoice_type=InvoiceType.MONTHLY,
                billing_year=billing_year,
                billing_month=billing_month,
                is_deleted=False,
            )
            .exclude(status=InvoiceStatus.CANCELLED)
            .first()
        )
        if existing:
            raise ValidationError(
                f"An active invoice ({existing.invoice_number}) already exists for student {student.student_id} in {billing_month}/{billing_year}."
            )


def _resolve_billable_items(
    student: Student,
    fee_structure: FeeStructure | None,
    billing_month: int | None,
    custom_items: list[dict[str, Any]] | None,
) -> dict[FeeHead, Decimal]:
    """Compile dictionary of FeeHead -> base amount for student."""
    items_to_bill: dict[FeeHead, Decimal] = {}

    if fee_structure:
        for item in fee_structure.items.select_related("fee_head").filter(fee_head__is_active=True):
            if (
                item.applicable_months
                and billing_month
                and billing_month not in item.applicable_months
            ):
                continue
            items_to_bill[item.fee_head] = item.amount

    assignments = StudentFeeAssignment.objects.filter(
        student=student,
        is_deleted=False,
    ).select_related("fee_head")

    for asgn in assignments:
        if asgn.is_exempt:
            items_to_bill.pop(asgn.fee_head, None)
        elif asgn.custom_amount is not None:
            items_to_bill[asgn.fee_head] = asgn.custom_amount
        elif asgn.fee_head.is_optional and asgn.fee_head not in items_to_bill:
            items_to_bill[asgn.fee_head] = asgn.custom_amount or Decimal("0.00")

    if custom_items:
        for ci in custom_items:
            items_to_bill[ci["fee_head"]] = Decimal(str(ci["amount"]))

    return items_to_bill


def generate_single_student_invoice(
    student: Student,
    session: AcademicSession,
    invoice_type: str = InvoiceType.MONTHLY,
    billing_year: int = 2026,
    billing_month: int | None = None,
    fee_structure: FeeStructure | None = None,
    custom_items: list[dict[str, Any]] | None = None,
    issue_date: date | None = None,
    due_date: date | None = None,
    title: str = "",
    as_issued: bool = True,
    fine_rule: FineRule | None = None,
) -> Invoice:
    """Generate an invoice for an individual student with itemized lines, waivers, and sequence numbering."""
    institution = student.institution
    _check_duplicate_invoice(
        institution, student, session, invoice_type, billing_year, billing_month
    )

    enrollment = (
        StudentEnrollment.objects.filter(
            institution=institution,
            student=student,
            session=session,
            status=EnrollmentStatus.ACTIVE,
            is_deleted=False,
        )
        .select_related("class_level", "section")
        .first()
    )

    if not fee_structure and enrollment and enrollment.class_level:
        fee_structure = (
            FeeStructure.objects.filter(
                institution=institution,
                session=session,
                class_level=enrollment.class_level,
                is_active=True,
                is_deleted=False,
            )
            .prefetch_related("items__fee_head")
            .first()
        )

    items_to_bill = _resolve_billable_items(student, fee_structure, billing_month, custom_items)
    if not items_to_bill:
        raise ValidationError("No applicable fee items found to invoice for this student.")

    today = timezone.localdate()
    iss_date = issue_date or today
    d_date = due_date or date(billing_year, billing_month or today.month, 15)

    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    inv_title = title or (
        f"{month_names[billing_month]} {billing_year} Tuition & Fees"
        if billing_month
        else f"{session.name} School Fees"
    )

    with transaction.atomic():
        invoice_num = get_next_invoice_number(institution, billing_year)
        inv = Invoice.objects.create(
            institution=institution,
            invoice_number=invoice_num,
            student=student,
            enrollment=enrollment,
            session=session,
            invoice_type=invoice_type,
            title=inv_title,
            billing_month=billing_month,
            billing_year=billing_year,
            status=InvoiceStatus.ISSUED if as_issued else InvoiceStatus.DRAFT,
            issue_date=iss_date,
            due_date=d_date,
            fine_rule=fine_rule,
        )

        subtotal = Decimal("0.00")
        total_waiver = Decimal("0.00")
        lines = []

        for f_head, base_amt in items_to_bill.items():
            waiver_amt = calculate_applicable_waiver(
                student=student,
                fee_head=f_head,
                amount=base_amt,
                billing_date=iss_date,
            )
            payable_amt = max(Decimal("0.00"), base_amt - waiver_amt)
            subtotal += base_amt
            total_waiver += waiver_amt

            lines.append(
                InvoiceLine(
                    institution=institution,
                    invoice=inv,
                    fee_head=f_head,
                    description=f"{f_head.name_en} ({f_head.name_bn})",
                    amount=base_amt,
                    waiver_amount=waiver_amt,
                    payable_amount=payable_amt,
                )
            )

        InvoiceLine.objects.bulk_create(lines)
        inv.subtotal_amount = subtotal
        inv.waiver_amount = total_waiver
        inv.total_payable = max(Decimal("0.00"), subtotal - total_waiver)
        inv.due_amount = inv.total_payable
        inv.save(
            update_fields=[
                "subtotal_amount",
                "waiver_amount",
                "fine_amount",
                "total_payable",
                "paid_amount",
                "due_amount",
                "updated_at",
            ]
        )
        return inv


def preview_bulk_invoices(
    institution: Institution,
    session: AcademicSession,
    class_level: ClassLevel,
    section_id: UUID | str | None = None,
    billing_month: int | None = None,
    billing_year: int = 2026,
    invoice_type: str = InvoiceType.MONTHLY,
) -> dict[str, Any]:
    """Preview summary of bulk invoice generation for a class or section."""
    enrollments_qs = StudentEnrollment.objects.filter(
        institution=institution,
        session=session,
        class_level=class_level,
        status=EnrollmentStatus.ACTIVE,
        is_deleted=False,
    ).select_related("student", "section")

    if section_id:
        enrollments_qs = enrollments_qs.filter(section_id=section_id)

    total_students = enrollments_qs.count()

    # Check for existing invoices to deduplicate
    existing_invoiced_student_ids = set(
        Invoice.objects.filter(
            institution=institution,
            session=session,
            invoice_type=invoice_type,
            billing_year=billing_year,
            billing_month=billing_month,
            is_deleted=False,
        )
        .exclude(status=InvoiceStatus.CANCELLED)
        .values_list("student_id", flat=True)
    )

    new_candidate_count = 0
    skipped_count = 0

    for enr in enrollments_qs:
        if enr.student_id in existing_invoiced_student_ids:
            skipped_count += 1
        else:
            new_candidate_count += 1

    fee_structure = (
        FeeStructure.objects.filter(
            institution=institution,
            session=session,
            class_level=class_level,
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("items__fee_head")
        .first()
    )

    estimated_total = Decimal("0.00")
    if fee_structure:
        unit_subtotal = Decimal("0.00")
        for it in fee_structure.items.all():
            if it.applicable_months and billing_month and billing_month not in it.applicable_months:
                continue
            unit_subtotal += it.amount
        estimated_total = unit_subtotal * Decimal(new_candidate_count)

    return {
        "class_level_id": str(class_level.id),
        "class_level_name": class_level.name,
        "section_id": str(section_id) if section_id else None,
        "billing_month": billing_month,
        "billing_year": billing_year,
        "total_active_students": total_students,
        "already_invoiced_count": skipped_count,
        "new_invoices_to_create": new_candidate_count,
        "has_fee_structure": bool(fee_structure),
        "estimated_total_bdt": estimated_total,
    }


def generate_bulk_invoices(
    institution: Institution,
    session: AcademicSession,
    class_level: ClassLevel,
    section_id: UUID | str | None = None,
    billing_month: int | None = None,
    billing_year: int = 2026,
    invoice_type: str = InvoiceType.MONTHLY,
    issue_date: date | None = None,
    due_date: date | None = None,
    as_issued: bool = True,
    fine_rule: FineRule | None = None,
) -> dict[str, Any]:
    """Execute bulk invoice generation for an entire class level or section."""
    enrollments_qs = StudentEnrollment.objects.filter(
        institution=institution,
        session=session,
        class_level=class_level,
        status=EnrollmentStatus.ACTIVE,
        is_deleted=False,
    ).select_related("student", "section")

    if section_id:
        enrollments_qs = enrollments_qs.filter(section_id=section_id)

    fee_structure = (
        FeeStructure.objects.filter(
            institution=institution,
            session=session,
            class_level=class_level,
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("items__fee_head")
        .first()
    )
    if not fee_structure:
        raise ValidationError(
            f"No active fee structure found for {class_level.name} ({session.name})."
        )

    # Existing invoices to skip
    existing_invoiced_student_ids = set(
        Invoice.objects.filter(
            institution=institution,
            session=session,
            invoice_type=invoice_type,
            billing_year=billing_year,
            billing_month=billing_month,
            is_deleted=False,
        )
        .exclude(status=InvoiceStatus.CANCELLED)
        .values_list("student_id", flat=True)
    )

    created_invoices = []
    skipped_count = 0

    for enr in enrollments_qs:
        if enr.student_id in existing_invoiced_student_ids:
            skipped_count += 1
            continue

        try:
            inv = generate_single_student_invoice(
                student=enr.student,
                session=session,
                invoice_type=invoice_type,
                billing_year=billing_year,
                billing_month=billing_month,
                fee_structure=fee_structure,
                issue_date=issue_date,
                due_date=due_date,
                as_issued=as_issued,
                fine_rule=fine_rule,
            )
            created_invoices.append(inv)
        except Exception:
            # Skip students with generation errors (e.g. no billable items)
            continue

    total_billed = sum((inv.total_payable for inv in created_invoices), Decimal("0.00"))

    return {
        "class_level_id": str(class_level.id),
        "total_active_students": enrollments_qs.count(),
        "created_count": len(created_invoices),
        "skipped_duplicate_count": skipped_count,
        "total_billed_bdt": total_billed,
        "created_invoice_ids": [str(inv.id) for inv in created_invoices],
    }


def issue_invoice(invoice: Invoice) -> Invoice:
    """Transition draft invoice to issued status."""
    if invoice.status != InvoiceStatus.DRAFT:
        raise ValidationError(
            f"Only draft invoices can be issued. Current status: {invoice.status}"
        )
    invoice.status = InvoiceStatus.ISSUED
    invoice.save(update_fields=["status", "updated_at"])
    return invoice


def cancel_invoice(invoice: Invoice, reason: str = "") -> Invoice:
    """Cancel an invoice with mandatory audit reason."""
    if invoice.status == InvoiceStatus.PAID:
        raise ValidationError(
            "Fully paid invoices cannot be cancelled. Use refund workflow instead."
        )
    invoice.status = InvoiceStatus.CANCELLED
    invoice.cancellation_reason = reason
    invoice.save(update_fields=["status", "cancellation_reason", "updated_at"])
    return invoice
