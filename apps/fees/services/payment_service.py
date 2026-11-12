"""Core payment collection, allocation, online gateway verification, and advance balances."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.fees.gateways.gateway_factory import get_gateway_adapter
from apps.fees.models import (
    AdvanceBalance,
    AdvanceTransaction,
    AdvanceTransactionType,
    Invoice,
    InvoiceStatus,
    MoneyReceipt,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    PaymentStatus,
)
from apps.fees.services.receipt_service import create_or_update_receipt_pdf, get_next_receipt_number
from apps.institutions.models import Institution
from apps.students.models import Student


def _allocate_payment_to_invoice(
    payment: Payment,
    invoice: Invoice,
    allocation_amount: Decimal,
) -> None:
    """Distribute allocation amount across invoice lines."""
    remaining = allocation_amount
    allocations = []

    lines = list(invoice.lines.filter(payable_amount__gt=Decimal("0.00")).order_by("id"))
    for line in lines:
        if remaining <= Decimal("0.00"):
            break
        unpaid = line.payable_amount - line.paid_amount
        if unpaid <= Decimal("0.00"):
            continue

        to_allocate = min(remaining, unpaid)
        line.paid_amount += to_allocate
        line.save(update_fields=["paid_amount"])

        allocations.append(
            PaymentAllocation(
                institution=payment.institution,
                payment=payment,
                invoice=invoice,
                invoice_line=line,
                allocated_amount=to_allocate,
            )
        )
        remaining -= to_allocate

    # If any remaining amount not mapped to specific lines, allocate to general invoice
    if remaining > Decimal("0.00"):
        allocations.append(
            PaymentAllocation(
                institution=payment.institution,
                payment=payment,
                invoice=invoice,
                invoice_line=None,
                allocated_amount=remaining,
            )
        )

    if allocations:
        PaymentAllocation.objects.bulk_create(allocations)


def credit_student_advance(
    student: Student,
    amount: Decimal,
    payment: Payment | None = None,
    invoice: Invoice | None = None,
    description: str = "Advance Balance Credit",
) -> AdvanceBalance:
    """Credit student's advance balance ledger."""
    with transaction.atomic():
        adv, _ = AdvanceBalance.objects.select_for_update().get_or_create(
            institution=student.institution,
            student=student,
            defaults={"current_balance": Decimal("0.00")},
        )
        adv.current_balance += amount
        adv.save(update_fields=["current_balance"])

        AdvanceTransaction.objects.create(
            institution=student.institution,
            advance_balance=adv,
            payment=payment,
            invoice=invoice,
            amount=amount,
            balance_after=adv.current_balance,
            transaction_type=AdvanceTransactionType.CREDIT_DEPOSIT,
            description=description,
        )
        return adv


def debit_student_advance(
    student: Student,
    amount: Decimal,
    invoice: Invoice | None = None,
    description: str = "Invoice Payment from Advance",
) -> AdvanceBalance:
    """Debit student's advance balance ledger."""
    with transaction.atomic():
        adv = AdvanceBalance.objects.select_for_update().get(
            institution=student.institution,
            student=student,
        )
        if adv.current_balance < amount:
            raise ValidationError(
                f"Insufficient advance balance (৳{adv.current_balance}) for requested debit (৳{amount})."
            )
        adv.current_balance -= amount
        adv.save(update_fields=["current_balance"])

        AdvanceTransaction.objects.create(
            institution=student.institution,
            advance_balance=adv,
            invoice=invoice,
            amount=-amount,
            balance_after=adv.current_balance,
            transaction_type=AdvanceTransactionType.DEBIT_INVOICE,
            description=description,
        )
        return adv


def _settle_invoice_counter_payment(
    invoice: Invoice,
    amount: Decimal,
    now: Any,
) -> tuple[Invoice, Decimal, Decimal]:
    """Lock invoice and record payment settlement, returning allocation and surplus amounts."""
    locked_inv = Invoice.objects.select_for_update().prefetch_related("lines").get(id=invoice.id)
    if locked_inv.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
        raise ValidationError(
            f"Invoice {locked_inv.invoice_number} cannot accept payments (Status: {locked_inv.status})."
        )

    # Check if overpaying invoice -> surplus goes to advance balance
    if amount > locked_inv.due_amount:
        allocated_to_invoice = locked_inv.due_amount
        surplus_amount = amount - locked_inv.due_amount
    else:
        allocated_to_invoice = amount
        surplus_amount = Decimal("0.00")

    locked_inv.paid_amount += allocated_to_invoice
    locked_inv.due_amount = max(Decimal("0.00"), locked_inv.total_payable - locked_inv.paid_amount)
    if locked_inv.due_amount == Decimal("0.00"):
        locked_inv.status = InvoiceStatus.PAID
        locked_inv.paid_date = now.date()
    else:
        locked_inv.status = InvoiceStatus.PARTIALLY_PAID
    locked_inv.save(
        update_fields=["paid_amount", "due_amount", "status", "paid_date", "updated_at"]
    )
    return locked_inv, allocated_to_invoice, surplus_amount


def _build_counter_payload(
    bank_name: str,
    cheque_no: str,
    cheque_date: date | None,
    pos_approval_code: str,
) -> dict[str, Any]:
    """Assemble dictionary of offline payment gateway tracking metadata."""
    payload: dict[str, Any] = {}
    if bank_name:
        payload["bank_name"] = bank_name
    if cheque_no:
        payload["cheque_no"] = cheque_no
    if cheque_date:
        payload["cheque_date"] = str(cheque_date)
    if pos_approval_code:
        payload["pos_approval_code"] = pos_approval_code
    return payload


def record_counter_payment(
    student: Student,
    amount: Decimal,
    invoice: Invoice | None = None,
    payment_method: str = PaymentMethod.CASH,
    received_by: User | None = None,
    collected_by: User | None = None,
    institution: Institution | None = None,
    idempotency_key: str | None = None,
    transaction_id: str = "",
    bank_name: str = "",
    cheque_no: str = "",
    cheque_date: date | None = None,
    pos_approval_code: str = "",
    notes: str = "",
) -> Payment:
    """Record in-person counter cash or bank deposit payment with atomic allocations."""
    if amount <= Decimal("0.00"):
        raise ValidationError("Payment amount must be greater than zero.")

    receiver = received_by or collected_by
    inst = institution or student.institution
    now = timezone.now()
    idem_key = idempotency_key or ""

    with transaction.atomic():
        if idem_key:
            existing = Payment.objects.filter(
                institution=inst,
                idempotency_key=idem_key,
                is_deleted=False,
            ).first()
            if existing:
                return existing

        surplus_amount = Decimal("0.00")
        allocated_to_invoice = amount

        if invoice:
            invoice, allocated_to_invoice, surplus_amount = _settle_invoice_counter_payment(
                invoice, amount, now
            )

        if not transaction_id:
            prefix = payment_method.upper()
            transaction_id = f"{prefix}_{now.strftime('%Y%m%d%H%M%S')}"

        gateway_payload = _build_counter_payload(
            bank_name, cheque_no, cheque_date, pos_approval_code
        )

        payment = Payment.objects.create(
            institution=inst,
            student=student,
            invoice=invoice,
            payment_method=payment_method,
            amount=amount,
            status=PaymentStatus.SUCCESSFUL,
            transaction_id=transaction_id,
            idempotency_key=idem_key or f"CTR-KEY-{student.id}-{now.timestamp()}",
            payment_date=now,
            received_by=receiver,
            gateway_payload=gateway_payload,
            notes=notes,
        )

        if invoice and allocated_to_invoice > Decimal("0.00"):
            _allocate_payment_to_invoice(payment, invoice, allocated_to_invoice)

        if surplus_amount > Decimal("0.00"):
            credit_student_advance(
                student=student,
                amount=surplus_amount,
                payment=payment,
                invoice=invoice,
                description=f"Surplus credit from Invoice {invoice.invoice_number if invoice else 'Deposit'}",
            )

        receipt_num = get_next_receipt_number(inst, now.year)
        receipt = MoneyReceipt.objects.create(
            institution=inst,
            receipt_number=receipt_num,
            payment=payment,
            student=student,
            total_amount=amount,
            issued_at=now,
            issued_by=receiver,
        )
        create_or_update_receipt_pdf(receipt)

        return payment


def apply_advance_to_invoice(
    student: Student,
    invoice: Invoice,
    amount: Decimal | None = None,
    applied_by: User | None = None,
) -> Payment:
    """Utilize existing student advance balance to settle invoice dues."""
    institution = student.institution
    now = timezone.now()

    with transaction.atomic():
        locked_inv = (
            Invoice.objects.select_for_update().prefetch_related("lines").get(id=invoice.id)
        )
        if locked_inv.due_amount <= Decimal("0.00"):
            raise ValidationError(f"Invoice {locked_inv.invoice_number} has zero outstanding dues.")

        to_apply = amount or locked_inv.due_amount
        to_apply = min(to_apply, locked_inv.due_amount)

        # Debit advance balance (validates sufficient funds)
        debit_student_advance(
            student=student,
            amount=to_apply,
            invoice=locked_inv,
            description=f"Settled Invoice {locked_inv.invoice_number}",
        )

        locked_inv.paid_amount += to_apply
        locked_inv.due_amount = max(
            Decimal("0.00"), locked_inv.total_payable - locked_inv.paid_amount
        )
        if locked_inv.due_amount == Decimal("0.00"):
            locked_inv.status = InvoiceStatus.PAID
            locked_inv.paid_date = now.date()
        else:
            locked_inv.status = InvoiceStatus.PARTIALLY_PAID
        locked_inv.save(
            update_fields=["paid_amount", "due_amount", "status", "paid_date", "updated_at"]
        )

        payment = Payment.objects.create(
            institution=institution,
            student=student,
            invoice=locked_inv,
            payment_method=PaymentMethod.ADVANCE,
            amount=to_apply,
            status=PaymentStatus.SUCCESSFUL,
            transaction_id=f"ADV-{now.strftime('%Y%m%d%H%M%S')}",
            idempotency_key=f"ADV-KEY-{locked_inv.id}-{now.timestamp()}",
            payment_date=now,
            received_by=applied_by,
            notes="Paid from advance balance credit.",
        )

        _allocate_payment_to_invoice(payment, locked_inv, to_apply)

        receipt_num = get_next_receipt_number(institution, now.year)
        receipt = MoneyReceipt.objects.create(
            institution=institution,
            receipt_number=receipt_num,
            payment=payment,
            student=student,
            total_amount=to_apply,
            issued_at=now,
            issued_by=applied_by,
        )
        create_or_update_receipt_pdf(receipt)

        return payment


def initiate_online_payment(
    invoice: Invoice,
    student: Student | None = None,
    payment_method: str = "sslcommerz",
    gateway_name: str | None = None,
    return_url: str = "",
    urls: dict[str, str] | None = None,
    payer_user: User | None = None,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Initiate an online payment session via configured gateway."""
    if invoice.due_amount <= Decimal("0.00"):
        raise ValidationError(f"Invoice {invoice.invoice_number} has zero outstanding balance.")

    stu = student or invoice.student
    gw_name = (gateway_name or payment_method or "sslcommerz").lower()
    institution = stu.institution
    adapter = get_gateway_adapter(gw_name)
    now = timezone.now()

    with transaction.atomic():
        payment = Payment.objects.create(
            institution=institution,
            student=stu,
            invoice=invoice,
            payment_method=gw_name,
            amount=invoice.due_amount,
            status=PaymentStatus.INITIATED,
            idempotency_key=idempotency_key or f"ONL-KEY-{invoice.id}-{now.timestamp()}",
            payment_date=now,
        )

        base_callback = return_url or "/api/v1/fees/payments/verify/"
        succ_url = (
            urls.get("success_url") if urls else None
        ) or f"{base_callback}?payment_id={payment.id}&status=success"
        fail_url = (
            urls.get("fail_url") if urls else None
        ) or f"{base_callback}?payment_id={payment.id}&status=fail"
        cancel_url = (
            urls.get("cancel_url") if urls else None
        ) or f"{base_callback}?payment_id={payment.id}&status=cancel"

        session_data = adapter.create_session(
            payment=payment,
            success_url=succ_url,
            fail_url=fail_url,
            cancel_url=cancel_url,
        )

        payment.gateway_order_id = session_data.get("session_id", "")
        payment.gateway_payload = session_data.get("raw_response", {})
        payment.status = PaymentStatus.PENDING
        payment.save(update_fields=["gateway_order_id", "gateway_payload", "status", "updated_at"])

        redir_url = session_data.get("redirect_url")
        return {
            "payment_id": str(payment.id),
            "gateway_url": redir_url,
            "redirect_url": redir_url,
            "session_id": session_data.get("session_id"),
            "amount": payment.amount,
            "currency": "BDT",
        }


def complete_online_payment(
    payment: Payment | UUID | str,
    verification_params: dict[str, Any],
) -> Payment:
    """Verify gateway response and finalize online payment atomically."""
    target_id = payment.id if isinstance(payment, Payment) else payment
    with transaction.atomic():
        payment_obj = Payment.objects.select_for_update().get(id=target_id)
        if payment_obj.status == PaymentStatus.SUCCESSFUL:
            return payment_obj

        adapter = get_gateway_adapter(payment_obj.payment_method)
        ver_result = adapter.verify(payment_obj, verification_params)

        if not ver_result.get("is_valid"):
            payment_obj.status = PaymentStatus.FAILED
            payment_obj.gateway_payload = ver_result.get("raw_data", {})
            payment_obj.save(update_fields=["status", "gateway_payload", "updated_at"])
            raise ValidationError(
                ver_result.get("error_message", "Online payment verification failed with gateway.")
            )

        now = timezone.now()
        payment_obj.status = PaymentStatus.SUCCESSFUL
        payment_obj.transaction_id = ver_result.get(
            "transaction_id", f"GW_TXN_{now.strftime('%Y%m%d%H%M%S')}"
        )
        payment_obj.gateway_payload = ver_result.get("raw_data", {})
        payment_obj.save(
            update_fields=["status", "transaction_id", "gateway_payload", "updated_at"]
        )

        invoice = payment_obj.invoice
        if invoice:
            locked_inv = (
                Invoice.objects.select_for_update().prefetch_related("lines").get(id=invoice.id)
            )
            alloc_amt = min(payment_obj.amount, locked_inv.due_amount)
            locked_inv.paid_amount += alloc_amt
            locked_inv.due_amount = max(
                Decimal("0.00"), locked_inv.total_payable - locked_inv.paid_amount
            )
            if locked_inv.due_amount == Decimal("0.00"):
                locked_inv.status = InvoiceStatus.PAID
                locked_inv.paid_date = now.date()
            else:
                locked_inv.status = InvoiceStatus.PARTIALLY_PAID
            locked_inv.save(
                update_fields=["paid_amount", "due_amount", "status", "paid_date", "updated_at"]
            )

            _allocate_payment_to_invoice(payment_obj, locked_inv, alloc_amt)

            # Overpayment surplus
            if payment_obj.amount > alloc_amt:
                credit_student_advance(
                    student=payment_obj.student,
                    amount=payment_obj.amount - alloc_amt,
                    payment=payment_obj,
                    invoice=locked_inv,
                    description=f"Online payment surplus credit from Invoice {locked_inv.invoice_number}",
                )

        receipt_num = get_next_receipt_number(payment_obj.institution, now.year)
        receipt = MoneyReceipt.objects.create(
            institution=payment_obj.institution,
            receipt_number=receipt_num,
            payment=payment_obj,
            student=payment_obj.student,
            total_amount=payment_obj.amount,
            issued_at=now,
        )
        create_or_update_receipt_pdf(receipt)

        return payment_obj
