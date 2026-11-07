"""
Day 1 · D1-S1 — Foundation and Environment: Application Configuration.

Responsibility:
- Centrally load, validate, and provide application settings from environment.
- Guard production environment: reject default insecure secret keys in production.
- Define isolated database URLs for demo (`DATABASE_URL`) and testing (`TEST_DATABASE_URL`).
- Provide consistent demo reference date (`DEMO_AS_OF_DATE`) across all modules.

Related documentation:
docs/day-1/D1-S1-foundation-and-environment.md
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
        """Fail-closed guard: ensure default development secret key is never used in production."""
        if self.APP_ENV.lower() == "production":
            if "super-secret" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Production deployment cannot use the default or insecure SECRET_KEY. "
                    "Please configure a strong, random 32+ character SECRET_KEY in production."
                )


settings = Settings()
settings.validate_production_guards()
