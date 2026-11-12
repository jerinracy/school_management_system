"""Services for recording payments and waiving LibraryFine entries."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.library.models import LibraryFine, LibraryFineStatus


@transaction.atomic
def record_fine_payment(
    *,
    fine: LibraryFine,
    amount: Decimal,
    payment_reference: str = "",
) -> LibraryFine:
    """Record a full or partial payment against an unpaid LibraryFine."""
    locked = LibraryFine.objects.select_for_update().get(id=fine.id)
    if locked.status in [LibraryFineStatus.PAID, LibraryFineStatus.WAIVED]:
        raise ValidationError(f"Fine is already {locked.status}.")
    if amount <= Decimal("0.00"):
        raise ValidationError("Payment amount must be greater than zero.")

    remaining = locked.amount - locked.paid_amount
    if amount > remaining:
        raise ValidationError(f"Payment ({amount}) exceeds remaining balance ({remaining}).")

    locked.paid_amount += amount
    if locked.paid_amount >= locked.amount:
        locked.status = LibraryFineStatus.PAID
        locked.paid_at = timezone.now()
    else:
        locked.status = LibraryFineStatus.PARTIALLY_PAID
    if payment_reference:
        locked.payment_reference = payment_reference
    locked.save(
        update_fields=["paid_amount", "status", "paid_at", "payment_reference", "updated_at"]
    )
    return locked


@transaction.atomic
def waive_fine(
    *,
    fine: LibraryFine,
    actor: Any = None,
    waive_reason: str = "",
) -> LibraryFine:
    """Waive an unpaid or partially paid LibraryFine."""
    locked = LibraryFine.objects.select_for_update().get(id=fine.id)
    if locked.status in [LibraryFineStatus.PAID, LibraryFineStatus.WAIVED]:
        raise ValidationError(f"Fine is already {locked.status}.")

    locked.status = LibraryFineStatus.WAIVED
    locked.waived_by = actor if actor and getattr(actor, "is_authenticated", False) else None
    locked.waive_reason = waive_reason
    locked.save(update_fields=["status", "waived_by", "waive_reason", "updated_at"])
    return locked
