"""Nagad payment gateway adapter."""

import os
from typing import Any

from apps.fees.gateways.base import PaymentGatewayAdapter
from apps.fees.models import Payment


class NagadAdapter(PaymentGatewayAdapter):
    gateway_name = "nagad"

    def __init__(self) -> None:
        self.merchant_id = os.getenv("NAGAD_MERCHANT_ID", "mock_nagad_merchant")
        self.is_sandbox = os.getenv("NAGAD_IS_SANDBOX", "true").lower() == "true"
        self.base_url = (
            "http://sandbox.mynagad.com:10080/remote-payment-gateway-1.0/api/dfs"
            if self.is_sandbox
            else "https://api.mynagad.com/api/dfs"
        )

    def create_session(
        self,
        payment: Payment,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        order_id = f"NAGAD_{payment.id}"
        # Sandbox simulated session
        return {
            "redirect_url": f"https://sandbox.mynagad.com/pay?order_id={order_id}&amount={payment.amount:.2f}",
            "session_id": order_id,
            "raw_response": {"status": "Success", "order_id": order_id},
        }

    def verify(
        self,
        payment: Payment,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        status_param = params.get("status", "").upper()
        payment_ref = (
            params.get("payment_ref_id") or params.get("order_id") or f"NAGAD_REF_{payment.id}"
        )

        if status_param in ["SUCCESS", "SUCCESSFUL"] or params.get("issuer_payment_ref"):
            return {
                "is_valid": True,
                "transaction_id": params.get("issuer_payment_ref", payment_ref),
                "raw_data": params,
            }

        return {
            "is_valid": False,
            "transaction_id": "",
            "raw_data": params,
            "error_message": "Nagad payment verification failed.",
        }

    def validate_ipn(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> bool:
        return payload.get("status", "").upper() == "SUCCESS"
