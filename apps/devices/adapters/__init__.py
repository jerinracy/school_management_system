"""Hardware adapter exports for biometric devices."""

from apps.devices.adapters.base import AdapterRegistry, BaseDeviceAdapter
from apps.devices.adapters.generic_http import GenericHTTPAdapter
from apps.devices.adapters.simulator import FakeDeviceAdapter
from apps.devices.adapters.stubs import (
    EsslPullAdapter,
    HikvisionISAPIAdapter,
    SupremaBioStarAdapter,
)
from apps.devices.adapters.zkteco import ZKTecoPushAdapter

__all__ = [
    "AdapterRegistry",
    "BaseDeviceAdapter",
    "EsslPullAdapter",
    "FakeDeviceAdapter",
    "GenericHTTPAdapter",
    "HikvisionISAPIAdapter",
    "SupremaBioStarAdapter",
    "ZKTecoPushAdapter",
]
