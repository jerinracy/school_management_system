"""Celery tasks for Events & Notice Board."""

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.accounts.models import User
from apps.communications.services.notification_service import dispatch_event_notification
from apps.events.models import Event, EventRSVP, RSVPStatus


@shared_task(name="events.send_upcoming_event_reminders")
def send_upcoming_event_reminders() -> dict[str, int]:
    """Send reminder notifications for published events starting within the next 24 hours."""
    now = timezone.now()
    window_end = now + timedelta(hours=24)

    upcoming_events = Event.objects.filter(
        is_deleted=False,
        is_published=True,
        start_datetime__gte=now,
        start_datetime__lte=window_end,
    ).select_related("institution")

    reminders_sent = 0
    for event in upcoming_events:
        rsvp_user_ids = list(
            EventRSVP.objects.filter(
                institution=event.institution,
                event=event,
                status__in=[RSVPStatus.GOING, RSVPStatus.INTERESTED],
            ).values_list("user_id", flat=True)
        )
        if not rsvp_user_ids:
            continue

        recipients = list(User.objects.filter(id__in=rsvp_user_ids, is_active=True))
        if not recipients:
            continue

        dispatch_event_notification(
            institution=event.institution,
            event_type="event_reminder",
            recipient_users=recipients,
            context={
                "event_title": event.title_en,
                "start_datetime": event.start_datetime.isoformat(),
                "venue": event.venue,
            },
            source_module="events",
            reference_id=event.id,
        )
        reminders_sent += len(recipients)

    return {"reminders_sent": reminders_sent}
