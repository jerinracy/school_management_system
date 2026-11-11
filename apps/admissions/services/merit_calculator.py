"""Merit calculation and quota seat allocation service."""

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.admissions.models import (
    AdmissionCircular,
    AdmissionTestResult,
    Application,
    ApplicationStatus,
    LotteryDraw,
    MeritList,
    MeritListEntry,
    MeritType,
    QuotaRule,
    QuotaType,
)


def _score_by_test(circular: AdmissionCircular) -> list[tuple[Application, Decimal]]:
    """Scores applicants based on latest test results."""
    results = (
        AdmissionTestResult.objects.filter(
            test__circular=circular,
            is_passed=True,
            application__status__in=[
                ApplicationStatus.TEST_SCHEDULED,
                ApplicationStatus.SHORTLISTED,
                ApplicationStatus.PAID,
            ],
        )
        .select_related("application")
        .order_by("-marks_obtained", "-application__previous_gpa", "application__created_at")
    )
    return [(r.application, r.marks_obtained) for r in results]


def _score_by_lottery(circular: AdmissionCircular) -> list[tuple[Application, Decimal]]:
    """Orders applicants based on the latest confirmed lottery draw."""
    draw = (
        LotteryDraw.objects.filter(circular=circular, is_confirmed=True)
        .order_by("-draw_date")
        .first()
    )
    if not draw:
        raise ValidationError("No confirmed lottery draw found for this circular.")

    order_map = {app_id: idx for idx, app_id in enumerate(draw.drawn_order)}
    applications = list(
        Application.objects.filter(id__in=draw.drawn_order).select_related("quota_rule")
    )
    applications.sort(key=lambda a: order_map.get(str(a.id), 999999))
    return [(app, Decimal(str(len(applications) - idx))) for idx, app in enumerate(applications)]


def _score_by_gpa(circular: AdmissionCircular) -> list[tuple[Application, Decimal]]:
    """Orders applicants by previous GPA."""
    applications = Application.objects.filter(
        circular=circular,
        status__in=[ApplicationStatus.PAID, ApplicationStatus.SHORTLISTED],
        previous_gpa__isnull=False,
    ).order_by("-previous_gpa", "created_at")
    return [(a, a.previous_gpa or Decimal("0.00")) for a in applications]


def _get_scored_candidates(
    circular: AdmissionCircular,
    selection_criteria: str,
) -> list[tuple[Application, Decimal]]:
    if selection_criteria == "test_score":
        return _score_by_test(circular)
    if selection_criteria == "lottery":
        return _score_by_lottery(circular)
    if selection_criteria == "gpa":
        return _score_by_gpa(circular)
    raise ValidationError(f"Invalid selection criteria: {selection_criteria}")


def _build_quota_caps(circular: AdmissionCircular, total_seats: int) -> dict[str, int]:
    quota_rules = list(QuotaRule.objects.filter(circular=circular).order_by("priority"))
    quota_caps: dict[str, int] = {}
    for q in quota_rules:
        if q.reserved_seats > 0:
            quota_caps[q.quota_type] = q.reserved_seats
        elif q.reserved_percentage > Decimal("0.00"):
            quota_caps[q.quota_type] = int((q.reserved_percentage / Decimal("100")) * total_seats)
        else:
            quota_caps[q.quota_type] = 0
    return quota_caps


def _partition_candidates(
    scored_candidates: list[tuple[Application, Decimal]],
    quota_caps: dict[str, int],
    total_seats: int,
) -> tuple[list[tuple[Application, Decimal, str]], list[tuple[Application, Decimal, str]]]:
    selected_candidates: list[tuple[Application, Decimal, str]] = []
    waiting_candidates: list[tuple[Application, Decimal, str]] = []
    quota_filled: dict[str, int] = {k: 0 for k in quota_caps}

    # Pass 1: Quota
    remaining_pool: list[tuple[Application, Decimal]] = []
    for app, score in scored_candidates:
        q_type = app.quota_type
        if (
            q_type != QuotaType.GENERAL
            and q_type in quota_caps
            and quota_filled[q_type] < quota_caps[q_type]
        ):
            selected_candidates.append((app, score, MeritType.QUOTA))
            quota_filled[q_type] += 1
        else:
            remaining_pool.append((app, score))

    # Pass 2: General Merit
    for app, score in remaining_pool:
        if len(selected_candidates) < total_seats:
            selected_candidates.append((app, score, MeritType.MERIT))
        else:
            waiting_candidates.append((app, score, MeritType.WAITING))

    return selected_candidates, waiting_candidates


def _create_merit_entries(
    merit_list: MeritList,
    institution_id: UUID | str,
    selected: list[tuple[Application, Decimal, str]],
    waiting: list[tuple[Application, Decimal, str]],
) -> None:
    rank = 1
    for app, score, m_type in selected:
        MeritListEntry.objects.create(
            institution_id=institution_id,
            merit_list=merit_list,
            application=app,
            rank=rank,
            merit_type=m_type,
            score=score,
            is_selected=True,
        )
        rank += 1

    w_rank = 1
    for app, score, m_type in waiting:
        MeritListEntry.objects.create(
            institution_id=institution_id,
            merit_list=merit_list,
            application=app,
            rank=w_rank,
            merit_type=m_type,
            score=score,
            is_selected=False,
        )
        w_rank += 1


def generate_merit_list(
    *,
    circular_id: UUID | str,
    selection_criteria: str = "test_score",
    title: str = "1st Merit List",
    auto_publish: bool = False,
) -> MeritList:
    """Calculates rankings with quota seat allocation and generates a MeritList with entries."""
    circular = AdmissionCircular.objects.get(id=circular_id)
    total_seats = circular.seats_available

    scored_candidates = _get_scored_candidates(circular, selection_criteria)
    if not scored_candidates:
        raise ValidationError("No eligible scored applicants available to build a merit list.")

    quota_caps = _build_quota_caps(circular, total_seats)
    selected, waiting = _partition_candidates(scored_candidates, quota_caps, total_seats)

    with transaction.atomic():
        merit_list = MeritList.objects.create(
            institution_id=circular.institution_id,
            circular=circular,
            title=title,
            selection_criteria=selection_criteria,
            is_published=auto_publish,
        )
        _create_merit_entries(merit_list, circular.institution_id, selected, waiting)

    return merit_list
