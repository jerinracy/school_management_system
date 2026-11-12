"""Business services for Transport Management."""

import hashlib
import hmac
import logging
import secrets
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.guardians.models import StudentGuardian
from apps.transport.models import (
    AssigneeType,
    BoardingEvent,
    BoardingMethod,
    Driver,
    LiveLocation,
    Route,
    RouteStop,
    TransportAssignment,
    TransportFeeLink,
    TripDirection,
    TripLog,
    TripStatus,
    Vehicle,
    VehicleStatus,
)

logger = logging.getLogger(__name__)


def hash_gps_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a raw GPS device token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def rotate_vehicle_gps_token(*, vehicle: Vehicle, gps_device_id: str | None = None) -> str:
    """Generate and persist a hashed GPS token for a Vehicle, returning raw token once."""
    raw_token = secrets.token_urlsafe(32)
    if gps_device_id is not None:
        vehicle.gps_device_id = gps_device_id
    vehicle.gps_token_hash = hash_gps_token(raw_token)
    vehicle.save(update_fields=["gps_device_id", "gps_token_hash", "updated_at"])
    return raw_token


def _notify_guardians_boarding(event: BoardingEvent) -> None:
    """Best-effort guardian notification when a student boards or drops off."""
    try:
        from apps.communications.services.notification_service import dispatch_event_notification

        guardians = StudentGuardian.objects.select_related("guardian", "guardian__user").filter(
            institution_id=event.institution_id,
            student_id=event.student_id,
            guardian__is_deleted=False,
            guardian__user__isnull=False,
        )
        users = [sg.guardian.user for sg in guardians if sg.guardian.user is not None]
        if not users:
            return
        dispatch_event_notification(
            institution=event.institution,
            event_type=f"transport_{event.event_type}",
            recipient_users=users,
            context={
                "student_id": event.student.student_id,
                "student_name": event.student.name_en,
                "event_type": event.event_type,
                "route": event.trip.route.name,
                "stop": event.stop.name if event.stop else "",
                "event_ts": event.event_ts.isoformat(),
            },
            source_module="transport",
            reference_id=event.id,
        )
    except Exception:
        logger.exception("Failed to dispatch transport boarding notification")


@transaction.atomic
def assign_transport(
    *,
    institution: Any,
    session: Any,
    route: Route,
    stop: RouteStop,
    student: Any = None,
    staff: Any = None,
    transport_fee_link: TransportFeeLink | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TransportAssignment:
    """Assign a student or staff member to a route & stop with atomic vehicle capacity check."""
    if bool(student) == bool(staff):
        raise ValidationError("Provide exactly one of student or staff.")
    if route.institution_id != institution.id or route.is_deleted or not route.is_active:
        raise ValidationError("Active route not found in this institution.")
    if stop.route_id != route.id:
        raise ValidationError("Selected stop does not belong to the chosen route.")
    if session.institution_id != institution.id:
        raise ValidationError("Academic session belongs to another institution.")

    locked_route = Route.objects.select_for_update().select_related("vehicle").get(id=route.id)
    if locked_route.vehicle_id:
        vehicle = Vehicle.objects.select_for_update().get(id=locked_route.vehicle_id)
        if vehicle.status == VehicleStatus.INACTIVE:
            raise ValidationError("Assigned vehicle is inactive.")
        active_count = TransportAssignment.objects.filter(
            institution=institution,
            session=session,
            route=locked_route,
            is_deleted=False,
            is_active=True,
        ).count()
        if active_count >= vehicle.capacity:
            raise ValidationError(
                f"Vehicle capacity reached ({active_count}/{vehicle.capacity} seats)."
            )

    assignee_type = AssigneeType.STUDENT if student is not None else AssigneeType.STAFF
    return TransportAssignment.objects.create(
        institution=institution,
        session=session,
        route=locked_route,
        stop=stop,
        assignee_type=assignee_type,
        student=student,
        staff=staff,
        transport_fee_link=transport_fee_link,
        start_date=start_date or timezone.localdate(),
        end_date=end_date,
        is_active=True,
    )


@transaction.atomic
def start_trip(
    *,
    institution: Any,
    route: Route,
    driver: Driver | None = None,
    vehicle: Vehicle | None = None,
    direction: str = TripDirection.MORNING_PICKUP,
    notes: str = "",
    actor: Any = None,
    enforce_driver_ownership: bool = False,
) -> TripLog:
    """Start a new TripLog for a route, checking vehicle concurrency and driver ownership."""
    if route.institution_id != institution.id or route.is_deleted:
        raise ValidationError("Route not found in this institution.")

    effective_driver = driver or route.driver
    effective_vehicle = vehicle or route.vehicle
    if effective_driver is None or effective_vehicle is None:
        raise ValidationError("Both driver and vehicle are required to start a trip.")
    if (
        effective_driver.institution_id != institution.id
        or effective_vehicle.institution_id != institution.id
    ):
        raise ValidationError("Driver or vehicle belongs to another institution.")

    if enforce_driver_ownership:
        if effective_driver.staff.user_id != getattr(actor, "id", None):
            raise DjangoPermissionDenied("Drivers may only start trips assigned to themselves.")

    Vehicle.objects.select_for_update().get(id=effective_vehicle.id)
    if TripLog.objects.filter(
        institution=institution,
        vehicle=effective_vehicle,
        status=TripStatus.IN_PROGRESS,
    ).exists():
        raise ValidationError("Vehicle already has an in-progress trip.")

    return TripLog.objects.create(
        institution=institution,
        route=route,
        vehicle=effective_vehicle,
        driver=effective_driver,
        direction=direction,
        trip_date=timezone.localdate(),
        started_at=timezone.now(),
        status=TripStatus.IN_PROGRESS,
        notes=notes,
    )


@transaction.atomic
def end_trip(
    *,
    institution: Any,
    trip: TripLog,
    notes: str = "",
    actor: Any = None,
    enforce_driver_ownership: bool = False,
) -> TripLog:
    """Complete an IN_PROGRESS TripLog."""
    locked = (
        TripLog.objects.select_for_update()
        .select_related("driver", "driver__staff")
        .get(id=trip.id, institution=institution)
    )
    if enforce_driver_ownership:
        if locked.driver.staff.user_id != getattr(actor, "id", None):
            raise DjangoPermissionDenied("Drivers may only end their own trips.")
    if locked.status != TripStatus.IN_PROGRESS:
        raise ValidationError(f"Only in-progress trips can be ended (current: {locked.status}).")

    locked.status = TripStatus.COMPLETED
    locked.ended_at = timezone.now()
    if notes:
        locked.notes = f"{locked.notes}\n{notes}".strip() if locked.notes else notes
    locked.save(update_fields=["status", "ended_at", "notes", "updated_at"])
    return locked


@transaction.atomic
def record_boarding_event(
    *,
    institution: Any,
    trip: TripLog,
    student: Any,
    event_type: str,
    stop: RouteStop | None = None,
    method: str = BoardingMethod.QR,
    event_ts: datetime | None = None,
    idempotency_key: str = "",
    actor: Any = None,
) -> tuple[BoardingEvent, bool]:
    """Record an idempotent student boarding/dropping scan event and notify guardians."""
    if trip.institution_id != institution.id:
        raise ValidationError("Trip belongs to another institution.")
    if student.institution_id != institution.id:
        raise ValidationError("Student belongs to another institution.")
    if stop is not None and stop.route_id != trip.route_id:
        raise ValidationError("Stop does not belong to the trip's route.")

    if idempotency_key:
        existing_by_key = BoardingEvent.objects.filter(
            institution=institution,
            idempotency_key=idempotency_key,
        ).first()
        if existing_by_key is not None:
            return existing_by_key, False

    existing = BoardingEvent.objects.filter(
        institution=institution,
        trip=trip,
        student=student,
        event_type=event_type,
    ).first()
    if existing is not None:
        return existing, False

    event = BoardingEvent.objects.create(
        institution=institution,
        trip=trip,
        student=student,
        stop=stop,
        event_type=event_type,
        event_ts=event_ts or timezone.now(),
        method=method,
        idempotency_key=idempotency_key,
        recorded_by=actor if actor and getattr(actor, "is_authenticated", False) else None,
    )
    _notify_guardians_boarding(event)
    return event, True


def ingest_gps_ping(
    *,
    gps_device_id: str,
    raw_token: str,
    latitude: Decimal,
    longitude: Decimal,
    speed_kmh: Decimal = Decimal("0.00"),
    recorded_at: datetime | None = None,
) -> LiveLocation:
    """Authenticate a GPS device token and store a LiveLocation ping."""
    if not gps_device_id or not raw_token:
        raise DjangoPermissionDenied("Missing GPS device credentials.")

    vehicle = (
        Vehicle.objects.select_related("institution")
        .filter(gps_device_id=gps_device_id, is_deleted=False)
        .first()
    )
    if vehicle is None or not vehicle.gps_token_hash:
        raise DjangoPermissionDenied("Invalid GPS device credentials.")

    candidate_hash = hash_gps_token(raw_token)
    if not hmac.compare_digest(candidate_hash, vehicle.gps_token_hash):
        raise DjangoPermissionDenied("Invalid GPS device credentials.")

    active_trip = TripLog.objects.filter(
        institution=vehicle.institution,
        vehicle=vehicle,
        status=TripStatus.IN_PROGRESS,
    ).first()

    return LiveLocation.objects.create(
        institution=vehicle.institution,
        vehicle=vehicle,
        trip=active_trip,
        latitude=latitude,
        longitude=longitude,
        speed_kmh=speed_kmh,
        recorded_at=recorded_at or timezone.now(),
    )
