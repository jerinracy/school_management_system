"""Models for Transport Management (Vehicles, Drivers, Routes, Assignments, Trips, Boarding, GPS)."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import SoftDeleteMixin, TenantOwnedModel


class VehicleType(models.TextChoices):
    BUS = "bus", "Bus"
    MICROBUS = "microbus", "Microbus"
    VAN = "van", "Van"
    CAR = "car", "Car"


class VehicleStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    MAINTENANCE = "maintenance", "Under Maintenance"
    INACTIVE = "inactive", "Inactive"


class DriverStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ON_LEAVE = "on_leave", "On Leave"
    SUSPENDED = "suspended", "Suspended"
    INACTIVE = "inactive", "Inactive"


class AssigneeType(models.TextChoices):
    STUDENT = "student", "Student"
    STAFF = "staff", "Staff"


class TripDirection(models.TextChoices):
    MORNING_PICKUP = "morning_pickup", "Morning Pickup"
    AFTERNOON_DROP = "afternoon_drop", "Afternoon Drop"
    SPECIAL = "special", "Special Trip"


class TripStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class BoardingEventType(models.TextChoices):
    BOARDED = "boarded", "Boarded"
    DROPPED = "dropped", "Dropped"


class BoardingMethod(models.TextChoices):
    QR = "qr", "QR Code"
    RFID = "rfid", "RFID Card"
    MANUAL = "manual", "Manual"


class Vehicle(TenantOwnedModel, SoftDeleteMixin):
    """School transport vehicle with compliance expiry dates and GPS device token hash."""

    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transport_vehicles",
    )
    registration_no = models.CharField(max_length=40, db_index=True)
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
        default=VehicleType.BUS,
    )
    capacity = models.PositiveSmallIntegerField()
    make_model = models.CharField(max_length=120, blank=True, default="")
    fitness_expiry = models.DateField(null=True, blank=True, db_index=True)
    insurance_expiry = models.DateField(null=True, blank=True, db_index=True)
    tax_token_expiry = models.DateField(null=True, blank=True, db_index=True)
    route_permit_expiry = models.DateField(null=True, blank=True)
    gps_device_id = models.CharField(max_length=80, blank=True, default="", db_index=True)
    gps_token_hash = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=VehicleStatus.choices,
        default=VehicleStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["registration_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "registration_no"],
                condition=Q(is_deleted=False),
                name="unique_active_vehicle_reg_per_institution",
            ),
            models.UniqueConstraint(
                fields=["institution", "gps_device_id"],
                condition=Q(is_deleted=False) & ~Q(gps_device_id=""),
                name="unique_active_gps_device_per_institution",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gt=0),
                name="vehicle_positive_capacity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.registration_no} ({self.capacity} seats)"


class Driver(TenantOwnedModel, SoftDeleteMixin):
    """Driver profile linked to an institutional Staff record."""

    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="driver_profiles",
    )
    license_no = models.CharField(max_length=64, db_index=True)
    license_expiry = models.DateField(db_index=True)
    helper_name = models.CharField(max_length=150, blank=True, default="")
    helper_phone = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=DriverStatus.choices,
        default=DriverStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["license_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "staff"],
                condition=Q(is_deleted=False),
                name="unique_active_driver_staff",
            ),
            models.UniqueConstraint(
                fields=["institution", "license_no"],
                condition=Q(is_deleted=False),
                name="unique_active_driver_license",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staff.full_name_en} ({self.license_no})"


class Route(TenantOwnedModel, SoftDeleteMixin):
    """Transport route with assigned vehicle, driver, and monthly fee."""

    branch = models.ForeignKey(
        "institutions.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transport_routes",
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=32, db_index=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routes",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="routes",
    )
    monthly_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"],
                condition=Q(is_deleted=False),
                name="unique_active_route_code",
            ),
            models.CheckConstraint(
                condition=Q(monthly_fee__gte=0),
                name="route_non_negative_fee",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class RouteStop(TenantOwnedModel):
    """Ordered pickup/drop stop along a Route."""

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="stops")
    name = models.CharField(max_length=150)
    order = models.PositiveSmallIntegerField()
    pickup_time = models.TimeField(null=True, blank=True)
    drop_time = models.TimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    stop_fee_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["route", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "order"],
                name="unique_route_stop_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.route.code} #{self.order}: {self.name}"


class TransportFeeLink(TenantOwnedModel):
    """Links transport routes to a FeeHead in apps/fees for billing."""

    fee_head = models.ForeignKey(
        "fees.FeeHead",
        on_delete=models.PROTECT,
        related_name="transport_fee_links",
    )
    route = models.ForeignKey(
        Route,
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
        related_name="transport_fee_links",
    )
    effective_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_amount__gte=0),
                name="transport_fee_link_non_negative",
            ),
        ]

    def __str__(self) -> str:
        route_label = self.route.code if self.route else "Default"
        return f"{route_label} -> {self.fee_head.name_en} ({self.effective_amount})"


class TransportAssignment(TenantOwnedModel, SoftDeleteMixin):
    """Student or Staff assignment to a transport route and stop for an AcademicSession."""

    session = models.ForeignKey(
        "institutions.AcademicSession",
        on_delete=models.PROTECT,
        related_name="transport_assignments",
    )
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="assignments")
    stop = models.ForeignKey(RouteStop, on_delete=models.PROTECT, related_name="assignments")
    assignee_type = models.CharField(
        max_length=20,
        choices=AssigneeType.choices,
        default=AssigneeType.STUDENT,
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transport_assignments",
    )
    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transport_assignments",
    )
    transport_fee_link = models.ForeignKey(
        TransportFeeLink,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(student__isnull=False, staff__isnull=True)
                    | Q(student__isnull=True, staff__isnull=False)
                ),
                name="transport_assignment_exactly_one_assignee",
            ),
            models.UniqueConstraint(
                fields=["institution", "session", "student"],
                condition=Q(is_deleted=False, is_active=True, student__isnull=False),
                name="unique_active_student_transport_per_session",
            ),
            models.UniqueConstraint(
                fields=["institution", "session", "staff"],
                condition=Q(is_deleted=False, is_active=True, staff__isnull=False),
                name="unique_active_staff_transport_per_session",
            ),
        ]

    def __str__(self) -> str:
        holder = (
            self.student.student_id
            if self.student
            else (self.staff.employee_id if self.staff else "?")
        )
        return f"{holder} -> {self.route.code} ({self.stop.name})"


class VehicleMaintenance(TenantOwnedModel):
    """Maintenance record for a transport vehicle."""

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="maintenances")
    maintenance_date = models.DateField(db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-maintenance_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cost__gte=0),
                name="vehicle_maintenance_non_negative_cost",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle.registration_no}: {self.title} ({self.maintenance_date})"


class FuelLog(TenantOwnedModel):
    """Fuel refill log for a transport vehicle."""

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="fuel_logs")
    filled_at = models.DateTimeField(default=timezone.now, db_index=True)
    liters = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2)
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    receipt_no = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-filled_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(liters__gt=0) & Q(cost__gte=0),
                name="fuel_log_valid_amounts",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle.registration_no}: {self.liters}L"


class TripLog(TenantOwnedModel):
    """Operational trip execution log for a route/vehicle/driver."""

    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="trips")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="trips")
    direction = models.CharField(
        max_length=20,
        choices=TripDirection.choices,
        default=TripDirection.MORNING_PICKUP,
    )
    trip_date = models.DateField(default=timezone.localdate, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=TripStatus.choices,
        default=TripStatus.SCHEDULED,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-trip_date", "-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["institution", "status", "trip_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.route.code} {self.trip_date} ({self.direction}: {self.status})"


class BoardingEvent(TenantOwnedModel):
    """Student boarding/dropping scan event on a TripLog."""

    trip = models.ForeignKey(TripLog, on_delete=models.PROTECT, related_name="boarding_events")
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="boarding_events",
    )
    stop = models.ForeignKey(
        RouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="boarding_events",
    )
    event_type = models.CharField(max_length=20, choices=BoardingEventType.choices)
    event_ts = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(
        max_length=20,
        choices=BoardingMethod.choices,
        default=BoardingMethod.QR,
    )
    idempotency_key = models.CharField(max_length=128, blank=True, default="", db_index=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_boarding_events",
    )

    class Meta:
        ordering = ["-event_ts"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "trip", "student", "event_type"],
                name="unique_boarding_event_per_trip_student_type",
            ),
            models.UniqueConstraint(
                fields=["institution", "idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="unique_boarding_idempotency_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student.student_id} {self.event_type} ({self.trip_id})"


class LiveLocation(TenantOwnedModel):
    """Vehicle GPS location ping."""

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="live_locations")
    trip = models.ForeignKey(
        TripLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="live_locations",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kmh = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["institution", "vehicle", "-recorded_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle.registration_no} @ ({self.latitude}, {self.longitude})"
