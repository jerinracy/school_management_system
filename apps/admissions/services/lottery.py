"""Deterministic, auditable lottery draw service for admissions."""

import random
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.admissions.models import (
    AdmissionCircular,
    Application,
    ApplicationStatus,
    LotteryDraw,
)


def conduct_lottery_draw(
    *,
    circular_id: UUID | str,
    total_to_select: int,
    seed: int | None = None,
    conducted_by_user: Any = None,
    auto_advance_status: bool = False,
) -> LotteryDraw:
    """Executes a deterministic pseudo-random lottery draw over eligible candidates.

    Stores the seed and ordered draw sequence so the result can be independently reproduced and audited.
    """
    circular = AdmissionCircular.objects.get(id=circular_id)

    # Eligible candidates are those who submitted and paid
    eligible_applications = list(
        Application.objects.filter(
            circular=circular,
            status__in=[ApplicationStatus.PAID, ApplicationStatus.SHORTLISTED],
        ).order_by("created_at")
    )

    total_candidates = len(eligible_applications)
    if total_candidates == 0:
        raise ValidationError("No eligible candidates found (status must be PAID or SHORTLISTED).")

    if total_to_select <= 0:
        raise ValidationError("total_to_select must be a positive integer.")

    # Determine seed if not provided
    if seed is None:
        seed = random.randint(100_000_000, 999_999_999)

    # Deterministic shuffle
    rng = random.Random(seed)
    candidate_ids = [str(app.id) for app in eligible_applications]
    rng.shuffle(candidate_ids)

    selected_ids = candidate_ids[:total_to_select]

    with transaction.atomic():
        draw = LotteryDraw.objects.create(
            institution_id=circular.institution_id,
            circular=circular,
            seed=seed,
            total_candidates=total_candidates,
            selected_candidates_count=len(selected_ids),
            drawn_order=candidate_ids,
            conducted_by=conducted_by_user,
            is_confirmed=True,
        )

        if auto_advance_status:
            # Advance selected to SHORTLISTED or ADMITTED
            Application.objects.filter(id__in=selected_ids).update(
                status=ApplicationStatus.SHORTLISTED
            )

    return draw
