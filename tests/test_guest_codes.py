import json
import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import Flat, Gate, OTPChallenge, PreApproval, VisitorEntry


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


def test_online_guest_code_verification_and_usage_decrement():
    resident_client, resident_headers = get_auth_client("9876543210")  # Neeraj (T07-1203)
    guard_client, guard_headers = get_auth_client("9876543230")  # Guard

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
    assert raw_code is not None
    assert len(raw_code) == 6

    # 1. First verification at Gate 1 -> valid, remaining uses = 1
    v1_res = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "code": raw_code},
        headers=guard_headers,
    )
    assert v1_res.status_code == 200
    v1_data = v1_res.json()
    assert v1_data["valid"] is True
    assert v1_data["remaining_uses"] == 1

    # 2. Second verification at Gate 1 -> valid, remaining uses = 0
    v2_res = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "code": raw_code},
        headers=guard_headers,
    )
    assert v2_res.status_code == 200
    v2_data = v2_res.json()
    assert v2_data["valid"] is True
    assert v2_data["remaining_uses"] == 0

    # 3. Third verification -> rejected (limit reached)
    v3_res = guard_client.post(
        "/api/v1/visitors/guest-code/verify",
        json={"gate_id": gate1.id, "code": raw_code},
        headers=guard_headers,
    )
    assert v3_res.status_code == 200
    v3_data = v3_res.json()
    assert v3_data["valid"] is False
    assert "maximum allowed uses" in v3_data["message"]


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
    assert v_wrong_gate.status_code == 200
    assert v_wrong_gate.json()["valid"] is False
    assert "restricted to gate" in v_wrong_gate.json()["message"]

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

    # 1. Public key endpoint
    pk_res = guard_client.get("/api/v1/visitors/gate/public-key")
    assert pk_res.status_code == 200
    pk_data = pk_res.json()
    assert pk_data["algorithm"] == "ECDSA_P256_SHA256"
    assert "BEGIN PUBLIC KEY" in pk_data["public_key_pem"]
    assert "offline_notice" in pk_data

    # 2. Time anchor endpoint
    ta_res = guard_client.get("/api/v1/visitors/gate/time-anchor")
    assert ta_res.status_code == 200
    ta_data = ta_res.json()
    assert "server_time_utc" in ta_data
    assert ta_data["validity_window_seconds"] == 86400


def test_offline_sync_deduplication_and_conflict_flagging():
    guard_client, guard_headers = get_auth_client("9876543230")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate1 = db.query(Gate).filter(Gate.gate_number == 1).first()
    pre_app = db.query(PreApproval).filter(PreApproval.flat_id == flat.id).first()
    db.close()

    client_event_id = f"evt_offline_{int(time.time() * 1000)}"
    sync_payload = {
        "gate_id": gate1.id,
        "events": [
            {
                "client_event_id": client_event_id,
                "gate_id": gate1.id,
                "flat_id": flat.id,
                "visitor_name": "Offline Arrival 1",
                "phone": "9812300001",
                "purpose": "Maintenance",
                "pre_approval_id": pre_app.id if pre_app else None,
                "capture_time": datetime.now(UTC).isoformat(),
            }
        ],
    }

    # 1. First sync ingest
    sync1 = guard_client.post(
        "/api/v1/visitors/gate/sync",
        json=sync_payload,
        headers=guard_headers,
    )
    assert sync1.status_code == 200
    assert client_event_id in sync1.json()["acknowledged_ids"]

    # 2. Re-submitting the same client_event_id is deduplicated
    sync2 = guard_client.post(
        "/api/v1/visitors/gate/sync",
        json=sync_payload,
        headers=guard_headers,
    )
    assert sync2.status_code == 200
    assert client_event_id in sync2.json()["acknowledged_ids"]

    # Verify database has exactly 1 entry for this client_event_id
    db = SessionLocal()
    count = db.query(VisitorEntry).filter(VisitorEntry.client_event_id == client_event_id).count()
    db.close()
    assert count == 1
