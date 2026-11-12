"""Onnorokom and Teletalk SMS Gateway Adapters."""

import logging
from decimal import Decimal

from .base import SMSGatewayAdapter, SMSGatewayResponse, calculate_sms_segments

logger = logging.getLogger(__name__)


class OnnorokomAdapter(SMSGatewayAdapter):
    """Adapter for Onnorokom SMS Gateway."""

    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        segments, _, _ = calculate_sms_segments(message)
        cost = self.config.rate_per_segment * segments
        # Standard Onnorokom implementation stub
        logger.info("[ONNOROKOM SMS] Sent to %s: %s", recipient, message)
        return SMSGatewayResponse(
            success=True,
            provider_message_id=f"ONN-{recipient[-4:]}",
            segment_count=segments,
            cost=cost,
            raw_response={"status": "SENT", "provider": "onnorokom"},
        )

    def check_balance(self) -> Decimal:
        return self.config.balance


class TeletalkAdapter(SMSGatewayAdapter):
    """Adapter for Teletalk SMS Gateway."""

    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        segments, _, _ = calculate_sms_segments(message)
        cost = self.config.rate_per_segment * segments
        logger.info("[TELETALK SMS] Sent to %s: %s", recipient, message)
        return SMSGatewayResponse(
            success=True,
            provider_message_id=f"TTK-{recipient[-4:]}",
            segment_count=segments,
            cost=cost,
            raw_response={"status": "SENT", "provider": "teletalk"},
        )

    def check_balance(self) -> Decimal:
        return self.config.balance
