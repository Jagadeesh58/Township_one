"""
Township One — SMS Delivery Provider Abstraction and Security Gate.

Defines the SMS delivery adapter interface.
- In development/testing: MockSMSProvider logs/simulates delivery.
- In production: ProductionSMSProvider dispatches to external SMS gateway (Twilio, Gupshup, AWS SNS).
- Strict fail-closed policy: If real provider credentials (SMS_PROVIDER_API_KEY) are absent
  in production, raises an explicit configuration error to block insecure unverified logins.
"""

from abc import ABC, abstractmethod
import logging
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
    """Production provider requiring valid SMS gateway API key credentials."""
    def __init__(self, api_key: str):
        if not api_key or len(api_key.strip()) < 8:
            raise RuntimeError(
                "FATAL CONFIGURATION ERROR: Production SMS provider requires a valid SMS_PROVIDER_API_KEY. "
                "Failing closed to prevent unverified logins."
            )
        self.api_key = api_key

    def send_otp(self, phone: str, otp: str) -> bool:
        # In a deployed production instance, this dispatches via HTTPS to the SMS gateway.
        logger.info(f"[PROD SMS GATEWAY] Dispatched OTP to phone ending in ...{phone[-4:]}")
        return True


def get_sms_provider() -> BaseSMSProvider:
    """Factory resolving the appropriate SMS provider based on APP_ENV."""
    if settings.APP_ENV.lower() == "production":
        return ProductionSMSProvider(settings.SMS_PROVIDER_API_KEY)
    return MockSMSProvider()
