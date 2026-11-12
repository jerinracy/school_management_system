"""SSL Wireless Bangladesh SMS Gateway Adapter."""

import logging
import uuid
from decimal import Decimal, InvalidOperation

import requests

from .base import SMSGatewayAdapter, SMSGatewayResponse, calculate_sms_segments

logger = logging.getLogger(__name__)

DEFAULT_SSL_ENDPOINT = "https://smsplus.sslwireless.com/api/v3/send-sms"
DEFAULT_SSL_BALANCE_ENDPOINT = "https://smsplus.sslwireless.com/api/v3/balance"


class SSLWirelessAdapter(SMSGatewayAdapter):
    """Adapter for SSL Wireless SMS API v3 (REST JSON)."""

    def _get_send_endpoint(self) -> str:
        return (
            self.config.endpoint_url.strip() if self.config.endpoint_url else DEFAULT_SSL_ENDPOINT
        )

    def _get_balance_endpoint(self) -> str:
        if self.config.meta_config and self.config.meta_config.get("balance_url"):
            return str(self.config.meta_config["balance_url"])
        return DEFAULT_SSL_BALANCE_ENDPOINT

    def send_sms(self, recipient: str, message: str) -> SMSGatewayResponse:
        segments, is_unicode, _ = calculate_sms_segments(message)
        cost = self.config.rate_per_segment * segments
        csms_id = f"SMS-{uuid.uuid4().hex[:12]}"
        # Ensure recipient is 8801XXXXXXXXX (without leading '+')
        formatted_recipient = recipient.lstrip("+")

        payload = {
            "api_token": self.config.api_key,
            "sid": self.config.client_id or self.config.sender_id,
            "msisdn": formatted_recipient,
            "sms": message,
            "csms_id": csms_id,
        }

        try:
            resp = requests.post(
                self._get_send_endpoint(),
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            data = resp.json() if resp.content else {}
        except Exception as exc:
            logger.error("SSL Wireless SMS delivery failed: %s", exc)
            return SMSGatewayResponse(
                success=False,
                segment_count=segments,
                cost=cost,
                error=str(exc),
                raw_response={"error": str(exc)},
            )

        status_code = data.get("status_code")
        status = str(data.get("status", "")).upper()
        if status_code in (200, 201) or status == "SUCCESS":
            smsinfo = data.get("smsinfo", [{}])
            ref_id = smsinfo[0].get("reference_id") if smsinfo else csms_id
            return SMSGatewayResponse(
                success=True,
                provider_message_id=str(ref_id),
                segment_count=segments,
                cost=cost,
                raw_response=data,
            )

        error_msg = data.get("error_message") or data.get("message") or f"HTTP {resp.status_code}"
        return SMSGatewayResponse(
            success=False,
            segment_count=segments,
            cost=cost,
            error=str(error_msg),
            raw_response=data,
        )

    def check_balance(self) -> Decimal:
        payload = {
            "api_token": self.config.api_key,
            "sid": self.config.client_id or self.config.sender_id,
        }
        try:
            resp = requests.post(
                self._get_balance_endpoint(),
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            data = resp.json() if resp.content else {}
            balance_val = data.get("balance") or data.get("balance_bdt") or 0
            return Decimal(str(balance_val))
        except (requests.RequestException, InvalidOperation, ValueError) as exc:
            logger.error("SSL Wireless balance check failed: %s", exc)
            return self.config.balance
