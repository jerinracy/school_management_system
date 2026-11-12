"""Abstract Base Class for Bangladeshi Payment Gateway Adapters."""

from abc import ABC, abstractmethod
from typing import Any

from apps.fees.models import Payment


class PaymentGatewayAdapter(ABC):
    """Unified interface for online payment gateways (SSLCommerz, bKash, Nagad, aamarPay)."""

    gateway_name: str

    @abstractmethod
    def create_session(
        self,
        payment: Payment,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Initiate payment session with the gateway and return session ID & redirect URL.

        Returns:
            dict containing at least:
                - "redirect_url": URL to send the payer's browser to.
                - "session_id": Internal or gateway order/session token.
        """
        raise NotImplementedError

    @abstractmethod
    def verify(
        self,
        payment: Payment,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform server-to-server transaction verification against the gateway.

        Returns:
            dict containing:
                - "is_valid": bool indicating payment authenticity.
                - "transaction_id": gateway confirmation ID/TrxID.
                - "raw_data": raw payload returned by the gateway.
                - "error_message": optional failure message.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_ipn(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> bool:
        """Validate Instant Payment Notification (IPN) / webhook signature."""
        raise NotImplementedError

    def validate_ipn_signature(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> bool:
        """Alias for validate_ipn."""
        return self.validate_ipn(payload, headers)
