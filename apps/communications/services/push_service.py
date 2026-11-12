"""Push notification service for Firebase Cloud Messaging (FCM)."""

import logging
import uuid
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.communications.models import (
    DeviceToken,
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
    NotificationStatus,
)

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)


class FCMMockClient:
    """Mock client for Firebase Cloud Messaging during local development and testing."""

    def send_to_token(
        self, token: str, title: str, body: str, data: dict[str, Any] | None = None
    ) -> tuple[bool, str | None, str | None]:
        if token.startswith("invalid_"):
            return False, None, "InvalidRegistration"
        message_id = f"projects/sms-fcm/messages/{uuid.uuid4().hex}"
        logger.info("[FCM PUSH] Token: %s... | Title: %s | Body: %s", token[:15], title, body)
        return True, message_id, None


_fcm_client = FCMMockClient()


def set_fcm_client(client: Any) -> None:
    """Override FCM client (e.g. in test suites)."""
    global _fcm_client
    _fcm_client = client


def send_push_notification(
    institution: "Institution",
    user: "User",
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    event: NotificationEvent | None = None,
    language: str = "bn",
) -> list[NotificationDelivery]:
    """Send a push notification to all active devices registered for a user."""
    tokens = DeviceToken.objects.filter(user=user, is_active=True)
    if not tokens.exists():
        logger.debug("No active device tokens found for user %s", user)
        # Create queued delivery for user notification history
        delivery = NotificationDelivery.objects.create(
            institution=institution,
            event=event,
            recipient_user=user,
            channel=NotificationChannel.PUSH,
            title=title,
            content=body,
            language=language,
            status=NotificationStatus.QUEUED,
            error_message="No registered FCM device tokens for user",
        )
        return [delivery]

    deliveries: list[NotificationDelivery] = []
    for device in tokens:
        success, msg_id, err = _fcm_client.send_to_token(
            token=device.token,
            title=title,
            body=body,
            data=data or {},
        )

        delivery = NotificationDelivery(
            institution=institution,
            event=event,
            recipient_user=user,
            channel=NotificationChannel.PUSH,
            title=title,
            content=body,
            language=language,
            provider_message_id=msg_id or "",
        )

        if success:
            delivery.status = NotificationStatus.SENT
            delivery.sent_at = timezone.now()
        else:
            delivery.status = NotificationStatus.FAILED
            delivery.error_message = err or "Push delivery failed"
            if err == "InvalidRegistration":
                device.is_active = False
                device.save(update_fields=["is_active"])

        delivery.save()
        deliveries.append(delivery)

    return deliveries
