"""SMS dispatch and balance management service."""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.communications.gateways.factory import get_gateway_adapter
from apps.communications.models import (
    NotificationChannel,
    NotificationDelivery,
    NotificationEvent,
    NotificationStatus,
    SMSBalanceLog,
    SMSGatewayConfig,
    SMSGatewayProvider,
)
from apps.core.utils.phone import normalize_bd_phone

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.institutions.models import Institution

logger = logging.getLogger(__name__)


def get_default_sms_gateway(institution: "Institution") -> SMSGatewayConfig:
    """Retrieve the active default gateway for an institution, or create a mock console one."""
    gateway = (
        SMSGatewayConfig.objects.filter(
            institution=institution, is_active=True, is_default=True
        ).first()
        or SMSGatewayConfig.objects.filter(institution=institution, is_active=True).first()
    )
    if not gateway:
        gateway, _ = SMSGatewayConfig.objects.get_or_create(
            institution=institution,
            provider=SMSGatewayProvider.MOCK_CONSOLE,
            defaults={
                "name": "Default Console SMS",
                "sender_id": "SMS_TEST",
                "api_key": "mock_console_key",
                "is_active": True,
                "is_default": True,
                "balance": Decimal("500.00"),
                "rate_per_segment": Decimal("0.3500"),
            },
        )
    return gateway


def send_single_sms(
    institution: "Institution",
    recipient_phone: str,
    message: str,
    recipient_user: "User | None" = None,
    event: NotificationEvent | None = None,
    gateway_config: SMSGatewayConfig | None = None,
    language: str = "bn",
) -> NotificationDelivery:
    """Validate, normalize, and dispatch a single SMS, persisting the delivery record."""
    try:
        normalized_phone = normalize_bd_phone(recipient_phone)
    except ValueError as exc:
        logger.warning("Invalid phone number '%s' rejected: %s", recipient_phone, exc)
        return NotificationDelivery.objects.create(
            institution=institution,
            event=event,
            recipient_user=recipient_user,
            recipient_phone=recipient_phone,
            channel=NotificationChannel.SMS,
            content=message,
            language=language,
            status=NotificationStatus.FAILED,
            error_message=f"Phone validation failed: {exc}",
        )

    gateway = gateway_config or get_default_sms_gateway(institution)
    adapter = get_gateway_adapter(gateway)

    delivery = NotificationDelivery(
        institution=institution,
        event=event,
        recipient_user=recipient_user,
        recipient_phone=normalized_phone,
        channel=NotificationChannel.SMS,
        content=message,
        language=language,
        gateway_config=gateway,
        status=NotificationStatus.QUEUED,
    )

    try:
        resp = adapter.send_sms(normalized_phone, message)
        delivery.segment_count = resp.segment_count
        delivery.cost_bdt = resp.cost
        delivery.provider_message_id = resp.provider_message_id or ""

        if resp.success:
            delivery.status = NotificationStatus.SENT
            delivery.sent_at = timezone.now()
            # Deduct balance safely
            with transaction.atomic():
                gateway.refresh_from_db()
                new_bal = max(Decimal("0.00"), gateway.balance - resp.cost)
                delta = new_bal - gateway.balance
                gateway.balance = new_bal
                gateway.save(update_fields=["balance"])
                if delta != Decimal("0.00"):
                    SMSBalanceLog.objects.create(
                        institution=institution,
                        gateway=gateway,
                        previous_balance=gateway.balance - delta,
                        current_balance=gateway.balance,
                        delta=delta,
                        reason="deduction",
                        note=f"Deducted for SMS delivery to {normalized_phone} ({resp.segment_count} segments)",
                    )
        else:
            delivery.status = NotificationStatus.FAILED
            delivery.error_message = resp.error or "Unknown provider failure"

    except Exception as exc:
        logger.exception("Unexpected error during SMS dispatch: %s", exc)
        delivery.status = NotificationStatus.FAILED
        delivery.error_message = str(exc)

    delivery.save()
    return delivery


def check_and_update_balance(gateway_config: SMSGatewayConfig) -> Decimal:
    """Query remote provider for balance, log changes, and update DB."""
    adapter = get_gateway_adapter(gateway_config)
    new_balance = adapter.check_balance()

    with transaction.atomic():
        gateway_config.refresh_from_db()
        prev_balance = gateway_config.balance
        delta = new_balance - prev_balance

        gateway_config.balance = new_balance
        gateway_config.last_balance_check = timezone.now()
        gateway_config.save(update_fields=["balance", "last_balance_check"])

        if delta != Decimal("0.00"):
            SMSBalanceLog.objects.create(
                institution=gateway_config.institution,
                gateway=gateway_config,
                previous_balance=prev_balance,
                current_balance=new_balance,
                delta=delta,
                reason="check",
                note="Automatic or manual balance check sync",
            )

    return new_balance
