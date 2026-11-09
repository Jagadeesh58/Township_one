"""
Township One - Health and Foundation Verification Tests.

Responsibility:
- Verify application health check and database connectivity.
- Verify standardized error response format with request ID tracing.
- Verify Alembic dynamic URL selection and isolation from hard-coded defaults.
- Verify production configuration guards (rejecting default/weak secret keys and debug mode).
"""

import os

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings, settings
from backend.app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers


def test_api_prefix_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_404_error_format():
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "HTTP_404"
    assert "request_id" in body["error"]


def test_database_url_separation():
    """Verify demo database and test database are strictly decoupled."""
    assert settings.DATABASE_URL != settings.TEST_DATABASE_URL
    assert "test" in settings.TEST_DATABASE_URL.lower()


def test_production_guard_rejects_default_secret():
    """Verify production mode rejects default or insecure secret key."""
    prod_settings = Settings(APP_ENV="production", SECRET_KEY="placeholder-insecure-secret-key-32chars")
    with pytest.raises(RuntimeError) as exc_info:
        prod_settings.validate_production_guards()
    assert "FATAL SECURITY VIOLATION" in str(exc_info.value)


def test_production_guard_rejects_weak_secret_and_debug_true():
    """Verify production mode rejects short secrets and debug=True."""
    weak_settings = Settings(APP_ENV="production", SECRET_KEY="short-secret", DEBUG=False)
    with pytest.raises(RuntimeError):
        weak_settings.validate_production_guards()

    debug_settings = Settings(APP_ENV="production", SECRET_KEY="a" * 32, DEBUG=True)
    with pytest.raises(RuntimeError):
        debug_settings.validate_production_guards()


def test_alembic_url_resolution_dynamic():
    """Verify Alembic dynamic URL resolver obtains URL from environment and ignores default placeholder."""
    from migrations.env import get_effective_migration_url

    custom_url = "sqlite:///./temp_alembic_test.db"
    old_env = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = custom_url
        assert get_effective_migration_url() == custom_url
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)
