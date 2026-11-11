"""Asia/Dhaka timezone helpers."""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

DHAKA_TZ = ZoneInfo("Asia/Dhaka")


def get_dhaka_now() -> datetime:
    """Return the current datetime localized to Asia/Dhaka."""
    return timezone.now().astimezone(DHAKA_TZ)


def to_dhaka_time(dt: datetime) -> datetime:
    """Convert any aware datetime to Asia/Dhaka timezone."""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(DHAKA_TZ)


def format_dhaka_datetime(dt: datetime, fmt: str = "%Y-%m-%d %I:%M:%S %p") -> str:
    """Format datetime in Asia/Dhaka."""
    return to_dhaka_time(dt).strftime(fmt)
