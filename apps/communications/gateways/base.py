"""Abstract base class and utilities for SMS gateways and segmentation."""

import abc
import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.communications.models import SMSGatewayConfig

# Basic GSM 7-bit alphabet characters
GSM_7BIT_CHARS = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`abcdefghijklmnopqrstuvwxyzäöñüà"
)


def is_unicode_text(text: str) -> bool:
    """Determine whether text contains characters requiring UCS-2 (Unicode) encoding.

    Returns True if any character falls outside the standard GSM-7 charset,
    including Bengali characters (Unicode range U+0980 to U+09FF).
    """
    for ch in text:
        if ch not in GSM_7BIT_CHARS:
            return True
    return False


def calculate_sms_segments(text: str) -> tuple[int, bool, int]:
    """Calculate the number of SMS segments, encoding type, and character length.

    Returns:
        tuple[int, bool, int]: (segment_count, is_unicode, char_length)

    Rules:
    - Unicode / UCS-2 (Bengali, emoji, non-GSM):
        * 1 segment: up to 70 characters
        * Multi-part: 67 characters per segment
    - Standard GSM 7-bit (English ASCII):
        * 1 segment: up to 160 characters
        * Multi-part: 153 characters per segment
    """
    if not text:
        return 1, False, 0

    char_length = len(text)
    is_unicode = is_unicode_text(text)

    if is_unicode:
        if char_length <= 70:
            segments = 1
        else:
            segments = math.ceil(char_length / 67)
    else:
        if char_length <= 160:
            segments = 1
        else:
            segments = math.ceil(char_length / 153)

    return max(1, segments), is_unicode, char_length


@dataclass
class SMSGatewayResponse:
    """Standardized response from an SMS gateway provider."""

    success: bool
    provider_message_id: str | None = None
    segment_count: int = 1
    cost: Decimal = Decimal("0.00")
    error: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class SMSGatewayAdapter(abc.ABC):
    """Abstract interface for all Bangladeshi SMS gateway integrations."""

    def __init__(self, config: "SMSGatewayConfig") -> None:
        self.config = config

    @abc.abstractmethod
    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        """Send an SMS to a single recipient phone number."""
        pass

    def send_bulk_sms(self, recipients: list[str], message: str) -> list[SMSGatewayResponse]:
        """Send an SMS to multiple recipients. Defaults to sequential single dispatch."""
        responses: list[SMSGatewayResponse] = []
        for recipient in recipients:
            responses.append(self.send_sms(recipient, message))
        return responses

    @abc.abstractmethod
    def check_balance(self) -> Decimal:
        """Query the remote SMS provider for the remaining account balance in BDT."""
        pass

    def parse_dlr(self, payload: dict[str, Any]) -> tuple[str, str]:
        """Parse provider delivery report (DLR) webhook payload.

        Returns (provider_message_id, normalized_status) where normalized_status is
        'delivered', 'failed', or 'sent'.
        """
        message_id = str(
            payload.get("msgid") or payload.get("message_id") or payload.get("sms_id") or ""
        )
        status_str = str(payload.get("status") or "").lower()
        if "deliv" in status_str or status_str in ("success", "ok", "1"):
            normalized_status = "delivered"
        elif "fail" in status_str or "reject" in status_str or "error" in status_str:
            normalized_status = "failed"
        else:
            normalized_status = "sent"
        return message_id, normalized_status
