"""Virtual simulator adapter generating synthetic punch events for testing and demonstration."""

import json
from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.devices.adapters.base import AdapterRegistry, BaseDeviceAdapter
from apps.devices.models import DeviceType


@AdapterRegistry.register("simulator", "simulator")
@AdapterRegistry.register("virtual", "simulator")
class FakeDeviceAdapter(BaseDeviceAdapter):
    """Virtual hardware simulator producing realistic synthetic punch streams."""

    def authenticate_request(self, request: Any) -> bool:
        """Allow test requests or verify token if configured."""
        if not self.device.api_token:
            return True
        token = request.headers.get("X-Device-Token") or request.GET.get("token")
        return bool(token == self.device.api_token)

    def parse_push_payload(
        self,
        payload: Any,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Accept JSON or newline-delimited simulated punch strings."""
        if isinstance(payload, (bytes, str)):
            try:
                data = json.loads(payload)
                if isinstance(data, list):
                    items = data
                else:
                    items = data.get("punches", [data])
            except Exception:
                items = [{"pin": p.strip()} for p in str(payload).splitlines() if p.strip()]
        elif isinstance(payload, list):
            items = payload
        else:
            items = [payload]

        punches: list[dict[str, Any]] = []
        now = timezone.now()

        for item in items:
            pin = str(item.get("pin") or item.get("user_id") or "1001").strip()
            punch_time = item.get("time") or item.get("timestamp") or now
            if isinstance(punch_time, str):
                try:
                    punch_time = datetime.fromisoformat(punch_time)
                except ValueError:
                    punch_time = now
            if timezone.is_naive(punch_time):
                punch_time = timezone.make_aware(punch_time, timezone.get_current_timezone())

            verify = str(item.get("verify") or DeviceType.FINGERPRINT)
            state = str(item.get("state") or "0")
            raw_str = f"SIM:{pin}@{punch_time.isoformat()}"

            punches.append(
                {
                    "raw_user_id": pin,
                    "device_time": punch_time,
                    "verify_type": verify,
                    "punch_state": state,
                    "work_code": "",
                    "payload_hash": self.compute_payload_hash(raw_str),
                    "raw_line": raw_str,
                }
            )

        return punches
