"""Console / Mock SMS Gateway Adapter for local dev and automated tests."""

import logging
import uuid
from decimal import Decimal

from .base import SMSGatewayAdapter, SMSGatewayResponse, calculate_sms_segments

logger = logging.getLogger(__name__)


class ConsoleMockAdapter(SMSGatewayAdapter):
    """Deterministic in-memory and stdout SMS adapter for local testing."""

    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        segments, is_unicode, char_len = calculate_sms_segments(message)
        cost = self.config.rate_per_segment * segments
        message_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

        logger.info(
            "[MOCK SMS] Recipient: %s | Segments: %d (Unicode: %s, Len: %d) | Cost: ৳%s | Msg: %s",
            recipient,
            segments,
            is_unicode,
            char_len,
            cost,
            message,
        )

        return SMSGatewayResponse(
            success=True,
            provider_message_id=message_id,
            segment_count=segments,
            cost=cost,
            raw_response={"mock": True, "recipient": recipient, "segments": segments},
        )

    def check_balance(self) -> Decimal:
        logger.info(
            "[MOCK SMS] Checking balance for %s: %s BDT", self.config.name, self.config.balance
        )
        return self.config.balance
