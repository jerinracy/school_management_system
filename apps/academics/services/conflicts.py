"""Timetable conflict detection and validation service."""

import dataclasses
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from apps.academics.models import Period, RoutineSlot, Weekday
from apps.institutions.models import Institution

WEEKDAY_NAME_MAP: dict[int, str] = {
    int(Weekday.SATURDAY): "saturday",
    int(Weekday.SUNDAY): "sunday",
    int(Weekday.MONDAY): "monday",
    int(Weekday.TUESDAY): "tuesday",
    int(Weekday.WEDNESDAY): "wednesday",
    int(Weekday.THURSDAY): "thursday",
    int(Weekday.FRIDAY): "friday",
}


@dataclasses.dataclass
class SlotConflict:
    code: str
    message: str
    field: str
    conflicting_slot_id: str | None = None
    details: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ConflictReport:
    is_valid: bool
    conflicts: list[SlotConflict] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "conflicts": [
                {
                    "code": c.code,
                    "message": c.message,
                    "field": c.field,
                    "conflicting_slot_id": c.conflicting_slot_id,
                    "details": c.details,
                }
                for c in self.conflicts
            ],
            "warnings": self.warnings,
        }


def _check_period_break(
    institution_id: UUID | str,
    period_id: UUID | str,
    conflicts: list[SlotConflict],
) -> bool:
    """Validate period existence and whether it is a break."""
    try:
        period = Period.objects.get(id=period_id, institution_id=institution_id)
        if period.is_break:
            conflicts.append(
                SlotConflict(
                    code="PERIOD_IS_BREAK",
                    message=f"Period '{period.name}' is marked as a break period.",
                    field="period",
                )
            )
        return True
    except Period.DoesNotExist:
        conflicts.append(
            SlotConflict(
                code="INVALID_PERIOD",
                message="Specified period does not exist for this institution.",
                field="period",
            )
        )
        return False


def _check_weekend_calendar(
    institution_id: UUID | str,
    weekday: int,
    warnings: list[str],
) -> None:
    """Adds a warning if the weekday falls on an institutional weekend."""
    try:
        institution = Institution.objects.get(id=institution_id)
        weekday_name = WEEKDAY_NAME_MAP.get(weekday, "").lower()
        institution_weekends = [d.lower() for d in (institution.weekend_days or [])]
        if weekday_name in institution_weekends:
            warnings.append(
                f"{weekday_name.capitalize()} is configured as an institutional weekend day."
            )
    except Institution.DoesNotExist:
        pass


def _check_section_clash(
    base_qs: QuerySet[RoutineSlot],
    section_id: UUID | str,
    conflicts: list[SlotConflict],
) -> None:
    clashing_section_slot = base_qs.filter(section__id=section_id).first()
    if clashing_section_slot:
        conflicts.append(
            SlotConflict(
                code="SECTION_CLASH",
                message=(
                    f"Section '{clashing_section_slot.section.name}' already has "
                    f"'{clashing_section_slot.subject.name_en}' scheduled in this period."
                ),
                field="section",
                conflicting_slot_id=str(clashing_section_slot.id),
                details={"subject_id": str(clashing_section_slot.subject_id)},
            )
        )


def _check_teacher_clash(
    base_qs: QuerySet[RoutineSlot],
    teacher_user_id: UUID | str | None,
    conflicts: list[SlotConflict],
) -> None:
    if not teacher_user_id:
        return
    clashing_teacher_slot = base_qs.filter(teacher_user__id=teacher_user_id).first()
    if clashing_teacher_slot:
        teacher_name = (
            clashing_teacher_slot.teacher_user.full_name
            if clashing_teacher_slot.teacher_user
            else "Selected teacher"
        )
        conflicts.append(
            SlotConflict(
                code="TEACHER_DOUBLE_BOOKED",
                message=(
                    f"Teacher '{teacher_name}' is already assigned to "
                    f"section '{clashing_teacher_slot.section.name}' ({clashing_teacher_slot.section.class_level.name}) in this period."
                ),
                field="teacher_user",
                conflicting_slot_id=str(clashing_teacher_slot.id),
                details={
                    "section_name": clashing_teacher_slot.section.name,
                    "class_name": clashing_teacher_slot.section.class_level.name,
                },
            )
        )


def _check_room_clash(
    base_qs: QuerySet[RoutineSlot],
    room_id: UUID | str | None,
    conflicts: list[SlotConflict],
) -> None:
    if not room_id:
        return
    clashing_room_slot = base_qs.filter(room__id=room_id).first()
    if clashing_room_slot:
        room_name = clashing_room_slot.room.name if clashing_room_slot.room else "Selected room"
        conflicts.append(
            SlotConflict(
                code="ROOM_CLASH",
                message=(
                    f"Room '{room_name}' is already occupied by "
                    f"section '{clashing_room_slot.section.name}' in this period."
                ),
                field="room",
                conflicting_slot_id=str(clashing_room_slot.id),
                details={
                    "section_name": clashing_room_slot.section.name,
                },
            )
        )


def validate_routine_slot_conflicts(
    *,
    institution_id: UUID | str,
    section_id: UUID | str,
    weekday: int,
    period_id: UUID | str,
    teacher_user_id: UUID | str | None = None,
    room_id: UUID | str | None = None,
    exclude_slot_id: UUID | str | None = None,
) -> ConflictReport:
    """Validate a single proposed routine slot against database slots for conflicts."""
    conflicts: list[SlotConflict] = []
    warnings: list[str] = []

    if not _check_period_break(institution_id, period_id, conflicts):
        return ConflictReport(is_valid=False, conflicts=conflicts, warnings=warnings)

    _check_weekend_calendar(institution_id, weekday, warnings)

    base_qs = RoutineSlot.objects.filter(
        institution_id=institution_id,
        weekday=weekday,
        period_id=period_id,
    )
    if exclude_slot_id:
        base_qs = base_qs.exclude(id=exclude_slot_id)

    _check_section_clash(base_qs, section_id, conflicts)
    _check_teacher_clash(base_qs, teacher_user_id, conflicts)
    _check_room_clash(base_qs, room_id, conflicts)

    return ConflictReport(
        is_valid=len(conflicts) == 0,
        conflicts=conflicts,
        warnings=warnings,
    )


def validate_routine_slots_batch(
    *,
    institution_id: UUID | str,
    slots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate a batch of proposed slots for internal and external conflicts."""
    results: list[dict[str, Any]] = []
    seen_teacher_periods: dict[tuple[int, str, str], int] = {}
    seen_room_periods: dict[tuple[int, str, str], int] = {}
    seen_section_periods: dict[tuple[int, str, str], int] = {}

    for idx, slot_data in enumerate(slots):
        sec_id = str(slot_data.get("section_id") or "")
        p_id = str(slot_data.get("period_id") or "")
        w_day = int(slot_data.get("weekday", 0))
        t_id = (
            str(slot_data.get("teacher_user_id") or "")
            if slot_data.get("teacher_user_id")
            else None
        )
        r_id = str(slot_data.get("room_id") or "") if slot_data.get("room_id") else None
        slot_id = slot_data.get("id")

        report = validate_routine_slot_conflicts(
            institution_id=institution_id,
            section_id=sec_id,
            weekday=w_day,
            period_id=p_id,
            teacher_user_id=t_id,
            room_id=r_id,
            exclude_slot_id=slot_id,
        )

        sec_key = (w_day, p_id, sec_id)
        if sec_key in seen_section_periods:
            report.conflicts.append(
                SlotConflict(
                    code="BATCH_SECTION_CLASH",
                    message=f"Duplicate section assignment in batch (matches slot index {seen_section_periods[sec_key]}).",
                    field="section",
                )
            )
            report.is_valid = False
        else:
            seen_section_periods[sec_key] = idx

        if t_id:
            t_key = (w_day, p_id, t_id)
            if t_key in seen_teacher_periods:
                report.conflicts.append(
                    SlotConflict(
                        code="BATCH_TEACHER_CLASH",
                        message=f"Teacher is double-booked in batch (matches slot index {seen_teacher_periods[t_key]}).",
                        field="teacher_user",
                    )
                )
                report.is_valid = False
            else:
                seen_teacher_periods[t_key] = idx

        if r_id:
            r_key = (w_day, p_id, r_id)
            if r_key in seen_room_periods:
                report.conflicts.append(
                    SlotConflict(
                        code="BATCH_ROOM_CLASH",
                        message=f"Room is double-booked in batch (matches slot index {seen_room_periods[r_key]}).",
                        field="room",
                    )
                )
                report.is_valid = False
            else:
                seen_room_periods[r_key] = idx

        results.append(
            {
                "slot_index": idx,
                "report": report.to_dict(),
            }
        )

    return results
