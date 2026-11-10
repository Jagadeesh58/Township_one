import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app


def test_root_and_client_routes_serve_the_built_frontend(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Township One</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('township')", encoding="utf-8")
    monkeypatch.setattr("backend.app.main.FRONTEND_DIST", dist)
    client = TestClient(app)

    root = client.get("/")
    client_route = client.get("/resident/complaints")
    asset = client.get("/assets/app.js")

    assert root.status_code == 200
    assert "Township One" in root.text
    assert client_route.status_code == 200
    assert "Township One" in client_route.text
    assert asset.status_code == 200
    assert "console.log" in asset.text


def test_frontend_route_does_not_allow_path_traversal(monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("not public", encoding="utf-8")
    monkeypatch.setattr("backend.app.main.FRONTEND_DIST", dist)
    client = TestClient(app)

    response = client.get("/%2e%2e/secret.txt")

    assert response.status_code == 404
    with pytest.raises(HTTPException):
        from backend.app.main import serve_frontend_route

        serve_frontend_route("../secret.txt")
