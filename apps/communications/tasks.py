"""Celery background tasks for communications."""

import logging

from celery import shared_task
from django.utils import timezone

from apps.communications.models import (
    NotificationDelivery,
    NotificationStatus,
    SMSGatewayConfig,
)
from apps.communications.services.sms_service import check_and_update_balance, send_single_sms

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_batch_task(self, delivery_ids: list[str]) -> dict[str, int]:
    """Process queued notification deliveries asynchronously."""
    deliveries = NotificationDelivery.objects.filter(
        id__in=delivery_ids, status=NotificationStatus.QUEUED
    )
    processed = 0
    failed = 0

    for deliv in deliveries:
        try:
            if deliv.channel == "sms" and deliv.recipient_phone:
                send_single_sms(
                    institution=deliv.institution,
                    recipient_phone=deliv.recipient_phone,
                    message=deliv.content,
                    recipient_user=deliv.recipient_user,
                    event=deliv.event,
                    gateway_config=deliv.gateway_config,
                    language=deliv.language,
                )
                processed += 1
        except Exception as exc:
            logger.exception("Batch notification dispatch error for delivery %s: %s", deliv.id, exc)
            failed += 1

    return {"processed": processed, "failed": failed}


@shared_task
def sync_sms_balances_task() -> int:
    """Periodic task to refresh balances from all active SMS gateways."""
    gateways = SMSGatewayConfig.objects.filter(is_active=True)
    synced_count = 0
    for gw in gateways:
        try:
            check_and_update_balance(gw)
            synced_count += 1
        except Exception as exc:
            logger.warning("Failed to sync balance for gateway %s (%s): %s", gw.name, gw.id, exc)
    return synced_count


@shared_task
def cleanup_expired_notices_task() -> int:
    """Periodic task to auto-unpublish or flag expired notices."""
    from apps.communications.models import Notice

    now = timezone.now()
    updated = Notice.objects.filter(
        is_published=True,
        expiry_date__isnull=False,
        expiry_date__lt=now,
    ).update(is_published=False)
    return updated
