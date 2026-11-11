"""Service layer for guardians, families, and authorized pickups."""

from .family_service import generate_family_code, link_siblings_to_family, suggest_siblings
from .guardian_service import (
    create_or_update_guardian,
    create_portal_user_for_guardian,
    link_student_guardian,
    merge_duplicate_guardians,
    unlink_student_guardian,
)
from .pickup_service import (
    generate_pickup_verification_otp,
    register_pickup_person,
    verify_pickup_otp,
)

__all__ = [
    "create_or_update_guardian",
    "create_portal_user_for_guardian",
    "link_student_guardian",
    "unlink_student_guardian",
    "merge_duplicate_guardians",
    "generate_family_code",
    "suggest_siblings",
    "link_siblings_to_family",
    "register_pickup_person",
    "generate_pickup_verification_otp",
    "verify_pickup_otp",
]
