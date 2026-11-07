import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Flat, User
from backend.app.core.security import verify_flat_access
from fastapi import HTTPException

client = TestClient(app)


def test_request_otp_success():
    response = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert response.status_code == 200
    data = response.json()
    assert "demo_hint" in data
    assert data["phone"] == "9876543210"


def test_request_otp_nonexistent_user():
    response = client.post("/api/v1/auth/otp/request", json={"phone": "9999999999"})
    assert response.status_code == 404
    assert "No registered resident or staff account" in response.json()["error"]["message"]


def test_verify_otp_valid():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    response = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["name"] == "Neeraj Kulkarni"
    assert len(data["user"]["flats"]) == 1
    assert data["user"]["flats"][0]["flat_number"] == "T07-1203"
    assert data["user"]["flats"][0]["member_type"] == "OWNER"


def test_verify_otp_invalid():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})  # Swati Joshi
    response = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "000000"})
    assert response.status_code == 401
    assert "Invalid OTP code" in response.json()["error"]["message"]


def test_verify_otp_replay_prevented():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    resp1 = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert resp1.status_code == 200

    resp2 = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert resp2.status_code == 400
    assert "already been used" in resp2.json()["error"]["message"]


def test_verify_otp_rate_limiting():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543212"})  # Aamir Shaikh
    for _ in range(3):
        client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "999999"})
    
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "999999"})
    assert resp.status_code == 429
    assert "Too many invalid attempts" in resp.json()["error"]["message"]


def test_logout_and_revocation():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200

    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    post_logout_resp = client.get("/api/v1/auth/me", headers=headers)
    assert post_logout_resp.status_code == 401
    assert "revoked" in post_logout_resp.json()["error"]["message"]


def test_cross_flat_access_idor_denied():
    db = SessionLocal()
    try:
        user_neeraj = db.query(User).filter(User.phone == "9876543210").first()
        flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()

        with pytest.raises(HTTPException) as exc_info:
            verify_flat_access(user_neeraj, flat_swati.id, action="pay")
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
    finally:
        db.close()


def test_committee_individual_flat_access_strictly_denied():
    # Login as Vikram Sardesai (Committee Member: 9876543250)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543250"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543250", "otp": "123456"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
        flat_id = flat_swati.id
    finally:
        db.close()

    # Committee member attempts to view Swati's individual billing summary
    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert resp.status_code == 403
    assert "Committee members can only access aggregate reports" in resp.json()["error"]["message"]

    # Committee member views authorized aggregate report -> ALLOWED
    agg_resp = client.get("/api/v1/billing/committee/aggregate", headers=headers)
    assert agg_resp.status_code == 200
    agg_data = agg_resp.json()
    assert agg_data["scope"] == "TOWNSHIP_AGGREGATE"
    assert "total_billed_inr" in agg_data


def test_family_member_permission_enforcement():
    # Login as Ananya Kulkarni (Family member of T07-1203: 9876543213)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543213"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543213", "otp": "123456"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    flat_id = login["user"]["flats"][0]["flat_id"]

    # Can read flat billing summary
    resp_read = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert resp_read.status_code == 200

    db = SessionLocal()
    try:
        user_ananya = db.query(User).filter(User.phone == "9876543213").first()
        # Attempt to pay without permission -> Denied
        with pytest.raises(HTTPException) as exc_info:
            verify_flat_access(user_ananya, flat_id, action="pay")
        assert exc_info.value.status_code == 403
        assert "membership does not permit bill payment" in exc_info.value.detail
    finally:
        db.close()


def test_guard_access_to_finance_denied():
    # Login as Suresh Shinde (Guard: 9876543230)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543230"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543230", "otp": "123456"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        flat_id = flat.id
    finally:
        db.close()

    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert resp.status_code == 403
    assert "Gate security staff do not have access" in resp.json()["error"]["message"]
