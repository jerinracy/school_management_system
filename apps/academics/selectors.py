"""Selectors for academic queries and routine timetable grids."""

from typing import Any
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.academics.models import Period, RoutineSlot, Weekday


def get_routine_slots_queryset(institution_id: UUID | str) -> QuerySet[RoutineSlot]:
    """Base pre-fetched queryset for routine slots."""
    return (
        RoutineSlot.objects.filter(institution_id=institution_id)
        .select_related(
            "section",
            "section__class_level",
            "period",
            "period__shift",
            "subject",
            "teacher_user",
            "teacher_staff",
            "room",
            "room__branch",
        )
        .order_by("weekday", "period__order")
    )


def get_routine_for_section(
    *,
    institution_id: UUID | str,
    section_id: UUID | str,
    weekday: int | None = None,
) -> QuerySet[RoutineSlot]:
    qs = get_routine_slots_queryset(institution_id).filter(section__id=section_id)
    if weekday is not None:
        qs = qs.filter(weekday=weekday)
    return qs


def get_routine_for_teacher(
    *,
    institution_id: UUID | str,
    teacher_user_id: UUID | str,
    weekday: int | None = None,
) -> QuerySet[RoutineSlot]:
    qs = get_routine_slots_queryset(institution_id).filter(
        Q(teacher_user__id=teacher_user_id)
        | Q(teacher_staff__id=teacher_user_id)
        | Q(teacher_staff__user__id=teacher_user_id)
    )
    if weekday is not None:
        qs = qs.filter(weekday=weekday)
    return qs


def get_routine_for_room(
    *,
    institution_id: UUID | str,
    room_id: UUID | str,
    weekday: int | None = None,
) -> QuerySet[RoutineSlot]:
    qs = get_routine_slots_queryset(institution_id).filter(room__id=room_id)
    if weekday is not None:
        qs = qs.filter(weekday=weekday)
    return qs


def build_section_timetable_matrix(
    *,
    institution_id: UUID | str,
    section_id: UUID | str,
) -> dict[str, Any]:
    """Builds a full 2D grid (weekday x period) suitable for frontend timetable rendering."""
    slots = get_routine_for_section(institution_id=institution_id, section_id=section_id)

    # Fetch all periods for this section's shift
    shift_periods: list[Period] = []
    if slots.exists():
        shift_id = slots.first().section.shift_id  # type: ignore[union-attr]
        shift_periods = list(
            Period.objects.filter(shift_id=shift_id, institution_id=institution_id).order_by(
                "order"
            )
        )

    # Map slot by (weekday, period_id)
    slot_map: dict[tuple[int, str], RoutineSlot] = {
        (slot.weekday, str(slot.period_id)): slot for slot in slots
    }

    grid: list[dict[str, Any]] = []
    for day_code, day_name in Weekday.choices:
        day_slots: list[dict[str, Any]] = []
        for period in shift_periods:
            matched_slot = slot_map.get((day_code, str(period.id)))
            day_slots.append(
                {
                    "period_id": str(period.id),
                    "period_name": period.name,
                    "start_time": period.start_time.strftime("%H:%M"),
                    "end_time": period.end_time.strftime("%H:%M"),
                    "is_break": period.is_break,
                    "slot": (
                        {
                            "id": str(matched_slot.id),
                            "subject": {
                                "id": str(matched_slot.subject_id),
                                "code": matched_slot.subject.code,
                                "name_en": matched_slot.subject.name_en,
                                "name_bn": matched_slot.subject.name_bn,
                            },
                            "teacher": (
                                {
                                    "id": str(matched_slot.teacher_user_id),
                                    "full_name": matched_slot.teacher_user.full_name,
                                }
                                if matched_slot.teacher_user
                                else None
                            ),
                            "room": (
                                {
                                    "id": str(matched_slot.room_id),
                                    "name": matched_slot.room.name,
                                }
                                if matched_slot.room
                                else None
                            ),
                        }
                        if matched_slot
                        else None
                    ),
                }
            )
        grid.append(
            {
                "weekday": day_code,
                "weekday_name": day_name,
                "periods": day_slots,
            }
        )

    return {
        "section_id": str(section_id),
        "periods": [
            {
                "id": str(p.id),
                "name": p.name,
                "start_time": p.start_time.strftime("%H:%M"),
                "end_time": p.end_time.strftime("%H:%M"),
                "is_break": p.is_break,
                "order": p.order,
            }
            for p in shift_periods
        ],
        "grid": grid,
    }
