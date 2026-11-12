"""Payment Gateway factory for resolving provider adapters."""

from apps.fees.gateways.aamarpay import AamarPayAdapter
from apps.fees.gateways.base import PaymentGatewayAdapter
from apps.fees.gateways.bkash import BKashAdapter
from apps.fees.gateways.nagad import NagadAdapter
from apps.fees.gateways.sslcommerz import SSLCommerzAdapter

_GATEWAY_REGISTRY: dict[str, type[PaymentGatewayAdapter]] = {
    "sslcommerz": SSLCommerzAdapter,
    "card": SSLCommerzAdapter,
    "bkash": BKashAdapter,
    "nagad": NagadAdapter,
    "aamarpay": AamarPayAdapter,
}


def get_gateway_adapter(gateway_name: str) -> PaymentGatewayAdapter:
    """Return an adapter instance for the specified gateway or payment method."""
    key = gateway_name.lower().strip()
    adapter_cls = _GATEWAY_REGISTRY.get(key)
    if not adapter_cls:
        # Default to SSLCommerz for unknown/general card methods
        return SSLCommerzAdapter()
    return adapter_cls()
