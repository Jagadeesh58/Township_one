import json
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.exceptions import InvalidSignature
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import Flat, Gate, OTPChallenge, PreApproval


def get_auth_client(phone: str) -> tuple[TestClient, dict]:
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    client = TestClient(app)
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req.status_code == 200
    res = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert res.status_code == 200
    csrf = res.cookies.get("township_csrf")
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    return client, headers


def test_online_guest_code_preview_does_not_consume_until_arrival():
    resident_client, resident_headers = get_auth_client("9876543210")
    guard_client, guard_headers = get_auth_client("9876543230")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate1 = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    now = datetime.now(UTC)
    create_res = resident_client.post(
        "/api/v1/visitors/pre-approvals",
        json={
            "flat_id": flat.id,
            "guest_name": "Karan Malhotra",
            "phone": "9820099999",
            "purpose": "Dinner Guest",
            "gate_id": gate1.id,
            "valid_from": (now - timedelta(hours=1)).isoformat(),
            "valid_until": (now + timedelta(hours=5)).isoformat(),
            "max_uses": 2,
        },
        headers=resident_headers,
    )
    assert create_res.status_code == 201
    pre_app_data = create_res.json()
    raw_code = pre_app_data["code"]
    pre_app_id = pre_app_data["id"]
    assert raw_code is not None and len(raw_code) == 6

    # Preview is non-consuming; arrival creation consumes exactly one use.
    preview = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "code": raw_code},
        headers=guard_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["remaining_uses"] == 2

    for expected_remaining in (1, 0):
        arrival = guard_client.post(
            "/api/v1/visitors/entries",
            json={
                "gate_id": gate1.id,
                "flat_id": flat.id,
                "visitor_name": "Karan Malhotra",
                "purpose": "Dinner Guest",
                "guest_code": raw_code,
            },
            headers=guard_headers,
        )
        assert arrival.status_code == 201
        assert arrival.json()["status"] == "APPROVED"
        assert arrival.json()["pre_approval_id"] == pre_app_id

        db = SessionLocal()
        stored = db.query(PreApproval).filter(PreApproval.id == pre_app_id).one()
        assert stored.used_count == 2 - expected_remaining
        db.close()

    exhausted = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate1.id,
            "flat_id": flat.id,
            "visitor_name": "Karan Malhotra",
            "purpose": "Dinner Guest",
            "guest_code": raw_code,
        },
        headers=guard_headers,
    )
    assert exhausted.status_code == 422
    assert "maximum allowed uses" in exhausted.json()["detail"]


def test_offline_ecdsa_credential_verification_and_tamper_rejection():
    resident_client, resident_headers = get_auth_client("9876543210")
    guard_client, guard_headers = get_auth_client("9876543230")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate1 = db.query(Gate).filter(Gate.gate_number == 1).first()
    gate2 = db.query(Gate).filter(Gate.gate_number == 2).first()
    db.close()

    now = datetime.now(UTC)
    create_res = resident_client.post(
        "/api/v1/visitors/pre-approvals",
        json={
            "flat_id": flat.id,
            "guest_name": "Meera Joshi",
            "purpose": "Consultation",
            "gate_id": gate1.id,
            "valid_from": (now - timedelta(hours=2)).isoformat(),
            "valid_until": (now + timedelta(hours=6)).isoformat(),
            "max_uses": 1,
        },
        headers=resident_headers,
    )
    assert create_res.status_code == 201
    cred_jwt = create_res.json()["credential_jwt"]
    assert cred_jwt is not None
    assert "." in cred_jwt

    # 1. Valid offline credential at designated Gate 1 -> valid
    v_ok = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "credential_jwt": cred_jwt},
        headers=guard_headers,
    )
    assert v_ok.status_code == 200
    assert v_ok.json()["valid"] is True

    # 2. Gate restriction enforcement: attempt entry at Gate 2 -> rejected
    v_wrong_gate = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate2.id, "credential_jwt": cred_jwt},
        headers=guard_headers,
    )
    assert v_wrong_gate.status_code == 403
    assert "not assigned to the requested gate" in v_wrong_gate.json()["detail"]

    # 3. Tampered payload -> cryptographic verification failure
    payload_hex, sig_hex = cred_jwt.split(".")
    payload_dict = json.loads(bytes.fromhex(payload_hex).decode("utf-8"))
    payload_dict["name"] = "Tampered Imposter"
    tampered_payload_hex = json.dumps(payload_dict, sort_keys=True).encode("utf-8").hex()
    tampered_token = f"{tampered_payload_hex}.{sig_hex}"

    v_tampered = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "credential_jwt": tampered_token},
        headers=guard_headers,
    )
    assert v_tampered.status_code == 200
    assert v_tampered.json()["valid"] is False
    assert "Cryptographic verification failed" in v_tampered.json()["message"]


def test_gate_public_key_and_time_anchor_endpoints():
    guard_client, guard_headers = get_auth_client("9876543230")
    db = SessionLocal()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()
    device_id = "device-test-0000000001"
    generation_id = "generation-test-000001"

    pk_res = guard_client.get("/api/v1/visitors/gate/public-key", headers=guard_headers)
    assert pk_res.status_code == 200
    pk_data = pk_res.json()
    assert pk_data["algorithm"] == "ECDSA_P256_SHA256"
    assert "BEGIN PUBLIC KEY" in pk_data["public_key_pem"]
    assert "offline_notice" in pk_data

    enroll_res = guard_client.post(
        "/api/v1/visitors/gate/devices/enroll",
        json={"device_id": device_id, "generation_id": generation_id, "gate_id": gate.id},
        headers=guard_headers,
    )
    assert enroll_res.status_code == 200
    assert enroll_res.json()["last_sequence"] == 0

    ta_res = guard_client.get(
        "/api/v1/visitors/gate/time-anchor",
        params={"gate_id": gate.id, "device_id": device_id, "generation_id": generation_id},
        headers=guard_headers,
    )
    assert ta_res.status_code == 200
    ta_data = ta_res.json()
    assert ta_data["payload"]["gate_id"] == gate.id
    assert ta_data["payload"]["device_id"] == device_id
    assert ta_data["payload"]["device_generation_id"] == generation_id
    assert ta_data["payload"]["valid_until_unix"] - ta_data["payload"]["timestamp_unix"] == 86400


def test_guest_signing_key_survives_service_cache_reload(monkeypatch):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    from backend.app.core.config import settings
    from backend.app.services import visitor_service

    key_one = ec.generate_private_key(ec.SECP256R1())
    pem_one = key_one.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "SIGNING_KEY", pem_one)
    monkeypatch.setattr(settings, "SIGNING_KEY_FILE", "")
    visitor_service._ECDSA_PRIVATE_KEY = None
    payload = b"persistent-guest-credential"
    signature = visitor_service.get_ecdsa_private_key().sign(payload, ec.ECDSA(hashes.SHA256()))

    visitor_service._ECDSA_PRIVATE_KEY = None
    reloaded_key = visitor_service.get_ecdsa_private_key()
    reloaded_key.public_key().verify(signature, payload, ec.ECDSA(hashes.SHA256()))

    key_two = ec.generate_private_key(ec.SECP256R1())
    pem_two = key_two.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    monkeypatch.setattr(settings, "SIGNING_KEY", pem_two)
    visitor_service._ECDSA_PRIVATE_KEY = None
    with pytest.raises(InvalidSignature):
        visitor_service.get_ecdsa_private_key().public_key().verify(signature, payload, ec.ECDSA(hashes.SHA256()))
    visitor_service._ECDSA_PRIVATE_KEY = None
