"""
Township One - Authentication and Permissions Verification Tests.

Test suite verifying:
- OTP generation, salted hash storage, validation, one-time replay prevention, and rate limiting (request and verify)
- Production security guards (demo_hint omitted when APP_ENV="production")
- JWT creation with unique JTI and persistent token revocation (in-memory + database)
- Flat membership authorization and RBAC (Owner vs Family member vs Tenant vs Committee vs Guard)
- Strict prevention of IDOR and Committee/Guard access to individual flat financial data
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.models.entities import Flat, User, RevokedToken
from backend.app.core.security import verify_flat_access, OTP_STORE
from fastapi import HTTPException

client = TestClient(app)


def test_request_otp_success():
    response = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert response.status_code == 200
    data = response.json()
    assert "demo_hint" in data
    assert data["phone"] == "9876543210"

    # Verify salted hash is stored, never plain text OTP
    assert "9876543210" in OTP_STORE
    challenge = OTP_STORE["9876543210"]
    assert "otp_hash" in challenge
    assert "salt" in challenge
    assert "otp" not in challenge
    assert len(challenge["otp_hash"]) == 64  # SHA-256


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


def test_demo_hint_hidden_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", "test-sms-key")
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert resp.status_code == 200
    data = resp.json()
    assert "demo_hint" not in data or data.get("demo_hint") is None


def test_otp_request_rate_limiting():
    phone = "9876543302"  # Rajesh Nair
    from backend.app.core.security import OTP_STORE
    OTP_STORE.pop(phone, None)
    
    # Fire 5 requests
    for _ in range(5):
        resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
        assert resp.status_code == 200
    
    # 6th request within window must be rejected
    rate_limited_resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert rate_limited_resp.status_code == 429
    assert "Too many OTP requests" in rate_limited_resp.json()["error"]["message"]


def test_database_persisted_revoked_token():
    phone = "9876543210"
    from backend.app.models.entities import OTPChallenge
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    from backend.app.core.security import OTP_STORE
    OTP_STORE.pop(phone, None)

    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"}).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == "9876543210").first()
        revoked_entry = db.query(RevokedToken).filter(RevokedToken.user_id == user.id).first()
        assert revoked_entry is not None
        assert revoked_entry.token_jti is not None
    finally:
        db.close()



def test_database_persisted_otp_challenge():
    """Verify OTP challenge is stored persistently in database table otp_challenges."""
    phone = "9876543210"
    from backend.app.models.entities import OTPChallenge
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert resp.status_code == 200

    from backend.app.models.entities import OTPChallenge
    db = SessionLocal()
    try:
        challenge = db.query(OTPChallenge).filter(OTPChallenge.phone == phone).order_by(OTPChallenge.created_at.desc()).first()
        assert challenge is not None
        assert challenge.otp_hash is not None
        assert len(challenge.otp_hash) == 64
        assert challenge.salt is not None
        assert challenge.is_used is False
    finally:
        db.close()


def test_production_sms_provider_fails_closed_without_credentials(monkeypatch):
    """Verify that in production mode, missing SMS_PROVIDER_API_KEY fails closed."""
    from backend.app.services.sms import get_sms_provider

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", "")

    with pytest.raises(RuntimeError) as exc_info:
        get_sms_provider()
    assert "SMS provider requires a valid SMS_PROVIDER_API_KEY" in str(exc_info.value)


def test_production_sms_provider_succeeds_with_configured_credentials(monkeypatch):
    """Verify that in production mode, configured SMS_PROVIDER_API_KEY initializes provider successfully."""
    from backend.app.services.sms import get_sms_provider

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", "test-sms-key")

    provider = get_sms_provider()
    assert provider is not None
    assert provider.send_otp("9876543210", "654321") is True


def test_cookie_httponly_and_csrf_on_verify_otp():
    """Verify verify-otp sets HttpOnly SameSite=Lax session cookie and readable CSRF cookie."""
    phone = "9876543210"
    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert resp.status_code == 200

    # Verify session cookie
    assert "township_session" in resp.cookies
    session_cookie = resp.cookies["township_session"]
    assert len(session_cookie) > 20

    # Verify CSRF cookie
    assert "township_csrf" in resp.cookies
    csrf_cookie = resp.cookies["township_csrf"]
    assert len(csrf_cookie) > 20

    # Verify Set-Cookie header directives
    set_cookie_headers = [v for k, v in resp.headers.raw if k.decode("latin1").lower() == "set-cookie"]
    session_header = next((h.decode("latin1") for h in set_cookie_headers if "township_session=" in h.decode("latin1")), "")
    assert "httponly" in session_header.lower()
    assert "samesite=lax" in session_header.lower()

    csrf_header = next((h.decode("latin1") for h in set_cookie_headers if "township_csrf=" in h.decode("latin1")), "")
    assert "httponly" not in csrf_header.lower()
    assert "samesite=lax" in csrf_header.lower()


def test_csrf_missing_on_post_returns_403():
    """Verify that state-changing POST with session cookie but missing X-CSRF-Token is rejected with 403."""
    custom_client = TestClient(app)
    custom_client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login_resp = custom_client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert login_resp.status_code == 200

    # Attempt POST /api/v1/auth/logout without X-CSRF-Token header
    resp = custom_client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["error"]["message"]


def test_csrf_invalid_on_post_returns_403():
    """Verify that state-changing POST with invalid X-CSRF-Token is rejected with 403."""
    custom_client = TestClient(app)
    custom_client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login_resp = custom_client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert login_resp.status_code == 200

    # Attempt POST with mismatched CSRF header
    resp = custom_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": "invalid-tampered-csrf-token-12345"}
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["error"]["message"]


def test_csrf_valid_on_post_returns_200():
    """Verify that state-changing POST with valid matching X-CSRF-Token header succeeds with 200."""
    custom_client = TestClient(app)
    custom_client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login_resp = custom_client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert login_resp.status_code == 200
    csrf_token = login_resp.cookies.get("township_csrf")

    # POST with matching X-CSRF-Token header
    resp = custom_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token}
    )
    assert resp.status_code == 200
    assert "Logged out successfully" in resp.json()["message"]


def test_logout_clears_cookie_and_revokes_token():
    """Verify that logout deletes both session and CSRF cookies, and revokes access token."""
    phone = "9876543211"
    from backend.app.models.entities import OTPChallenge
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    from backend.app.core.security import OTP_STORE
    OTP_STORE.pop(phone, None)

    custom_client = TestClient(app)
    custom_client.post("/api/v1/auth/otp/request", json={"phone": phone})
    login_resp = custom_client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert login_resp.status_code == 200
    session_token = login_resp.cookies.get("township_session")
    csrf_token = login_resp.cookies.get("township_csrf")

    # Verify authenticated before logout
    me_resp = custom_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200

    # Execute logout
    logout_resp = custom_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token}
    )
    assert logout_resp.status_code == 200

    # Verify session cookie was deleted/cleared in response
    set_cookie_headers = [v for k, v in logout_resp.headers.raw if k.decode("latin1").lower() == "set-cookie"]
    session_header = next((h.decode("latin1") for h in set_cookie_headers if "township_session=" in h.decode("latin1")), "")
    assert ('""' in session_header or 'max-age=0' in session_header.lower())

    # Verify subsequent request is unauthorized
    post_logout_me = custom_client.get("/api/v1/auth/me")
    assert post_logout_me.status_code == 401
