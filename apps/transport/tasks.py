"""Celery background tasks for Transport Management."""

import logging
from datetime import timedelta
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.transport.models import Driver, DriverStatus, LiveLocation, Vehicle, VehicleStatus

logger = logging.getLogger(__name__)


@shared_task(acks_late=True)
def send_transport_expiry_alerts(days_ahead: int = 30) -> dict[str, int]:
    """Alert institution admins about upcoming or expired vehicle/driver compliance dates."""
    today = timezone.localdate()
    cutoff = today + timedelta(days=days_ahead)
    alerts_sent = 0

    def _notify_admins(institution: Any, event_type: str, context: dict[str, Any], ref: Any) -> int:
        try:
            from apps.communications.services.notification_service import (
                dispatch_event_notification,
            )

            admins = list(
                User.objects.filter(
                    institution=institution,
                    is_active=True,
                    user_type__in=[UserType.ADMIN, UserType.HEAD_TEACHER],
                )
            )
            if not admins:
                return 0
            dispatch_event_notification(
                institution=institution,
                event_type=event_type,
                recipient_users=admins,
                context=context,
                source_module="transport",
                reference_id=ref,
            )
            return len(admins)
        except Exception:
            logger.exception("Failed to send transport expiry alert")
            return 0

    vehicles = Vehicle.objects.select_related("institution").filter(
        is_deleted=False, status=VehicleStatus.ACTIVE
    )
    for vehicle in vehicles:
        expiring_fields: list[str] = []
        for field_name in (
            "fitness_expiry",
            "insurance_expiry",
            "tax_token_expiry",
            "route_permit_expiry",
        ):
            val = getattr(vehicle, field_name)
            if val is not None and val <= cutoff:
                expiring_fields.append(f"{field_name}:{val.isoformat()}")
        if expiring_fields:
            alerts_sent += _notify_admins(
                vehicle.institution,
                "transport_vehicle_expiry",
                {"registration_no": vehicle.registration_no, "expiries": expiring_fields},
                vehicle.id,
            )

    drivers = Driver.objects.select_related("institution", "staff").filter(
        is_deleted=False, status=DriverStatus.ACTIVE, license_expiry__lte=cutoff
    )
    for driver in drivers:
        alerts_sent += _notify_admins(
            driver.institution,
            "transport_driver_license_expiry",
            {
                "driver_name": driver.staff.full_name_en,
                "license_no": driver.license_no,
                "license_expiry": driver.license_expiry.isoformat(),
            },
            driver.id,
        )

    return {"alerts_sent": alerts_sent}


@shared_task(acks_late=True)
def purge_old_live_locations(retention_days: int | None = None) -> dict[str, int]:
    """Delete LiveLocation GPS pings older than configured retention window."""
    days = (
        retention_days
        if retention_days is not None
        else int(getattr(settings, "TRANSPORT_LOCATION_RETENTION_DAYS", 30))
    )
    cutoff = timezone.now() - timedelta(days=days)
    deleted_count, _ = LiveLocation.objects.filter(recorded_at__lt=cutoff).delete()
    return {"deleted": deleted_count}
