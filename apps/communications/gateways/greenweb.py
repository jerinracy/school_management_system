"""Greenweb Bangladesh SMS Gateway Adapter."""

import logging
from decimal import Decimal, InvalidOperation

import requests

from .base import SMSGatewayAdapter, SMSGatewayResponse, calculate_sms_segments

logger = logging.getLogger(__name__)

DEFAULT_GREENWEB_ENDPOINT = "http://api.greenweb.com.bd/api.php"
DEFAULT_GREENWEB_BALANCE_ENDPOINT = "http://api.greenweb.com.bd/grebalsms.php"


class GreenwebAdapter(SMSGatewayAdapter):
    """Adapter for Greenweb Bangladesh SMS Gateway."""

    def _get_endpoint(self) -> str:
        return (
            self.config.endpoint_url.strip()
            if self.config.endpoint_url
            else DEFAULT_GREENWEB_ENDPOINT
        )

    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        segments, _, _ = calculate_sms_segments(message)
        cost = self.config.rate_per_segment * segments
        formatted_recipient = recipient.lstrip("+")

        params = {
            "token": self.config.api_key,
            "to": formatted_recipient,
            "message": message,
        }

        try:
            resp = requests.post(self._get_endpoint(), data=params, timeout=10)
            text_response = resp.text.strip()
        except Exception as exc:
            logger.error("Greenweb SMS delivery failed: %s", exc)
            return SMSGatewayResponse(
                success=False,
                segment_count=segments,
                cost=cost,
                error=str(exc),
                raw_response={"error": str(exc)},
            )

        if "Ok" in text_response or "SMS Sent" in text_response:
            return SMSGatewayResponse(
                success=True,
                provider_message_id=text_response,
                segment_count=segments,
                cost=cost,
                raw_response={"response": text_response},
            )

        return SMSGatewayResponse(
            success=False,
            segment_count=segments,
            cost=cost,
            error=text_response or f"HTTP {resp.status_code}",
            raw_response={"response": text_response},
        )

    def check_balance(self) -> Decimal:
        url = (
            str(self.config.meta_config.get("balance_url"))
            if self.config.meta_config and self.config.meta_config.get("balance_url")
            else DEFAULT_GREENWEB_BALANCE_ENDPOINT
        )
        try:
            resp = requests.get(url, params={"token": self.config.api_key}, timeout=10)
            text = resp.text.strip()
            # Greenweb returns balance as text number, or "Remaining SMS : 123"
            parts = [w for w in text.split() if w.replace(".", "", 1).isdigit()]
            if parts:
                return Decimal(parts[0])
            return self.config.balance
        except (requests.RequestException, InvalidOperation, ValueError) as exc:
            logger.error("Greenweb balance check failed: %s", exc)
            return self.config.balance
