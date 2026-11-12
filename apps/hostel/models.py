"""Models for Hostel Management (Hostels, Rooms, Beds, Allocations, Attendance, GatePass, Meals, Visitors)."""

from datetime import time
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class HostelType(models.TextChoices):
    BOYS = "boys", "Boys Hostel"
    GIRLS = "girls", "Girls Hostel"
    MIXED = "mixed", "Mixed Hostel"


class BedStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    OCCUPIED = "occupied", "Occupied"
    MAINTENANCE = "maintenance", "Maintenance"


class HostelAttendanceEventType(models.TextChoices):
    NIGHT_ROLL_CALL = "night_roll_call", "Night Roll Call"
    BIOMETRIC_IN = "biometric_in", "Biometric Check-In"
    BIOMETRIC_OUT = "biometric_out", "Biometric Check-Out"


class HostelAttendanceStatus(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    ON_GATE_PASS = "on_gate_pass", "On Gate Pass"
    LATE = "late", "Late"


class GatePassStatus(models.TextChoices):
    PENDING_GUARDIAN_OTP = "pending_guardian_otp", "Pending Guardian OTP"
    GUARDIAN_CONFIRMED = "guardian_confirmed", "Guardian Confirmed"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CHECKED_OUT = "checked_out", "Checked Out"
    RETURNED = "returned", "Returned"
    OVERDUE = "overdue", "Overdue"


class MealType(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    LUNCH = "lunch", "Lunch"
    SNACKS = "snacks", "Snacks"
    DINNER = "dinner", "Dinner"


class Hostel(TenantOwnedModel, SoftDeleteMixin):
    """Residential hostel building/wing."""

    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hostels",
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=32, db_index=True)
    hostel_type = models.CharField(
        max_length=20,
        choices=HostelType.choices,
        default=HostelType.BOYS,
    )
    warden = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_hostels",
    )
    curfew_time = models.TimeField(default=time(21, 0))
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=Q(is_deleted=False),
                name="unique_active_hostel_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Room(TenantOwnedModel, SoftDeleteMixin):
    """Room within a Hostel."""

    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="rooms")
    room_number = models.CharField(max_length=32, db_index=True)
    floor = models.CharField(max_length=32, blank=True, default="")
    capacity = models.PositiveSmallIntegerField(default=4)
    monthly_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["hostel", "room_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "room_number"],
                condition=Q(is_deleted=False),
                name="unique_active_room_per_hostel",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gt=0) & Q(monthly_fee__gte=0),
                name="hostel_room_valid_capacity_fee",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.hostel.code}-{self.room_number}"


class Bed(TenantOwnedModel, SoftDeleteMixin):
    """Individual bed within a Room."""

    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="beds")
    bed_number = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=BedStatus.choices,
        default=BedStatus.AVAILABLE,
        db_index=True,
    )

    class Meta:
        ordering = ["room", "bed_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "bed_number"],
                condition=Q(is_deleted=False),
                name="unique_active_bed_per_room",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.room} / Bed {self.bed_number}"


class HostelFeeLink(TenantOwnedModel):
    """Links Hostel/AcademicSession to a FeeHead in apps/fees."""

    fee_head = models.ForeignKey(
        "fees.FeeHead",
        on_delete=models.PROTECT,
        related_name="hostel_fee_links",
    )
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fee_links",
    )
    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hostel_fee_links",
    )
    effective_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_amount__gte=0),
                name="hostel_fee_link_non_negative",
            ),
        ]

    def __str__(self) -> str:
        label = self.hostel.code if self.hostel else "Default"
        return f"{label} -> {self.fee_head.name_en} ({self.effective_amount})"


class HostelAllocation(TenantOwnedModel, SoftDeleteMixin):
    """Student bed allocation with full historical tracking."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.PROTECT,
        related_name="hostel_allocations",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="hostel_allocations",
    )
    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="allocations")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="allocations")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="allocations")
    hostel_fee_link = models.ForeignKey(
        HostelFeeLink,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocations",
    )
    allocated_date = models.DateField(default=timezone.localdate)
    vacated_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-allocated_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bed"],
                condition=Q(is_deleted=False, is_active=True),
                name="unique_active_allocation_per_bed",
            ),
            models.UniqueConstraint(
                fields=["institution", "session", "student"],
                condition=Q(is_deleted=False, is_active=True),
                name="unique_active_hostel_allocation_per_student_session",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} -> {self.bed}"


class HostelAttendance(TenantOwnedModel):
    """Night roll call or biometric hostel attendance event."""

    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="attendances")
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="hostel_attendances",
    )
    attendance_date = models.DateField(default=timezone.localdate, db_index=True)
    event_type = models.CharField(
        max_length=24,
        choices=HostelAttendanceEventType.choices,
        default=HostelAttendanceEventType.NIGHT_ROLL_CALL,
    )
    status = models.CharField(
        max_length=20,
        choices=HostelAttendanceStatus.choices,
        default=HostelAttendanceStatus.PRESENT,
    )
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hostel_attendances_recorded",
    )

    class Meta:
        ordering = ["-attendance_date", "-recorded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "student", "attendance_date", "event_type"],
                name="unique_hostel_attendance_per_day_event",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.student.student_id} {self.attendance_date} ({self.event_type}: {self.status})"
        )


class GatePass(TenantOwnedModel):
    """Student leave/gate pass requiring guardian OTP confirmation and warden approval."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="gate_passes",
    )
    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="gate_passes")
    allocation = models.ForeignKey(
        HostelAllocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gate_passes",
    )
    reason = models.TextField()
    destination = models.CharField(max_length=255, blank=True, default="")
    expected_out_at = models.DateTimeField()
    expected_return_at = models.DateTimeField()
    actual_out_at = models.DateTimeField(null=True, blank=True)
    actual_return_at = models.DateTimeField(null=True, blank=True)
    guardian_otp_hash = models.CharField(max_length=128, blank=True, default="")
    guardian_otp_expires_at = models.DateTimeField(null=True, blank=True)
    guardian_confirmed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_gate_passes",
    )
    status = models.CharField(
        max_length=24,
        choices=GatePassStatus.choices,
        default=GatePassStatus.PENDING_GUARDIAN_OTP,
        db_index=True,
    )
    curfew_alert_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["institution", "status", "expected_return_at"]),
        ]

    def __str__(self) -> str:
        return f"GatePass {self.student.student_id} ({self.status})"


class MealPlan(TenantOwnedModel, SoftDeleteMixin):
    """Hostel meal schedule and per-meal cost."""

    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="meal_plans")
    name = models.CharField(max_length=120)
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    menu_description = models.TextField(blank=True, default="")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["hostel", "meal_type", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_cost__gte=0),
                name="meal_plan_non_negative_cost",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.hostel.code} {self.meal_type}: {self.name}"


class MealAttendance(TenantOwnedModel):
    """Daily student meal consumption tracking."""

    meal_plan = models.ForeignKey(MealPlan, on_delete=models.PROTECT, related_name="attendances")
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="meal_attendances",
    )
    meal_date = models.DateField(default=timezone.localdate, db_index=True)
    consumed = models.BooleanField(default=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="meal_attendances_recorded",
    )

    class Meta:
        ordering = ["-meal_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "meal_plan", "student", "meal_date"],
                name="unique_meal_attendance_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} - {self.meal_plan.meal_type} ({self.meal_date})"


class HostelVisitorLog(TenantOwnedModel):
    """Hostel visitor check-in / check-out log."""

    hostel = models.ForeignKey(Hostel, on_delete=models.PROTECT, related_name="visitor_logs")
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="hostel_visitors",
    )
    visitor_name = models.CharField(max_length=150)
    visitor_phone = models.CharField(max_length=20)
    relation = models.CharField(max_length=64, blank=True, default="")
    nid_or_id_no = models.CharField(max_length=64, blank=True, default="")
    purpose = models.CharField(max_length=255, blank=True, default="")
    check_in_at = models.DateTimeField(default=timezone.now, db_index=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hostel_visitors_logged",
    )

    class Meta:
        ordering = ["-check_in_at"]

    def __str__(self) -> str:
        return f"{self.visitor_name} -> {self.student.student_id}"
