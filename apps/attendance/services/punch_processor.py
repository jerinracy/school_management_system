"""Raw punch ingestion pipeline normalizing device records into attendance events."""

import logging
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import (
    AttendanceEvent,
    AttendanceSource,
    PunchDirection,
)
from apps.devices.models import RawPunch, RawPunchStatus

logger = logging.getLogger(__name__)


def _resolve_punch_direction(punch_state: str) -> str:
    if punch_state == "0":
        return PunchDirection.IN
    if punch_state == "1":
        return PunchDirection.OUT
    return PunchDirection.AUTO


def _is_duplicate_punch(
    punch: RawPunch,
    student: Any,
    staff: Any,
    events_to_create: list[AttendanceEvent],
) -> bool:
    window_start = punch.device_time - timedelta(seconds=60)
    window_end = punch.device_time + timedelta(seconds=60)

    for ev in events_to_create:
        if student and ev.student == student and window_start <= ev.timestamp <= window_end:
            return True
        if staff and ev.staff == staff and window_start <= ev.timestamp <= window_end:
            return True

    if student:
        return AttendanceEvent.objects.filter(
            student=student,
            timestamp__gte=window_start,
            timestamp__lte=window_end,
        ).exists()
    if staff:
        return AttendanceEvent.objects.filter(
            staff=staff,
            timestamp__gte=window_start,
            timestamp__lte=window_end,
        ).exists()
    return False


def process_raw_punches(batch_size: int = 500) -> tuple[int, int]:
    """Convert unprocessed, resolved RawPunch records into AttendanceEvents and trigger daily recalculation.

    Returns:
        tuple of (events_created_count, punches_processed_count)
    """
    raw_punches = list(
        RawPunch.objects.filter(
            status=RawPunchStatus.UNPROCESSED,
        )
        .exclude(resolved_student__isnull=True, resolved_staff__isnull=True)
        .select_related("device", "resolved_student", "resolved_staff", "institution")
        .order_by("device_time")[:batch_size]
    )

    if not raw_punches:
        return 0, 0

    events_to_create: list[AttendanceEvent] = []
    punches_to_mark_processed: list[Any] = []
    affected_targets: set[tuple[Any, str, Any, Any]] = set()

    for punch in raw_punches:
        user_type = "student" if punch.resolved_student else "staff"
        student = punch.resolved_student
        staff = punch.resolved_staff
        target_id = student.id if student else staff.id  # type: ignore[union-attr]
        punch_date = punch.device_time.date()

        direction = _resolve_punch_direction(punch.punch_state)

        if not _is_duplicate_punch(punch, student, staff, events_to_create):
            event = AttendanceEvent(
                institution=punch.institution,
                user_type=user_type,
                student=student,
                staff=staff,
                direction=direction,
                method=punch.verify_type,
                device=punch.device,
                timestamp=punch.device_time,
                source=AttendanceSource.BIOMETRIC,
                raw_punch=punch,
                is_processed=True,
            )
            events_to_create.append(event)
            affected_targets.add((punch.institution, user_type, target_id, punch_date))

        punches_to_mark_processed.append(punch.id)

    with transaction.atomic():
        if events_to_create:
            AttendanceEvent.objects.bulk_create(events_to_create)

        if punches_to_mark_processed:
            RawPunch.objects.filter(id__in=punches_to_mark_processed).update(
                status=RawPunchStatus.PROCESSED,
                updated_at=timezone.now(),
            )

    # Trigger daily attendance recalculation for affected persons
    from apps.attendance.services.attendance_service import update_daily_attendance_for_person

    for inst, u_type, target_id, p_date in affected_targets:
        try:
            update_daily_attendance_for_person(
                institution=inst,
                user_type=u_type,
                person_id=target_id,
                target_date=p_date,
            )
        except Exception as err:
            logger.error(
                "Failed to update daily attendance for %s %s on %s: %s",
                u_type,
                target_id,
                p_date,
                err,
            )

    logger.info(
        "Processed %d raw punches into %d attendance events across %d daily targets",
        len(punches_to_mark_processed),
        len(events_to_create),
        len(affected_targets),
    )
    return len(events_to_create), len(punches_to_mark_processed)
