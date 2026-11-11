"""Pluggable SMS Service interface and console implementation."""

import abc
import logging

logger = logging.getLogger(__name__)


class BaseSMSService(abc.ABC):
    """Abstract interface for SMS delivery (Console, SSL Wireless, Onnorokom, etc.)."""

    @abc.abstractmethod
    def send_sms(self, phone: str, message: str) -> bool:
        """Send an SMS to a Bangladeshi mobile number."""
        pass


class ConsoleSMSService(BaseSMSService):
    """Dev and test SMS service that logs message content to stdout/logger."""

    def send_sms(self, phone: str, message: str) -> bool:
        logger.info("[CONSOLE SMS] Sent to %s: %s", phone, message)
        print(
            f"\n================ [CONSOLE SMS] ================\nRecipient: {phone}\nMessage: {message}\n===============================================\n"
        )
        return True


def get_sms_service() -> BaseSMSService:
    """Factory returning configured SMS backend."""
    return ConsoleSMSService()
