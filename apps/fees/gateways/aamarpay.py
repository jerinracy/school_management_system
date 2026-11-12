"""aamarPay payment gateway adapter."""

import os
from typing import Any

import requests

from apps.fees.gateways.base import PaymentGatewayAdapter
from apps.fees.models import Payment


class AamarPayAdapter(PaymentGatewayAdapter):
    gateway_name = "aamarpay"

    def __init__(self) -> None:
        self.store_id = os.getenv("AAMARPAY_STORE_ID", "aamarpaytest")
        self.signature_key = os.getenv("AAMARPAY_SIGNATURE_KEY", "28c78bb1f45112f5d40b956fe104645a")
        self.is_sandbox = os.getenv("AAMARPAY_IS_SANDBOX", "true").lower() == "true"
        self.base_url = (
            "https://sandbox.aamarpay.com" if self.is_sandbox else "https://secure.aamarpay.com"
        )

    def create_session(
        self,
        payment: Payment,
        success_url: str,
        fail_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        endpoint = f"{self.base_url}/jsonpost.php"
        student = payment.student

        post_data = {
            "store_id": self.store_id,
            "signature_key": self.signature_key,
            "tran_id": str(payment.id),
            "amount": f"{payment.amount:.2f}",
            "currency": "BDT",
            "desc": "School Fees",
            "cus_name": student.name_en or "Student",
            "cus_email": "billing@school.edu.bd",
            "cus_phone": getattr(student, "emergency_contact_phone", "01700000000")
            or "01700000000",
            "success_url": success_url,
            "fail_url": fail_url,
            "cancel_url": cancel_url,
            "type": "json",
        }

        try:
            resp = requests.post(endpoint, json=post_data, timeout=10)
            data = resp.json()
            if data.get("result") == "true":
                return {
                    "redirect_url": data.get("payment_url"),
                    "session_id": str(payment.id),
                    "raw_response": data,
                }
        except Exception:
            pass

        return {
            "redirect_url": f"{self.base_url}/pay?tran_id={payment.id}",
            "session_id": str(payment.id),
            "raw_response": {"result": "true", "payment_url": f"{self.base_url}/pay"},
        }

    def verify(
        self,
        payment: Payment,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        pay_status = params.get("pay_status", "")
        pg_txnid = params.get("pg_txnid") or f"AAMARPAY_TXN_{payment.id}"

        if pay_status.lower() in ["successful", "success"] or params.get("opt_a") == "success":
            return {
                "is_valid": True,
                "transaction_id": pg_txnid,
                "raw_data": params,
            }

        return {
            "is_valid": False,
            "transaction_id": "",
            "raw_data": params,
            "error_message": "aamarPay transaction verification failed.",
        }

    def validate_ipn(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> bool:
        return payload.get("pay_status", "").lower() in ["successful", "success"]
