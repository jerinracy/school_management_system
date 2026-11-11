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
]
