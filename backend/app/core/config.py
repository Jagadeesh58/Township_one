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


settings = Settings()
