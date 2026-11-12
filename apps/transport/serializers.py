"""Serializers for Transport Management."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.transport.models import (
    BoardingEvent,
    BoardingEventType,
    BoardingMethod,
    Driver,
    FuelLog,
    LiveLocation,
    Route,
    RouteStop,
    TransportAssignment,
    TransportFeeLink,
    TripDirection,
    TripLog,
    Vehicle,
    VehicleMaintenance,
)


class VehicleSerializer(serializers.ModelSerializer):
    has_gps_token = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "institution",
            "branch",
            "registration_no",
            "vehicle_type",
            "capacity",
            "make_model",
            "fitness_expiry",
            "insurance_expiry",
            "tax_token_expiry",
            "route_permit_expiry",
            "gps_device_id",
            "has_gps_token",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "has_gps_token", "created_at", "updated_at"]

    def get_has_gps_token(self, obj: Vehicle) -> bool:
        return bool(obj.gps_token_hash)


class GpsTokenRotateSerializer(serializers.Serializer):
    gps_device_id = serializers.CharField(required=False, allow_blank=False, max_length=80)


class GpsTokenRotateResponseSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField()
    gps_device_id = serializers.CharField()
    gps_token = serializers.CharField()


class DriverSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name_en", read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "institution",
            "staff",
            "staff_name",
            "license_no",
            "license_expiry",
            "helper_name",
            "helper_phone",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class RouteStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteStop
        fields = [
            "id",
            "institution",
            "route",
            "name",
            "order",
            "pickup_time",
            "drop_time",
            "latitude",
            "longitude",
            "stop_fee_override",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class RouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    vehicle_registration = serializers.CharField(
        source="vehicle.registration_no", read_only=True, default=""
    )

    class Meta:
        model = Route
        fields = [
            "id",
            "institution",
            "branch",
            "name",
            "code",
            "vehicle",
            "vehicle_registration",
            "driver",
            "monthly_fee",
            "is_active",
            "stops",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class TransportFeeLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportFeeLink
        fields = [
            "id",
            "institution",
            "fee_head",
            "route",
            "session",
            "effective_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class TransportAssignmentSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.name", read_only=True)
    stop_name = serializers.CharField(source="stop.name", read_only=True)

    class Meta:
        model = TransportAssignment
        fields = [
            "id",
            "institution",
            "session",
            "route",
            "route_name",
            "stop",
            "stop_name",
            "assignee_type",
            "student",
            "staff",
            "transport_fee_link",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "assignee_type", "created_at", "updated_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        student = attrs.get("student", getattr(self.instance, "student", None))
        staff = attrs.get("staff", getattr(self.instance, "staff", None))
        if bool(student) == bool(staff):
            raise serializers.ValidationError("Provide exactly one of 'student' or 'staff'.")
        return attrs


class VehicleMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleMaintenance
        fields = [
            "id",
            "institution",
            "vehicle",
            "maintenance_date",
            "title",
            "description",
            "cost",
            "odometer_km",
            "next_due_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class FuelLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelLog
        fields = [
            "id",
            "institution",
            "vehicle",
            "filled_at",
            "liters",
            "cost",
            "odometer_km",
            "receipt_no",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class TripLogSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.name", read_only=True)
    vehicle_registration = serializers.CharField(source="vehicle.registration_no", read_only=True)

    class Meta:
        model = TripLog
        fields = [
            "id",
            "institution",
            "route",
            "route_name",
            "vehicle",
            "vehicle_registration",
            "driver",
            "direction",
            "trip_date",
            "started_at",
            "ended_at",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TripStartSerializer(serializers.Serializer):
    route = serializers.UUIDField()
    vehicle = serializers.UUIDField(required=False, allow_null=True)
    driver = serializers.UUIDField(required=False, allow_null=True)
    direction = serializers.ChoiceField(
        choices=TripDirection.choices, default=TripDirection.MORNING_PICKUP
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class TripEndSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BoardingEventSerializer(serializers.ModelSerializer):
    student_code = serializers.CharField(source="student.student_id", read_only=True)
    student_name = serializers.CharField(source="student.name_en", read_only=True)

    class Meta:
        model = BoardingEvent
        fields = [
            "id",
            "institution",
            "trip",
            "student",
            "student_code",
            "student_name",
            "stop",
            "event_type",
            "event_ts",
            "method",
            "idempotency_key",
            "recorded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BoardingScanSerializer(serializers.Serializer):
    trip = serializers.UUIDField()
    student = serializers.UUIDField()
    stop = serializers.UUIDField(required=False, allow_null=True)
    event_type = serializers.ChoiceField(choices=BoardingEventType.choices)
    method = serializers.ChoiceField(choices=BoardingMethod.choices, default=BoardingMethod.QR)
    event_ts = serializers.DateTimeField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class LiveLocationSerializer(serializers.ModelSerializer):
    vehicle_registration = serializers.CharField(source="vehicle.registration_no", read_only=True)

    class Meta:
        model = LiveLocation
        fields = [
            "id",
            "institution",
            "vehicle",
            "vehicle_registration",
            "trip",
            "latitude",
            "longitude",
            "speed_kmh",
            "recorded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GpsPingSerializer(serializers.Serializer):
    gps_device_id = serializers.CharField(required=False, allow_blank=True, default="")
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    speed_kmh = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, default=Decimal("0.00")
    )
    recorded_at = serializers.DateTimeField(required=False, allow_null=True)
