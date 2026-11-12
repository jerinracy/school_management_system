"""Factory for SMS Gateway adapters."""

from apps.communications.models import SMSGatewayConfig, SMSGatewayProvider

from .base import SMSGatewayAdapter
from .console import ConsoleMockAdapter
from .greenweb import GreenwebAdapter
from .onnorokom import OnnorokomAdapter, TeletalkAdapter
from .ssl_wireless import SSLWirelessAdapter


def get_gateway_adapter(config: SMSGatewayConfig) -> SMSGatewayAdapter:
    """Return an instantiated adapter for the specified SMSGatewayConfig."""
    provider = config.provider
    if provider == SMSGatewayProvider.SSL_WIRELESS:
        return SSLWirelessAdapter(config)
    elif provider == SMSGatewayProvider.GREENWEB:
        return GreenwebAdapter(config)
    elif provider == SMSGatewayProvider.ONNOROKOM:
        return OnnorokomAdapter(config)
    elif provider == SMSGatewayProvider.TELETALK:
        return TeletalkAdapter(config)
    else:
        return ConsoleMockAdapter(config)
