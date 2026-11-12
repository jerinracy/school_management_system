"""Django Admin registrations for Transport Management."""

from django.contrib import admin

from apps.transport.models import (
    BoardingEvent,
    Driver,
    FuelLog,
    LiveLocation,
    Route,
    RouteStop,
    TransportAssignment,
    TransportFeeLink,
    TripLog,
    Vehicle,
    VehicleMaintenance,
)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration_no", "vehicle_type", "capacity", "status", "fitness_expiry")
    search_fields = ("registration_no", "gps_device_id")
    list_filter = ("vehicle_type", "status")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("staff", "license_no", "license_expiry", "status")
    search_fields = ("license_no", "staff__full_name_en")
    list_filter = ("status",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "vehicle", "driver", "monthly_fee", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ("route", "order", "name", "pickup_time", "drop_time")


@admin.register(TransportFeeLink)
class TransportFeeLinkAdmin(admin.ModelAdmin):
    list_display = ("route", "session", "fee_head", "effective_amount")


@admin.register(TransportAssignment)
class TransportAssignmentAdmin(admin.ModelAdmin):
    list_display = ("route", "stop", "assignee_type", "student", "staff", "is_active")
    list_filter = ("assignee_type", "is_active")


@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "maintenance_date", "title", "cost")


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "filled_at", "liters", "cost", "odometer_km")


@admin.register(TripLog)
class TripLogAdmin(admin.ModelAdmin):
    list_display = ("route", "vehicle", "driver", "trip_date", "direction", "status")
    list_filter = ("status", "direction")


@admin.register(BoardingEvent)
class BoardingEventAdmin(admin.ModelAdmin):
    list_display = ("trip", "student", "event_type", "method", "event_ts")
    list_filter = ("event_type", "method")


@admin.register(LiveLocation)
class LiveLocationAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "latitude", "longitude", "speed_kmh", "recorded_at")
