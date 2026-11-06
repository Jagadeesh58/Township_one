import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Flat, User
from backend.app.core.security import verify_flat_access
from fastapi import HTTPException

client = TestClient(app)


def test_request_otp_success():
    # Neeraj Kulkarni (Resident)
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
    # Request OTP
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    
    # Verify with correct demo code
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
    # First verify
    resp1 = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert resp1.status_code == 200

    # Second verify with same OTP should fail (one-time use)
    resp2 = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert resp2.status_code == 400
    assert "already been used" in resp2.json()["error"]["message"]


def test_verify_otp_rate_limiting():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543212"})  # Aamir Shaikh
    # 3 bad attempts
    for _ in range(3):
        client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "999999"})
    
    # 4th bad attempt should trigger 429
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "999999"})
    assert resp.status_code == 429
    assert "Too many invalid attempts" in resp.json()["error"]["message"]


def test_logout_and_revocation():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access profile
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # Logout
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    # Access after logout should fail
    post_logout_resp = client.get("/api/v1/auth/me", headers=headers)
    assert post_logout_resp.status_code == 401
    assert "revoked" in post_logout_resp.json()["error"]["message"]


def test_cross_flat_access_idor_denied():
    db = SessionLocal()
    try:
        user_neeraj = db.query(User).filter(User.phone == "9876543210").first()
        flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()

        # Neeraj attempts to access Swati's flat T12-0408
        with pytest.raises(HTTPException) as exc_info:
            verify_flat_access(user_neeraj, flat_swati.id, action="pay")
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
    finally:
        db.close()
