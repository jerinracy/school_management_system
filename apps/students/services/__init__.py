"""Student services package."""

from apps.students.services.bulk_import import import_students_from_excel
from apps.students.services.id_card_service import issue_or_renew_id_card
from apps.students.services.intake import admit_from_application
from apps.students.services.promotion import apply_promotion, preview_promotion, rollback_promotion
from apps.students.services.roll_assigner import auto_assign_section_rolls
from apps.students.services.transfer import issue_testimonial, issue_transfer_certificate

__all__ = [
    "admit_from_application",
    "auto_assign_section_rolls",
    "preview_promotion",
    "apply_promotion",
    "rollback_promotion",
    "issue_transfer_certificate",
    "issue_testimonial",
    "issue_or_renew_id_card",
    "import_students_from_excel",
]
