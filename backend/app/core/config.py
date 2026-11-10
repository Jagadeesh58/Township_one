"""
Township One — Application Configuration and Environment Security Controls.

Centralizes configuration parameters, environment variables, database URLs,
session expiry policies, and fail-closed production safety guards.
"""

import json
import os
import secrets

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Township One"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = ""
    SIGNING_KEY: str = ""
    SIGNING_KEY_FILE: str = ""
    ALLOWED_ORIGINS: str | list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            clean = v.strip()
            if clean.startswith("["):
                try:
                    return json.loads(clean)
                except Exception:
                    pass
            return [x.strip() for x in clean.split(",") if x.strip()]
        return v

    # Database URLs (PostgreSQL standard per architecture; SQLite fast-test local fallback)
    DATABASE_URL: str = "postgresql+psycopg://township:township_dev_password@localhost:5432/township_one"
    TEST_DATABASE_URL: str = "postgresql+psycopg://township:township_dev_password@localhost:5432/township_one_test"

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

    # Storage & Attachments. Local is for development; hosted demo uses authenticated Cloudinary assets.
    STORAGE_BACKEND: str = "local"
    STORAGE_DIR: str = os.path.join(os.getcwd(), "private_storage")
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    R2_ACCOUNT_ID: str = ""
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""
    RETENTION_JOB_TOKEN: str = ""

    # AI Classification & Emergency Service
    GROQ_API_KEY: str = ""
    GROQ_MODEL_ID: str = "openai/gpt-oss-20b"
    GROQ_TIMEOUT_SECONDS: float = 5.0

    # Demo SLA Timers (Hours per urgency)
    DEMO_SLA_HOURS: dict = {"CRITICAL": 1, "HIGH": 4, "MEDIUM": 24, "LOW": 48}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context):
        if not self.SECRET_KEY:
            if self.APP_ENV.lower() in ["development", "test", "demo"]:
                object.__setattr__(self, "SECRET_KEY", secrets.token_urlsafe(32))
            else:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: SECRET_KEY environment variable is required outside development. "
                    "Please configure a strong, random 32+ character SECRET_KEY."
                )

    def validate_production_guards(self):
        """
        Fail-closed security guards for the production and hosted-demo profiles.

        Production requires a real SMS transport. The public challenge demo uses
        fixed OTP only, but its shared database, signing key, object storage and
        scheduled-job credential must still be persistent and explicitly set.
        """
        if self.APP_ENV.lower() == "demo" and self.STORAGE_BACKEND.lower() in {"cloudinary", "cloudflare_r2"}:
            required_hosted_values = {
                "DATABASE_URL": self.DATABASE_URL,
                "SECRET_KEY": self.SECRET_KEY,
                "SIGNING_KEY": self.SIGNING_KEY,
                "RETENTION_JOB_TOKEN": self.RETENTION_JOB_TOKEN,
            }
            if self.STORAGE_BACKEND.lower() == "cloudinary":
                required_hosted_values.update(
                    {
                        "CLOUDINARY_CLOUD_NAME": self.CLOUDINARY_CLOUD_NAME,
                        "CLOUDINARY_API_KEY": self.CLOUDINARY_API_KEY,
                        "CLOUDINARY_API_SECRET": self.CLOUDINARY_API_SECRET,
                    }
                )
            else:
                required_hosted_values.update(
                    {
                        "R2_ACCOUNT_ID": self.R2_ACCOUNT_ID,
                        "R2_ACCESS_KEY_ID": self.R2_ACCESS_KEY_ID,
                        "R2_SECRET_ACCESS_KEY": self.R2_SECRET_ACCESS_KEY,
                        "R2_BUCKET": self.R2_BUCKET,
                    }
                )
            missing = [name for name, value in required_hosted_values.items() if not str(value).strip()]
            explicitly_configured = {"DATABASE_URL", "SECRET_KEY", "SIGNING_KEY", "RETENTION_JOB_TOKEN"}
            missing_explicit = sorted(explicitly_configured - self.model_fields_set)
            if missing or missing_explicit:
                raise RuntimeError(
                    "FATAL HOSTED DEMO CONFIGURATION: Set the required persistent secrets and storage/database "
                    f"values. Missing values: {sorted(missing)}; not explicitly configured: {missing_explicit}."
                )
            if not self.DATABASE_URL.startswith(("postgresql://", "postgresql+")):
                raise RuntimeError("FATAL HOSTED DEMO CONFIGURATION: DATABASE_URL must use PostgreSQL.")
            if len(self.SECRET_KEY) < 32 or len(self.RETENTION_JOB_TOKEN) < 32:
                raise RuntimeError(
                    "FATAL HOSTED DEMO CONFIGURATION: SECRET_KEY and RETENTION_JOB_TOKEN must be 32+ characters."
                )

        if self.APP_ENV.lower() == "production":
            insecure_markers = [
                "super-secret",
                "change-in-production",
                "example",
                "placeholder",
                "secret-key",
                "default",
                "password",
                "123456",
            ]
            key_lower = self.SECRET_KEY.lower()
            if (
                any(marker in key_lower for marker in insecure_markers)
                or len(self.SECRET_KEY) < 32
                or len(set(self.SECRET_KEY)) < 8
            ):
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Production deployment cannot use a default, placeholder, "
                    "or weak SECRET_KEY. Please configure a strong, random 32+ character SECRET_KEY with high entropy."
                )

            if self.DEBUG:
                raise RuntimeError("FATAL SECURITY VIOLATION: DEBUG mode must be False in production.")

            if not self.SIGNING_KEY.strip() and not self.SIGNING_KEY_FILE.strip():
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: SIGNING_KEY or SIGNING_KEY_FILE is required in production."
                )

            if not self.SMS_PROVIDER_API_KEY or len(self.SMS_PROVIDER_API_KEY.strip()) < 8:
                raise RuntimeError(
                    "FATAL SECURITY VIOLATION: Production deployment requires a valid SMS_PROVIDER_API_KEY "
                    "for transactional OTP delivery. Failing closed."
                )


settings = Settings()
settings.validate_production_guards()
