"""Academics business services."""

from apps.academics.services.conflicts import (
    ConflictReport,
    validate_routine_slot_conflicts,
    validate_routine_slots_batch,
)
from apps.academics.services.copy_session import copy_academic_structure_from_previous_session

__all__ = [
    "ConflictReport",
    "validate_routine_slot_conflicts",
    "validate_routine_slots_batch",
    "copy_academic_structure_from_previous_session",
]
