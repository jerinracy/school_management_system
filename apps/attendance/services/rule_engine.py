"""Pure, deterministic attendance evaluation rule engine."""

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Sequence

from django.utils import timezone

from apps.attendance.models import (
    AttendanceEvent,
    AttendancePolicy,
    AttendanceStatus,
    MultiPunchMode,
)


@dataclass(frozen=True)
class EvaluationResult:
    """Computed attendance metrics for a specific person on a date."""

    status: str
    first_in: datetime | None
    last_out: datetime | None
    total_minutes: int
    minutes_late: int
    minutes_early_leave: int
    remarks: str = ""


def _combine_date_time(d: date, t: time | str) -> datetime:
    if isinstance(t, str):
        t = time.fromisoformat(t)
    dt = datetime.combine(d, t)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _check_special_absence(
    has_approved_leave: bool,
    is_holiday: bool,
    is_weekend: bool,
) -> EvaluationResult | None:
    if has_approved_leave:
        return EvaluationResult(
            status=AttendanceStatus.LEAVE,
            first_in=None,
            last_out=None,
            total_minutes=0,
            minutes_late=0,
            minutes_early_leave=0,
            remarks="Approved institutional leave",
        )
    if is_holiday:
        return EvaluationResult(
            status=AttendanceStatus.HOLIDAY,
            first_in=None,
            last_out=None,
            total_minutes=0,
            minutes_late=0,
            minutes_early_leave=0,
            remarks="Institutional holiday",
        )
    if is_weekend:
        return EvaluationResult(
            status=AttendanceStatus.WEEKEND,
            first_in=None,
            last_out=None,
            total_minutes=0,
            minutes_late=0,
            minutes_early_leave=0,
            remarks="Configured weekend",
        )
    return None


def _extract_sorted_timestamps(events: Sequence[AttendanceEvent | datetime]) -> list[datetime]:
    timestamps: list[datetime] = []
    for item in events:
        if isinstance(item, AttendanceEvent):
            ts = item.timestamp
        elif isinstance(item, datetime):
            ts = item
        else:
            continue

        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts, timezone.get_current_timezone())
        timestamps.append(ts)
    timestamps.sort()
    return timestamps


def _evaluate_arrival(
    first_in: datetime, policy: AttendancePolicy, target_date: date
) -> tuple[str, int]:
    scheduled_start = _combine_date_time(target_date, policy.start_time)
    diff_arrival = int((first_in - scheduled_start).total_seconds() / 60)

    if diff_arrival <= policy.grace_minutes:
        return AttendanceStatus.PRESENT, 0
    if diff_arrival <= policy.late_threshold_minutes:
        return AttendanceStatus.LATE, max(0, diff_arrival)
    if diff_arrival <= policy.half_day_threshold_minutes:
        return AttendanceStatus.HALF_DAY, max(0, diff_arrival)
    return AttendanceStatus.ABSENT, max(0, diff_arrival)


def _evaluate_departure(
    last_out: datetime | None, policy: AttendancePolicy, target_date: date
) -> int:
    scheduled_end = _combine_date_time(target_date, policy.end_time)
    if last_out and last_out < scheduled_end:
        early_diff = int((scheduled_end - last_out).total_seconds() / 60)
        if early_diff >= policy.early_leave_threshold_minutes:
            return early_diff
    return 0


def evaluate_daily_status(
    events: Sequence[AttendanceEvent | datetime],
    policy: AttendancePolicy,
    target_date: date,
    is_holiday: bool = False,
    is_weekend: bool = False,
    has_approved_leave: bool = False,
) -> EvaluationResult:
    """Evaluate raw attendance events against institutional policy rules.

    Pure function with zero database side-effects.
    """
    if has_approved_leave:
        result = _check_special_absence(
            has_approved_leave=True, is_holiday=is_holiday, is_weekend=is_weekend
        )
        if result:
            return result

    timestamps = _extract_sorted_timestamps(events)

    if not timestamps:
        special = _check_special_absence(
            has_approved_leave=False, is_holiday=is_holiday, is_weekend=is_weekend
        )
        if special:
            return special
        return EvaluationResult(
            status=AttendanceStatus.ABSENT,
            first_in=None,
            last_out=None,
            total_minutes=0,
            minutes_late=0,
            minutes_early_leave=0,
            remarks="No check-in recorded",
        )

    first_in = timestamps[0]
    if policy.multi_punch_mode == MultiPunchMode.SINGLE:
        last_out = first_in
        total_minutes = 0
    elif len(timestamps) > 1:
        last_out = timestamps[-1]
        total_minutes = max(0, int((last_out - first_in).total_seconds() / 60))
    else:
        last_out = first_in
        total_minutes = 0

    computed_status, minutes_late = _evaluate_arrival(first_in, policy, target_date)
    minutes_early_leave = _evaluate_departure(last_out, policy, target_date)

    if (
        policy.user_type in ["staff", "all"]
        and policy.min_work_duration_minutes > 0
        and policy.multi_punch_mode != MultiPunchMode.SINGLE
    ):
        if total_minutes < policy.min_work_duration_minutes:
            if computed_status in [AttendanceStatus.PRESENT, AttendanceStatus.LATE]:
                computed_status = AttendanceStatus.HALF_DAY

    return EvaluationResult(
        status=computed_status,
        first_in=first_in,
        last_out=last_out,
        total_minutes=total_minutes,
        minutes_late=minutes_late,
        minutes_early_leave=minutes_early_leave,
    )
