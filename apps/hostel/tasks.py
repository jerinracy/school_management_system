"""Celery background tasks for Hostel Management."""

import logging

from celery import shared_task
from django.utils import timezone

from apps.accounts.models import User, UserType
from apps.hostel.models import GatePass, GatePassStatus
from apps.hostel.services.hostel_service import _notify_guardians_gatepass

logger = logging.getLogger(__name__)


@shared_task(acks_late=True)
def send_hostel_curfew_alerts() -> dict[str, int]:
    """Flag overdue checked-out GatePasses past expected_return_at and alert wardens/guardians."""
    now = timezone.now()
    overdue_passes = list(
        GatePass.objects.select_related(
            "institution", "student", "hostel", "hostel__warden"
        ).filter(
            status=GatePassStatus.CHECKED_OUT,
            expected_return_at__lt=now,
            curfew_alert_sent=False,
        )
    )
    alerted = 0
    for gp in overdue_passes:
        gp.status = GatePassStatus.OVERDUE
        gp.curfew_alert_sent = True
        gp.save(update_fields=["status", "curfew_alert_sent", "updated_at"])
        _notify_guardians_gatepass(gate_pass=gp, event_type="hostel_curfew_overdue")

        try:
            from apps.communications.services.notification_service import (
                dispatch_event_notification,
            )

            recipients = list(
                User.objects.filter(
                    institution=gp.institution,
                    is_active=True,
                    user_type__in=[UserType.ADMIN, UserType.HEAD_TEACHER],
                )
            )
            if gp.hostel.warden and gp.hostel.warden.user_id and gp.hostel.warden.user:
                recipients.append(gp.hostel.warden.user)
            if recipients:
                dispatch_event_notification(
                    institution=gp.institution,
                    event_type="hostel_curfew_overdue",
                    recipient_users=recipients,
                    context={
                        "student_id": gp.student.student_id,
                        "student_name": gp.student.name_en,
                        "hostel": gp.hostel.name,
                        "expected_return_at": gp.expected_return_at.isoformat(),
                    },
                    source_module="hostel",
                    reference_id=gp.id,
                )
        except Exception:
            logger.exception("Failed to send hostel curfew alert to staff for %s", gp.id)
        alerted += 1

    return {"curfew_alerts": alerted}
