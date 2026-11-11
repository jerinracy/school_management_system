"""Table-driven unit tests for the pure Attendance Rule Engine."""

from datetime import date, datetime, time

import pytest
from django.utils import timezone

from apps.attendance.models import (
    AttendancePolicy,
    AttendanceStatus,
    MultiPunchMode,
)
from apps.attendance.services.rule_engine import evaluate_daily_status
from apps.institutions.models import Institution


def _make_tz_dt(d: date, h: int, m: int) -> datetime:
    dt = datetime(d.year, d.month, d.day, h, m)
    return timezone.make_aware(dt, timezone.get_current_timezone())


@pytest.fixture
def policy(db) -> AttendancePolicy:
    inst = Institution.objects.create(name_en="Rule Test School", eiin="991122")
    return AttendancePolicy.objects.create(
        institution=inst,
        name="Test Policy",
        user_type="student",
        start_time=time(8, 0),
        end_time=time(14, 0),
        grace_minutes=15,
        late_threshold_minutes=45,
        half_day_threshold_minutes=120,
        early_leave_threshold_minutes=30,
        min_work_duration_minutes=360,
        multi_punch_mode=MultiPunchMode.ENTRY_EXIT,
    )


def test_on_time_arrival_within_grace(policy):
    target = date(2026, 3, 2)  # Monday
    # Arrival at 08:10 (start is 08:00, grace is 15 mins)
    punches = [_make_tz_dt(target, 8, 10), _make_tz_dt(target, 14, 5)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.PRESENT
    assert res.minutes_late == 0
    assert res.minutes_early_leave == 0
    assert res.total_minutes == 355


def test_late_arrival_within_threshold(policy):
    target = date(2026, 3, 2)
    # Arrival at 08:30 (start is 08:00, grace 15m, late threshold 45m)
    punches = [_make_tz_dt(target, 8, 30), _make_tz_dt(target, 14, 0)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.LATE
    assert res.minutes_late == 30
    assert res.minutes_early_leave == 0


def test_half_day_arrival(policy):
    target = date(2026, 3, 2)
    # Arrival at 09:30 (90 mins after 08:00, between 45m and 120m threshold)
    punches = [_make_tz_dt(target, 9, 30), _make_tz_dt(target, 14, 0)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.HALF_DAY
    assert res.minutes_late == 90


def test_extreme_late_marked_absent(policy):
    target = date(2026, 3, 2)
    # Arrival at 11:00 (180 mins after 08:00, exceeding 120m threshold)
    punches = [_make_tz_dt(target, 11, 0), _make_tz_dt(target, 14, 0)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.ABSENT
    assert res.minutes_late == 180


def test_early_leave_flag(policy):
    target = date(2026, 3, 2)
    # Departure at 13:00 (end_time is 14:00, early threshold is 30m)
    punches = [_make_tz_dt(target, 8, 0), _make_tz_dt(target, 13, 0)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.PRESENT
    assert res.minutes_early_leave == 60


def test_staff_min_work_duration(policy):
    policy.user_type = "staff"
    policy.save()

    target = date(2026, 3, 2)
    # 08:00 to 12:00 = 240 mins (min_work_duration is 360 mins)
    punches = [_make_tz_dt(target, 8, 0), _make_tz_dt(target, 12, 0)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    # Should be demoted from PRESENT to HALF_DAY due to short duration
    assert res.status == AttendanceStatus.HALF_DAY
    assert res.total_minutes == 240


def test_single_punch_mode(policy):
    policy.multi_punch_mode = MultiPunchMode.SINGLE
    policy.save()

    target = date(2026, 3, 2)
    punches = [_make_tz_dt(target, 8, 5)]

    res = evaluate_daily_status(events=punches, policy=policy, target_date=target)
    assert res.status == AttendanceStatus.PRESENT
    assert res.first_in is not None
    assert res.last_out == res.first_in


def test_weekend_and_holiday_without_punches(policy):
    target = date(2026, 3, 6)  # Friday

    res_weekend = evaluate_daily_status(
        events=[], policy=policy, target_date=target, is_weekend=True
    )
    assert res_weekend.status == AttendanceStatus.WEEKEND

    res_holiday = evaluate_daily_status(
        events=[], policy=policy, target_date=target, is_holiday=True
    )
    assert res_holiday.status == AttendanceStatus.HOLIDAY


def test_approved_leave_override(policy):
    target = date(2026, 3, 2)
    punches = [_make_tz_dt(target, 8, 0)]

    res = evaluate_daily_status(
        events=punches, policy=policy, target_date=target, has_approved_leave=True
    )
    assert res.status == AttendanceStatus.LEAVE
