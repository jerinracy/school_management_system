"""Service exports for the Attendance Engine."""

from apps.attendance.services.attendance_service import (
    decide_attendance_correction,
    mark_daily_absentees_for_date,
    recompute_daily_attendance,
    request_attendance_correction,
    resolve_effective_policy,
    submit_manual_attendance,
    update_daily_attendance_for_person,
)
from apps.attendance.services.geofence_service import (
    haversine_distance_meters,
    validate_geofence,
)
from apps.attendance.services.punch_processor import process_raw_punches
from apps.attendance.services.rule_engine import (
    EvaluationResult,
    evaluate_daily_status,
)

__all__ = [
    "EvaluationResult",
    "decide_attendance_correction",
    "evaluate_daily_status",
    "haversine_distance_meters",
    "mark_daily_absentees_for_date",
    "process_raw_punches",
    "recompute_daily_attendance",
    "request_attendance_correction",
    "resolve_effective_policy",
    "submit_manual_attendance",
    "update_daily_attendance_for_person",
    "validate_geofence",
]
