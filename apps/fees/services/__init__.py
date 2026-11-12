"""Fee management service interfaces."""

from apps.fees.services.fine_service import (
    apply_invoice_fine,
    calculate_invoice_late_fine,
    evaluate_overdue_invoices_batch,
)
from apps.fees.services.invoice_number_service import get_next_invoice_number
from apps.fees.services.invoice_pdf_service import (
    create_or_update_invoice_pdf,
    generate_invoice_pdf,
)
from apps.fees.services.invoice_service import (
    cancel_invoice,
    generate_bulk_invoices,
    generate_single_student_invoice,
    issue_invoice,
    preview_bulk_invoices,
)
from apps.fees.services.payment_service import (
    apply_advance_to_invoice,
    complete_online_payment,
    credit_student_advance,
    debit_student_advance,
    initiate_online_payment,
    record_counter_payment,
)
from apps.fees.services.receipt_service import (
    create_or_update_receipt_pdf,
    generate_money_receipt_pdf,
    get_next_receipt_number,
)
from apps.fees.services.refund_service import (
    approve_refund,
    process_refund,
    reject_refund,
    request_refund,
)
from apps.fees.services.waiver_service import (
    approve_student_waiver,
    calculate_applicable_waiver,
    reject_student_waiver,
)

__all__ = [
    "get_next_invoice_number",
    "calculate_applicable_waiver",
    "approve_student_waiver",
    "reject_student_waiver",
    "calculate_invoice_late_fine",
    "apply_invoice_fine",
    "evaluate_overdue_invoices_batch",
    "generate_single_student_invoice",
    "preview_bulk_invoices",
    "generate_bulk_invoices",
    "issue_invoice",
    "cancel_invoice",
    "generate_invoice_pdf",
    "create_or_update_invoice_pdf",
    "get_next_receipt_number",
    "generate_money_receipt_pdf",
    "create_or_update_receipt_pdf",
    "credit_student_advance",
    "debit_student_advance",
    "record_counter_payment",
    "apply_advance_to_invoice",
    "initiate_online_payment",
    "complete_online_payment",
    "request_refund",
    "approve_refund",
    "reject_refund",
    "process_refund",
]
