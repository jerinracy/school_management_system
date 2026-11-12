"""Central notification dispatcher and template rendering service."""

import datetime
import logging
import re
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.communications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    NotificationStatus,
    NotificationTemplate,
)
from apps.communications.services.push_service import send_push_notification
from apps.communications.services.sms_service import send_single_sms

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)
DHAKA_TZ = ZoneInfo("Asia/Dhaka")


def render_template(
    template: NotificationTemplate,
    context: dict[str, Any],
    lang: str = "bn",
) -> tuple[str, str]:
    """Substitute placeholder tags (e.g. {{student_name}} or {student_name}) in template."""
    raw_body = template.body_template_bn if lang == "bn" else template.body_template_en
    raw_subject = template.subject_template or template.name

    def replacer(text: str) -> str:
        for key, value in context.items():
            pattern = re.compile(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}|\{" + re.escape(key) + r"\}"
            )
            text = pattern.sub(str(value), text)
        return text

    return replacer(raw_subject), replacer(raw_body)


def is_in_quiet_hours(
    pref: NotificationPreference, check_time: datetime.datetime | None = None
) -> bool:
    """Determine whether the current Asia/Dhaka time falls within the user's quiet hours."""
    if not pref.quiet_hours_enabled or not pref.quiet_hours_start or not pref.quiet_hours_end:
        return False

    now_dhaka = (check_time or timezone.now()).astimezone(DHAKA_TZ).time()
    start = pref.quiet_hours_start
    end = pref.quiet_hours_end

    if start <= end:
        # e.g., 01:00 to 06:00
        return start <= now_dhaka <= end
    else:
        # e.g., 22:00 to 07:00 (spans midnight)
        return now_dhaka >= start or now_dhaka <= end


def dispatch_event_notification(
    institution: "Institution",
    event_type: str,
    recipient_users: list["User"],
    context: dict[str, Any],
    channels: list[str] | None = None,
    force_override_quiet_hours: bool = False,
    source_module: str = "communications",
    reference_id: Any = None,
) -> list[NotificationDelivery]:
    """Render and dispatch notifications for an event across authorized channels."""
    event = NotificationEvent.objects.create(
        institution=institution,
        event_type=event_type,
        source_module=source_module,
        reference_id=reference_id,
        payload=context,
    )

    template = NotificationTemplate.objects.filter(
        institution=institution,
        code=event_type,
        is_active=True,
    ).first()

    deliveries: list[NotificationDelivery] = []

    for user in recipient_users:
        pref, _ = NotificationPreference.objects.get_or_create(
            institution=institution,
            user=user,
            defaults={"language_preference": "bn"},
        )

        lang = pref.language_preference or "bn"

        # Check quiet hours (unless emergency/forced override)
        if not force_override_quiet_hours and is_in_quiet_hours(pref):
            logger.info("Suppressed notification for user %s during quiet hours", user.phone)
            # Create a queued delivery noting quiet hours suppression
            deliv = NotificationDelivery.objects.create(
                institution=institution,
                event=event,
                recipient_user=user,
                recipient_phone=getattr(user, "phone", ""),
                channel=NotificationChannel.IN_APP,
                title="Notification Deferred (Quiet Hours)",
                content="Notification suppressed due to quiet hours preference.",
                language=lang,
                status=NotificationStatus.QUEUED,
                error_message="Quiet hours active in Asia/Dhaka",
            )
            deliveries.append(deliv)
            continue

        # Render message text
        if template:
            title, body = render_template(template, context, lang=lang)
        else:
            title = context.get("title") or event_type.replace("_", " ").title()
            body = context.get("message") or f"Event {event_type} occurred."

        # Determine target channels
        target_channels = channels or [
            NotificationChannel.SMS,
            NotificationChannel.PUSH,
            NotificationChannel.IN_APP,
        ]

        # 1. SMS Channel
        user_phone = getattr(user, "phone", None)
        if NotificationChannel.SMS in target_channels and pref.enable_sms and user_phone:
            sms_deliv = send_single_sms(
                institution=institution,
                recipient_phone=str(user_phone),
                message=body,
                recipient_user=user,
                event=event,
                language=lang,
            )
            deliveries.append(sms_deliv)

        # 2. Push Channel
        if NotificationChannel.PUSH in target_channels and pref.enable_push:
            push_delivs = send_push_notification(
                institution=institution,
                user=user,
                title=title,
                body=body,
                data={"event_type": event_type, "reference_id": str(reference_id or "")},
                event=event,
                language=lang,
            )
            deliveries.extend(push_delivs)

        # 3. In-App Channel
        if NotificationChannel.IN_APP in target_channels and pref.enable_in_app:
            in_app_deliv = NotificationDelivery.objects.create(
                institution=institution,
                event=event,
                recipient_user=user,
                recipient_phone=getattr(user, "phone", ""),
                channel=NotificationChannel.IN_APP,
                title=title,
                content=body,
                language=lang,
                status=NotificationStatus.DELIVERED,
                delivered_at=timezone.now(),
            )
            deliveries.append(in_app_deliv)

    return deliveries
