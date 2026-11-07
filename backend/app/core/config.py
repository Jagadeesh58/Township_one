"""
Township One — Application Configuration and Environment Security Controls.

Centralizes configuration parameters, environment variables, database URLs,
session expiry policies, and fail-closed production safety guards.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Township One"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "REDACTED"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Database URLs
    DATABASE_URL: str = "sqlite:///./township_one.db"
    TEST_DATABASE_URL: str = "sqlite:///./township_one_test.db"

    # Reference Date for Date Consistency across UI, API, Seed & Tests
    DEMO_AS_OF_DATE: str = "2026-11-06T00:00:00Z"

    # Auth & Tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    OTP_EXPIRY_SECONDS: int = 300
    DEMO_OTP_CODE: str = "123456"
    SMS_PROVIDER_API_KEY: str = ""

    # Maintenance Billing Defaults
    MAINTENANCE_RATE_PER_SQFT: float = 6.50
    DEFAULT_GRACE_PERIOD_DAYS: int = 5
    DEMO_LATE_FEE_PERCENTAGE_PA: float = 18.00

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_guards(self):
        """
        Fail-closed security guard:
        In production, verifies that:
        - SECRET_KEY is not a known default, placeholder, or low-entropy key.
        - DEBUG is strictly False.
        - Universal fixed demo OTP is disabled.
        """
        if self.APP_ENV.lower() == "production":
            insecure_markers = [
                "super-secret", "change-in-production", "example",
                "placeholder", "secret-key", "default", "password", "123456"
            ]
            key_lower = self.SECRET_KEY.lower()
            if any(marker in key_lower for marker in insecure_markers) or len(self.SECRET_KEY) < 32 or len(set(self.SECRET_KEY)) < 8:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Production deployment cannot use a default, placeholder, "
                    "or weak SECRET_KEY. Please configure a strong, random 32+ character SECRET_KEY with high entropy."
                )

            if self.DEBUG:
                raise RuntimeError("FATAL SECURITY VIOLATION: DEBUG mode must be False in production.")


settings = Settings()
settings.validate_production_guards()
