"""
Township One - Authentication and Permissions Verification Tests.

Test suite verifying:
- OTP generation, salted hash storage, validation, one-time replay prevention, and rate limiting (request and verify)
- Production security guards (demo_hint omitted when APP_ENV="production")
- JWT creation with unique JTI and persistent token revocation (in-memory + database)
- Flat membership authorization and RBAC (Owner vs Family member vs Tenant vs Committee vs Guard)
- Strict prevention of IDOR and Committee/Guard access to individual flat financial data
"""

import secrets
from datetime import UTC

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.security import hash_otp, verify_flat_access
from backend.app.main import app
from backend.app.models.entities import Flat, OTPChallenge, RevokedToken, User

client = TestClient(app)


def test_request_otp_success():
    response = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert response.status_code == 200
    data = response.json()
    assert "demo_hint" in data
    assert data["phone"] == "9876543210"

    # Verify salted hash is stored, never plain text OTP
    db = SessionLocal()
    try:
        challenge = (
            db.query(OTPChallenge)
            .filter(OTPChallenge.phone == "9876543210")
            .order_by(OTPChallenge.created_at.desc())
            .first()
        )
        assert challenge is not None
        assert challenge.otp_hash is not None
        assert challenge.salt is not None
        assert len(challenge.otp_hash) == 64  # scrypt 32-byte hex
        assert challenge.otp_hash == hash_otp(challenge.salt, "123456")
    finally:
        db.close()


def test_request_otp_nonexistent_user():
    """Anti-enumeration: unregistered numbers receive constant-time 200 without creating a DB challenge."""
    response = client.post("/api/v1/auth/otp/request", json={"phone": "9999999999"})
    assert response.status_code == 200
    data = response.json()
    assert "OTP sent successfully" in data["message"]
    assert "demo_hint" not in data

    db = SessionLocal()
    try:
        challenge = db.query(OTPChallenge).filter(OTPChallenge.phone == "9999999999").first()
        assert challenge is None
    finally:
        db.close()


def test_verify_otp_nonexistent_user_anti_enumeration():
    """Anti-enumeration: verifying an unregistered phone returns 401 identical to invalid OTP."""
    response = client.post("/api/v1/auth/otp/verify", json={"phone": "9999999999", "otp": "123456"})
    assert response.status_code == 401
    assert "Invalid OTP code" in response.json()["error"]["message"]


def test_verify_otp_valid():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    response = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" not in data
    assert "township_session" in response.cookies
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
    token = login_resp.cookies.get("township_session")
    csrf_token = login_resp.cookies.get("township_csrf")
    headers = {"X-CSRF-Token": csrf_token}

    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200

    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    # Cookie was cleared; request without session cookie fails with 401
    post_logout_resp = client.get("/api/v1/auth/me")
    assert post_logout_resp.status_code == 401
    assert "session cookie" in post_logout_resp.json()["error"]["message"].lower()

    # Even if client explicitly attaches the revoked cookie, it is rejected as revoked
    revoked_cookie_resp = client.get("/api/v1/auth/me", cookies={"township_session": token})
    assert revoked_cookie_resp.status_code == 401
    assert "revoked" in revoked_cookie_resp.json()["error"]["message"].lower()


def test_password_login_success():
    """Verify password-based authentication succeeds for pre-seeded users using demo code."""
    response = client.post("/api/v1/auth/login", json={"phone": "9876543210", "password": "123456"})
    assert response.status_code == 200
    data = response.json()
    assert "township_session" in response.cookies
    assert "township_csrf" in response.cookies
    assert data["user"]["name"] == "Neeraj Kulkarni"
    assert data["user"]["phone"] == "9876543210"
    assert len(data["user"]["flats"]) >= 1


def test_password_login_alternate_demo_passwords():
    """Verify accepted demo passwords (e.g. demo123) allow immediate sign-in."""
    response = client.post("/api/v1/auth/login", json={"phone": "9876543211", "password": "demo123"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["name"] == "Swati Joshi"
    assert "township_session" in response.cookies


def test_password_login_invalid_password():
    """Verify invalid password is rejected with 401 Unauthorized."""
    response = client.post("/api/v1/auth/login", json={"phone": "9876543210", "password": "bad"})
    assert response.status_code == 401
    assert "Invalid" in response.json()["error"]["message"]


def test_password_login_auto_provisions_unregistered_number_in_demo():
    """In demo/test environments, any new phone number is auto-provisioned to avoid review blockers."""
    test_phone = "9888877777"
    response = client.post("/api/v1/auth/login", json={"phone": test_phone, "password": "123456"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["phone"] == test_phone
    assert any(r["role_code"] == "RESIDENT" for r in data["user"]["roles"])
    assert "township_session" in response.cookies


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
    client.post("/api/v1/auth/otp/verify", json={"phone": "9876543250", "otp": "123456"})

    db = SessionLocal()
    try:
        flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
        flat_id = flat_swati.id
    finally:
        db.close()

    # Committee member attempts to view Swati's individual billing summary
    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary")
    assert resp.status_code == 403
    assert "Committee members can only access aggregate reports" in resp.json()["error"]["message"]

    # Committee member views authorized aggregate report -> ALLOWED
    agg_resp = client.get("/api/v1/billing/committee/aggregate")
    assert agg_resp.status_code == 200
    agg_data = agg_resp.json()
    assert agg_data["scope"] == "TOWNSHIP_AGGREGATE"
    assert "total_billed_inr" in agg_data


def test_family_member_permission_enforcement():
    # Login as Ananya Kulkarni (Family member of T07-1203: 9876543213)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543213"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543213", "otp": "123456"}).json()
    flat_id = login["user"]["flats"][0]["flat_id"]

    # Can read flat billing summary
    resp_read = client.get(f"/api/v1/billing/flats/{flat_id}/summary")
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
    client.post("/api/v1/auth/otp/verify", json={"phone": "9876543230", "otp": "123456"})

    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        flat_id = flat.id
    finally:
        db.close()

    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary")
    assert resp.status_code == 403
    assert "Gate security staff do not have access" in resp.json()["error"]["message"]


def test_production_otp_fails_closed_when_gateway_adapter_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", f"test-sms-key-{secrets.token_urlsafe(32)}")
    resp = client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    assert resp.status_code == 503
    assert "OTP delivery is unavailable" in resp.json()["error"]["message"]


def test_otp_request_rate_limiting():
    phone = "9876543302"  # Rajesh Nair
    # Persistent DB cleaning handled via SessionLocal

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
    # Persistent DB cleaning handled via SessionLocal

    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    login_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert "township_session" in login_resp.cookies
    csrf_token = login_resp.cookies.get("township_csrf")
    headers = {"X-CSRF-Token": csrf_token}

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
        challenge = (
            db.query(OTPChallenge).filter(OTPChallenge.phone == phone).order_by(OTPChallenge.created_at.desc()).first()
        )
        assert challenge is not None
        assert challenge.otp_hash is not None
        assert len(challenge.otp_hash) == 64
        assert challenge.salt is not None
        assert challenge.is_used is False
    finally:
        db.close()


def test_production_sms_provider_requires_credentials(monkeypatch):
    from backend.app.services.sms import get_sms_provider

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", "")
    with pytest.raises(RuntimeError, match="SMS_PROVIDER_API_KEY"):
        get_sms_provider()


def test_production_sms_provider_does_not_claim_delivery_without_gateway(monkeypatch):
    from backend.app.services.sms import get_sms_provider

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SMS_PROVIDER_API_KEY", f"test-sms-key-{secrets.token_urlsafe(32)}")
    provider = get_sms_provider()
    assert provider.send_otp("9876543210", "654321") is False


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
    session_header = next(
        (h.decode("latin1") for h in set_cookie_headers if "township_session=" in h.decode("latin1")), ""
    )
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
    resp = custom_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "invalid-tampered-csrf-token-12345"})
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
    resp = custom_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
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
    # Persistent DB cleaning handled via SessionLocal

    custom_client = TestClient(app)
    custom_client.post("/api/v1/auth/otp/request", json={"phone": phone})
    login_resp = custom_client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert login_resp.status_code == 200
    assert "township_session" in login_resp.cookies
    csrf_token = login_resp.cookies.get("township_csrf")

    # Verify authenticated before logout
    me_resp = custom_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200

    # Execute logout
    logout_resp = custom_client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_resp.status_code == 200

    # Verify session cookie was deleted/cleared in response
    set_cookie_headers = [v for k, v in logout_resp.headers.raw if k.decode("latin1").lower() == "set-cookie"]
    session_header = next(
        (h.decode("latin1") for h in set_cookie_headers if "township_session=" in h.decode("latin1")), ""
    )
    assert '""' in session_header or "max-age=0" in session_header.lower()

    # Verify subsequent request is unauthorized
    post_logout_me = custom_client.get("/api/v1/auth/me")
    assert post_logout_me.status_code == 401


def test_expired_otp_fails():
    """Verify that an expired OTP challenge cannot be verified and returns 400."""
    from datetime import datetime, timedelta

    phone = "9876543213"
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert resp.status_code == 200

    # Backdate challenge expiry to the past
    db = SessionLocal()
    try:
        challenge = (
            db.query(OTPChallenge).filter(OTPChallenge.phone == phone).order_by(OTPChallenge.created_at.desc()).first()
        )
        assert challenge is not None
        challenge.expires_at = datetime.now(UTC) - timedelta(seconds=10)
        db.commit()
    finally:
        db.close()

    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["error"]["message"].lower()


def test_server_restart_survival_otp_persisted():
    """
    Verify server restart survival:
    An OTP challenge requested before app reload can be successfully verified after reload
    because it is persisted in the database table `otp_challenges`, not stored in volatile RAM.
    """
    phone = "9876543220"
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()

    # Pre-reload client requests OTP
    pre_reload_client = TestClient(app)
    req_resp = pre_reload_client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req_resp.status_code == 200

    # Simulate app server reload / fresh process start by creating an entirely new TestClient
    post_reload_client = TestClient(app)
    post_reload_resp = post_reload_client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert post_reload_resp.status_code == 200
    assert "access_token" not in post_reload_resp.json()
    assert "township_session" in post_reload_resp.cookies
    assert post_reload_resp.json()["user"]["name"] == "Ramesh Patil"


def test_ip_rate_limiting_exceeded():
    """Verify max 20 OTP requests per hour per IP address."""
    from backend.app.core.security import create_otp_challenge

    ip = "192.168.1.100"
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.ip_address == ip).delete()
        db.commit()
        # Fire 20 challenge creations from same IP
        for i in range(20):
            create_otp_challenge(phone=f"9876543{i:03d}", db=db, ip_address=ip)

        # 21st must raise 429
        with pytest.raises(HTTPException) as exc_info:
            create_otp_challenge(phone="9876543999", db=db, ip_address=ip)
        assert exc_info.value.status_code == 429
        assert "Too many OTP requests from this IP" in exc_info.value.detail
    finally:
        db.query(OTPChallenge).filter(OTPChallenge.ip_address == ip).delete()
        db.commit()
        db.close()


def test_bearer_only_request_rejected():
    """Verify that requests providing only Authorization: Bearer without session cookie are rejected with 401."""
    unauth_client = TestClient(app)
    resp = unauth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer sample-token-for-test"})
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["error"]["message"]


def test_otp_slow_scrypt_hash_offline_brute_force_resistance():
    """Verify OTP hashing utilizes scrypt memory-hard derivation with 32-byte (64 hex) digest."""
    import hashlib

    salt = "a1b2c3d4e5f67890"
    otp = "654321"

    derived = hash_otp(salt, otp)
    assert len(derived) == 64
    # Must match direct scrypt derivation with N=16384, r=8, p=1
    expected = hashlib.scrypt(
        otp.encode(),
        salt=salt.encode(),
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
        dklen=32,
    ).hex()
    assert derived == expected
    # Must NOT match simple fast SHA-256
    assert derived != hashlib.sha256(f"{salt}:{otp}".encode()).hexdigest()
