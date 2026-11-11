"""Business logic service layer for institutions."""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AcademicSession, SessionStatus


def _validate_attendance_defaults(attendance: Any) -> None:
    if not isinstance(attendance, dict):
        raise ValidationError("attendance_defaults must be a dictionary.")
    late_tol = attendance.get("late_tolerance_minutes", 15)
    if not isinstance(late_tol, int) or late_tol < 0 or late_tol > 120:
        raise ValidationError("late_tolerance_minutes must be an integer between 0 and 120.")
    half_day = attendance.get("half_day_minimum_minutes", 180)
    if not isinstance(half_day, int) or half_day < 0 or half_day > 600:
        raise ValidationError("half_day_minimum_minutes must be an integer between 0 and 600.")


def _validate_sms_and_prefix(data: dict[str, Any]) -> None:
    sender_id = data.get("sms_sender_id")
    if sender_id and (not isinstance(sender_id, str) or len(sender_id) > 11):
        raise ValidationError(
            "sms_sender_id must be an alphanumeric string of at most 11 characters."
        )

    prefix = data.get("fee_receipt_prefix")
    if prefix is not None and (not isinstance(prefix, str) or len(prefix) > 20):
        raise ValidationError("fee_receipt_prefix must be a string of at most 20 characters.")


def validate_institution_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Validate institution settings JSON structure against business rules."""
    if not isinstance(data, dict):
        raise ValidationError("Settings must be a valid JSON dictionary.")

    validated = dict(data)
    if "attendance_defaults" in validated:
        _validate_attendance_defaults(validated["attendance_defaults"])

    _validate_sms_and_prefix(validated)

    if "bangla_digits" in validated and not isinstance(validated["bangla_digits"], bool):
        raise ValidationError("bangla_digits must be a boolean.")

    return validated


def activate_academic_session(
    *,
    session_id: UUID | str,
    institution_id: UUID | str,
    actor: Any = None,
) -> AcademicSession:
    """Atomically activate an academic session and set it as the only current session."""
    with transaction.atomic():
        try:
            target_session = (
                AcademicSession.objects.select_for_update()
                .filter(id=session_id, institution_id=institution_id)
                .first()
            )
        except (ValueError, TypeError) as exc:
            raise ValidationError(f"Invalid session ID: {exc}") from exc

        if not target_session:
            raise ValidationError("Academic session not found for this institution.")

        if target_session.status == SessionStatus.CLOSED:
            raise ValidationError("Cannot activate a closed academic session.")

        if target_session.is_current and target_session.status == SessionStatus.ACTIVE:
            return target_session

        # Atomically remove is_current from any active sessions in this institution
        AcademicSession.objects.filter(
            institution_id=institution_id,
            is_current=True,
        ).exclude(
            id=target_session.id
        ).update(is_current=False)

        target_session.is_current = True
        target_session.status = SessionStatus.ACTIVE
        target_session.save(update_fields=["is_current", "status", "updated_at"])

        return target_session


def close_academic_session(
    *,
    session_id: UUID | str,
    institution_id: UUID | str,
    confirm: bool = False,
    actor: Any = None,
) -> AcademicSession:
    """Safely and irreversibly close an academic session.

    Pre-checks:
    1. confirm must be True (irreversible operation).
    2. Session must belong to institution.
    3. Session cannot already be closed.
    """
    if not confirm:
        raise ValidationError(
            "Closing an academic session is irreversible. Pass confirm=True to confirm."
        )

    with transaction.atomic():
        target_session = (
            AcademicSession.objects.select_for_update()
            .filter(id=session_id, institution_id=institution_id)
            .first()
        )

        if not target_session:
            raise ValidationError("Academic session not found for this institution.")

        if target_session.status == SessionStatus.CLOSED:
            raise ValidationError("Academic session is already closed.")

        target_session.is_current = False
        target_session.status = SessionStatus.CLOSED
        target_session.save(update_fields=["is_current", "status", "updated_at"])

        return target_session
