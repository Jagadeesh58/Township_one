from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app


def test_retention_endpoint_rejects_missing_or_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "RETENTION_JOB_TOKEN", "a-long-random-retention-token")
    client = TestClient(app)

    missing = client.post("/api/v1/ops/retention/visitor-photos")
    invalid = client.post(
        "/api/v1/ops/retention/visitor-photos",
        headers={"X-Retention-Job-Token": "wrong-token"},
    )

    assert missing.status_code == 403
    assert invalid.status_code == 403


def test_retention_endpoint_runs_only_after_token_validation(monkeypatch):
    monkeypatch.setattr(settings, "RETENTION_JOB_TOKEN", "a-long-random-retention-token")
    monkeypatch.setattr(
        "backend.app.api.operations.purge_visitor_photos",
        lambda: 4,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/ops/retention/visitor-photos",
        headers={"X-Retention-Job-Token": "a-long-random-retention-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"deleted_photos": 4, "retention_days": 90}
