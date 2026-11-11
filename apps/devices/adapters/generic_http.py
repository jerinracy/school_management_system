"""Generic HTTP JSON webhook adapter with HMAC-SHA256 signature verification."""

import hmac
import json
import logging
import secrets
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.devices.adapters.base import AdapterRegistry, BaseDeviceAdapter

logger = logging.getLogger(__name__)


@AdapterRegistry.register("generic", "generic_http")
class GenericHTTPAdapter(BaseDeviceAdapter):
    """Adapter for custom API gateways and third-party webhook push devices using HMAC-SHA256."""

    def authenticate_request(self, request: Any) -> bool:
        """Verify HMAC signature or Authorization Bearer token."""
        # 1. Bearer Token Auth
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if self.device.api_token and secrets.compare_digest(token, self.device.api_token):
                return True

        # 2. HMAC-SHA256 Signature Auth
        signature = request.headers.get("X-Signature") or request.headers.get("X-Hub-Signature-256")
        if signature and self.device.auth_secret:
            secret_bytes = self.device.auth_secret.encode("utf-8")
            body_bytes = request.body if hasattr(request, "body") else b""
            expected_sig = hmac.new(secret_bytes, body_bytes, "sha256").hexdigest()
            if secrets.compare_digest(signature.lower(), expected_sig.lower()):
                return True

        # Fallback if no secret/token configured
        return not bool(self.device.api_token or self.device.auth_secret)

    def _normalize_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        raw_user_id = str(item.get("user_id") or item.get("pin") or "").strip()
        time_str = str(item.get("timestamp") or item.get("time") or "").strip()
        if not raw_user_id or not time_str:
            return None

        dt = parse_datetime(time_str)
        if not dt:
            return None

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        verify_type = str(item.get("verify_type") or item.get("method") or self.device.device_type)
        punch_state = str(item.get("punch_state") or item.get("state") or "0")
        work_code = str(item.get("work_code") or "")
        raw_json_str = json.dumps(item, sort_keys=True)
        payload_hash = self.compute_payload_hash(raw_json_str)

        return {
            "raw_user_id": raw_user_id,
            "device_time": dt,
            "verify_type": verify_type,
            "punch_state": punch_state,
            "work_code": work_code,
            "payload_hash": payload_hash,
            "raw_line": raw_json_str,
        }

    def parse_push_payload(
        self,
        payload: Any,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Parse structured JSON push payload into normalized punch records."""
        if isinstance(payload, (bytes, str)):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON payload received in GenericHTTPAdapter")
                return []
        elif isinstance(payload, dict):
            data = payload
        elif isinstance(payload, list):
            data = {"punches": payload}
        else:
            return []

        punches_raw = data.get("punches") if isinstance(data, dict) else data
        if not isinstance(punches_raw, list):
            punches_raw = [data]

        normalized: list[dict[str, Any]] = []
        for item in punches_raw:
            if isinstance(item, dict):
                punch = self._normalize_item(item)
                if punch:
                    normalized.append(punch)

        return normalized
