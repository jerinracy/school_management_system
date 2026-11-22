"""Data models for attendance policies, daily records, period tracking, corrections, and mobile GPS check-in."""

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present (উপস্থিত)"
    LATE = "late", "Late (বিলম্বিত)"
    ABSENT = "absent", "Absent (অনুপস্থিত)"
    HALF_DAY = "half_day", "Half Day (অর্ধদিবস)"
    LEAVE = "leave", "On Leave (ছুটি)"
    HOLIDAY = "holiday", "Holiday (ছুটির দিন)"
    WEEKEND = "weekend", "Weekend (সাপ্তাহিক ছুটি)"


class PunchDirection(models.TextChoices):
    IN = "in", "Check In"
    OUT = "out", "Check Out"
    AUTO = "auto", "Auto Determine"


class AttendanceSource(models.TextChoices):
    BIOMETRIC = "biometric", "Biometric Terminal"
    MOBILE = "mobile", "Mobile GPS App"
    MANUAL = "manual", "Manual Entry"
    SYSTEM = "system", "System Processed"


class MultiPunchMode(models.TextChoices):
    SINGLE = "single", "Single Punch (Mark Present)"
    ENTRY_EXIT = "entry_exit", "First In & Last Out Duration"
    PERIOD_WISE = "period_wise", "Period-Wise Classroom"


class PeriodAttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    LATE = "late", "Late"
    ABSENT = "absent", "Absent"
    EXCUSED = "excused", "Excused"


class CorrectionStatus(models.TextChoices):
    PENDING = "pending", "Pending Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


def default_weekend_days() -> list[int]:
    """Bangladeshi standard weekend: Friday (4) and Saturday (5)."""
    return [4, 5]


def default_allowed_methods() -> list[str]:
    return ["fingerprint", "face", "rfid", "mobile", "manual"]


class AttendancePolicy(TenantOwnedModel, SoftDeleteMixin):
    """Institutional rules governing arrival windows, late thresholds, and multi-punch computation."""

    name = models.CharField(
        max_length=150, help_text="e.g. 'Morning Shift Students', 'Teachers General'"
    )
    user_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff"), ("all", "All")],
        default="student",
        db_index=True,
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_policies",
    )
    shift = models.ForeignKey(
        "institutions.Shift",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_policies",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_policies",
    )
    start_time = models.TimeField(
        default="08:00:00", help_text="Official shift or school day start time"
    )
    end_time = models.TimeField(
        default="14:00:00", help_text="Official shift or school day departure time"
    )
    grace_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Arrival within grace period is counted as on-time (e.g. 15 mins -> up to 08:15)",
    )
    late_threshold_minutes = models.PositiveIntegerField(
        default=45,
        help_text="Arrival beyond grace up to this threshold is marked Late (e.g. 45 mins -> up to 08:45)",
    )
    half_day_threshold_minutes = models.PositiveIntegerField(
        default=120,
        help_text="Arrival beyond late threshold up to this minute is marked Half Day",
    )
    early_leave_threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Departure earlier than this threshold before end_time flags early leave",
    )
    min_work_duration_minutes = models.PositiveIntegerField(
        default=360,
        help_text="Minimum total work duration for staff to count as full day (e.g. 360 mins = 6 hours)",
    )
    multi_punch_mode = models.CharField(
        max_length=20,
        choices=MultiPunchMode.choices,
        default=MultiPunchMode.ENTRY_EXIT,
    )
    duplicate_window_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Window to suppress accidental double punches on terminal",
    )
    allowed_methods = models.JSONField(
        default=default_allowed_methods,
        blank=True,
        help_text="Recognized authentication methods, e.g. ['fingerprint', 'face', 'rfid']",
    )
    weekend_days = models.JSONField(
        default=default_weekend_days,
        blank=True,
        help_text="Weekday integers: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun",
    )
    geofence_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Campus GPS Latitude for mobile check-in",
    )
    geofence_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Campus GPS Longitude for mobile check-in",
    )
    geofence_radius_meters = models.PositiveIntegerField(
        default=100,
        help_text="Allowable radius in meters around campus coordinates",
    )
    version = models.PositiveIntegerField(default=1)
    effective_from = models.DateField(default=timezone.localdate)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Attendance Policy"
        verbose_name_plural = "Attendance Policies"
        ordering = ["name"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_attendance_policy_name_per_institution",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_user_type_display()} v{self.version})"


class PolicyAssignment(TenantOwnedModel):
    """Scoped binding of attendance policy to branches, shifts, or class levels with priority."""

    policy = models.ForeignKey(
        AttendancePolicy, on_delete=models.CASCADE, related_name="assignments"
    )
    user_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff"), ("all", "All")],
        default="all",
    )
    branch = models.ForeignKey(
        "institutions.Branch",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="policy_assignments",
    )
    shift = models.ForeignKey(
        "institutions.Shift",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="policy_assignments",
    )
    class_level = models.ForeignKey(
        "academics.ClassLevel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="policy_assignments",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="policy_assignments",
    )
    priority = models.PositiveIntegerField(
        default=10,
        help_text="Evaluation priority (higher number takes precedence)",
    )

    class Meta:
        ordering = ["-priority", "-created_at"]

    def __str__(self) -> str:
        return f"Assignment: {self.policy.name} (Priority {self.priority})"


class AttendanceEvent(TenantOwnedModel):
    """Normalized attendance check-in/out event derived from biometric terminal, mobile, or manual entry."""

    user_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff")],
        db_index=True,
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attendance_events",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attendance_events",
    )
    direction = models.CharField(
        max_length=10,
        choices=PunchDirection.choices,
        default=PunchDirection.AUTO,
    )
    method = models.CharField(max_length=30, default="fingerprint")
    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_events",
    )
    timestamp = models.DateTimeField(db_index=True)
    source = models.CharField(
        max_length=20,
        choices=AttendanceSource.choices,
        default=AttendanceSource.BIOMETRIC,
    )
    raw_punch = models.ForeignKey(
        "devices.RawPunch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_events",
    )
    is_processed = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "timestamp"]),
            models.Index(fields=["staff", "timestamp"]),
            models.Index(fields=["institution", "is_processed"]),
        ]

    def __str__(self) -> str:
        target = (
            self.student.name_en
            if self.student
            else (self.staff.full_name_en if self.staff else "Unknown")
        )
        return f"{self.direction.upper()} Event for {target} @ {self.timestamp}"


class DailyAttendance(TenantOwnedModel, SoftDeleteMixin):
    """Daily aggregated attendance record calculated per student or employee."""

    date = models.DateField(db_index=True)
    user_type = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("staff", "Staff")],
        db_index=True,
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="daily_attendances",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="daily_attendances",
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT,
        db_index=True,
    )
    first_in = models.DateTimeField(null=True, blank=True)
    last_out = models.DateTimeField(null=True, blank=True)
    total_minutes = models.PositiveIntegerField(default=0)
    minutes_late = models.PositiveIntegerField(default=0)
    minutes_early_leave = models.PositiveIntegerField(default=0)
    policy = models.ForeignKey(
        AttendancePolicy,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="daily_records",
    )
    policy_version = models.PositiveIntegerField(default=1)
    is_overridden = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_overrides",
    )
    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Daily Attendance"
        verbose_name_plural = "Daily Attendance Records"
        ordering = ["-date", "user_type"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["institution", "student", "date"],
                condition=models.Q(student__isnull=False, is_deleted=False),
                name="unique_daily_student_attendance_per_date",
            ),
            models.UniqueConstraint(
                fields=["institution", "staff", "date"],
                condition=models.Q(staff__isnull=False, is_deleted=False),
                name="unique_daily_staff_attendance_per_date",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["institution", "date", "status"]),
            models.Index(fields=["student", "date"]),
            models.Index(fields=["staff", "date"]),
        ]

    def __str__(self) -> str:
        target = (
            self.student.name_en
            if self.student
            else (self.staff.full_name_en if self.staff else "Unknown")
        )
        return f"{self.date}: {target} ({self.status})"


class PeriodAttendance(TenantOwnedModel, SoftDeleteMixin):
    """Subject and period-level attendance recorded by teachers during class."""

    date = models.DateField(db_index=True)
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.CASCADE,
        related_name="period_attendances",
    )
    routine_slot = models.ForeignKey(
        "academics.RoutineSlot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="period_attendances",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="period_attendances",
    )
    teacher = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conducted_period_attendances",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="period_attendances",
    )
    status = models.CharField(
        max_length=20,
        choices=PeriodAttendanceStatus.choices,
        default=PeriodAttendanceStatus.PRESENT,
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Period Attendance"
        verbose_name_plural = "Period Attendances"
        ordering = ["-date", "section"]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["section", "routine_slot", "student", "date"],
                condition=models.Q(routine_slot__isnull=False, is_deleted=False),
                name="unique_period_slot_student_date",
            ),
            models.UniqueConstraint(
                fields=["section", "subject", "student", "date"],
                condition=models.Q(routine_slot__isnull=True, is_deleted=False),
                name="unique_period_subject_student_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.date} {self.section.name}: {self.student.name_en} ({self.status})"


class AttendanceCorrection(TenantOwnedModel):
    """Administrative change request and audit trail for attendance rectifications."""

    daily_attendance = models.ForeignKey(
        DailyAttendance,
        on_delete=models.CASCADE,
        related_name="corrections",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_attendance_corrections",
    )
    reason = models.TextField(help_text="Justification for attendance correction")
    status_before = models.CharField(max_length=20)
    status_after = models.CharField(max_length=20, choices=AttendanceStatus.choices)
    time_in_before = models.DateTimeField(null=True, blank=True)
    time_in_after = models.DateTimeField(null=True, blank=True)
    time_out_before = models.DateTimeField(null=True, blank=True)
    time_out_after = models.DateTimeField(null=True, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=CorrectionStatus.choices,
        default=CorrectionStatus.PENDING,
        db_index=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_attendance_corrections",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Correction for {self.daily_attendance} ({self.approval_status})"


class MobileCheckin(TenantOwnedModel):
    """Mobile GPS geofenced check-in log with coordinate validation and selfie snapshot."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_checkins",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mobile_checkins",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_meters = models.FloatField(default=0.0)
    is_within_geofence = models.BooleanField(default=False)
    geofence_distance_meters = models.FloatField(default=0.0)
    selfie_image = models.ImageField(upload_to="attendance/selfies/", null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    attendance_event = models.ForeignKey(
        AttendanceEvent,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mobile_checkin_origins",
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"Mobile Checkin: {self.user.username} @ {self.timestamp} (Valid: {self.is_within_geofence})"


class StudentLeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"


class StudentLeaveApplicantType(models.TextChoices):
    GUARDIAN = "guardian", "Guardian"
    STUDENT = "student", "Student"


class StudentLeaveRequest(TenantOwnedModel):
    """Student leave application submitted by Guardian or Student, reviewed by Class Teacher."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    enrollment = models.ForeignKey(
        "students.StudentEnrollment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leave_requests",
    )
    section = models.ForeignKey(
        "academics.Section",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_leave_requests",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_leave_requests",
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_student_leave_requests",
    )
    applicant_type = models.CharField(
        max_length=20,
        choices=StudentLeaveApplicantType.choices,
        default=StudentLeaveApplicantType.GUARDIAN,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.PositiveIntegerField(default=1)
    reason_category = models.CharField(max_length=50, default="medical")
    reason = models.TextField()
    attachment = models.FileField(upload_to="attendance/student_leaves/", null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StudentLeaveStatus.choices,
        default=StudentLeaveStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_student_leave_requests",
    )
    reviewer_remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    guardian_notified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "status"]),
            models.Index(fields=["section", "status"]),
            models.Index(fields=["student", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"Leave for {self.student.name_en} ({self.start_date} to {self.end_date}) [{self.status}]"

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be earlier than start date."})
