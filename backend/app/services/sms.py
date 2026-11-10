"""
Township One — SMS Delivery Provider Abstraction and Security Gate.

Defines the SMS delivery adapter interface.
- In development/testing: MockSMSProvider logs/simulates delivery.
- In production: ProductionSMSProvider dispatches to external SMS gateway (Twilio, Gupshup, AWS SNS).
- Strict fail-closed policy: If real provider credentials (SMS_PROVIDER_API_KEY) are absent
  in production, raises an explicit configuration error to block insecure unverified logins.
"""

import logging
from abc import ABC, abstractmethod

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class BaseSMSProvider(ABC):
    """Abstract SMS provider interface for transactional OTP delivery."""

    @abstractmethod
    def send_otp(self, phone: str, otp: str) -> bool:
        """Sends OTP to the specified mobile phone number. Returns True on successful dispatch."""
        pass


class MockSMSProvider(BaseSMSProvider):
    """Simulated provider for local development, staging, and automated test suites."""

    def send_otp(self, phone: str, otp: str) -> bool:
        logger.info(f"[DEV/TEST MOCK SMS] Dispatched OTP {otp} to {phone}")
        return True


class ProductionSMSProvider(BaseSMSProvider):
    """Fail-closed placeholder until a real, configured SMS transport is implemented."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def send_otp(self, phone: str, otp: str) -> bool:
        # A configured key alone is not evidence that an HTTP gateway integration exists.
        logger.error("Production OTP delivery is unavailable: no SMS transport adapter is configured.")
        return False


def get_sms_provider() -> BaseSMSProvider:
    """Factory resolving the appropriate SMS provider based on APP_ENV."""
    if settings.APP_ENV.lower() == "production":
        if not settings.SMS_PROVIDER_API_KEY or len(settings.SMS_PROVIDER_API_KEY.strip()) < 8:
            raise RuntimeError(
                "Production SMS provider requires a valid SMS_PROVIDER_API_KEY. "
                "OTP delivery remains unavailable until a real gateway adapter is configured."
            )
        return ProductionSMSProvider(settings.SMS_PROVIDER_API_KEY)
    return MockSMSProvider()
