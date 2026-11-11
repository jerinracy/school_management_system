"""Service package for Staff & HR management."""

from .assignment_service import assign_teacher_to_subject, sync_academics_section_class_teacher
from .leave_service import (
    apply_for_leave,
    approve_leave,
    cancel_leave,
    initialize_leave_balances_for_session,
    recommend_leave,
    reject_leave,
    validate_no_leave_overlap,
)
from .staff_service import (
    create_portal_user_for_staff,
    create_staff,
    generate_employee_id,
)

__all__ = [
    "generate_employee_id",
    "create_staff",
    "create_portal_user_for_staff",
    "initialize_leave_balances_for_session",
    "validate_no_leave_overlap",
    "apply_for_leave",
    "recommend_leave",
    "approve_leave",
    "reject_leave",
    "cancel_leave",
    "assign_teacher_to_subject",
    "sync_academics_section_class_teacher",
]
