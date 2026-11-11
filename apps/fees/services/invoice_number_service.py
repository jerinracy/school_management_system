"""Concurrency-safe sequential invoice number generator."""

from django.db import transaction

from apps.fees.models import InvoiceSequence
from apps.institutions.models import Institution


def get_next_invoice_number(institution: Institution, year: int) -> str:
    """Generate the next gap-free sequential invoice number for an institution and year.

    Format: INV-{year}-{seq:06d}, e.g. INV-2026-000001
    """
    with transaction.atomic():
        seq, _ = InvoiceSequence.objects.select_for_update().get_or_create(
            institution=institution,
            year=year,
            defaults={"last_number": 0},
        )
        seq.last_number += 1
        seq.save(update_fields=["last_number", "updated_at"])

        return f"INV-{year}-{seq.last_number:06d}"
