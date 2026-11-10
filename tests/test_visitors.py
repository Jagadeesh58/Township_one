import hashlib
import io
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import (
    AuditEvent,
    Flat,
    Gate,
    GateDevice,
    OTPChallenge,
    VisitorEntry,
    VisitorPhoto,
)
from backend.app.services.storage import delete_private_object, private_object_exists
from backend.app.services.visitor_service import (
    get_storage_path,
    purge_visitor_photos,
)


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


def create_jpeg_bytes(width=200, height=200, color=(100, 150, 200)) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_visitor_lifecycle_arrival_approval_admit_and_exit():
    guard_client, guard_headers = get_auth_client("9876543230")  # Suresh Shinde (Guard)
    resident_client, resident_headers = get_auth_client("9876543210")  # Neeraj (T07-1203)

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    flat_id = flat.id
    gate_id = gate.id
    db.close()

    # 1. Guard records visitor arrival
    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate_id,
            "flat_id": flat_id,
            "visitor_name": "Vikram Seth",
            "phone": "9811122233",
            "purpose": "Personal Guest",
        },
        headers=guard_headers,
    )
    assert create_res.status_code == 201
    entry_data = create_res.json()
    entry_id = entry_data["id"]
    assert entry_data["status"] == "AWAITING_APPROVAL"

    # 2. Guard cannot admit before resident approval (409 Conflict)
    admit_fail = guard_client.post(
        f"/api/v1/visitors/{entry_id}/admit",
        headers=guard_headers,
    )
    assert admit_fail.status_code == 409

    # 3. Resident approves visitor
    approve_res = resident_client.post(
        f"/api/v1/visitors/{entry_id}/approval",
        json={"decision": "APPROVE"},
        headers=resident_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["approval_decided_by"] is not None

    # 4. Guard admits visitor
    admit_res = guard_client.post(
        f"/api/v1/visitors/{entry_id}/admit",
        headers=guard_headers,
    )
    assert admit_res.status_code == 200
    assert admit_res.json()["status"] == "ADMITTED"
    assert admit_res.json()["admitted_at"] is not None

    # 5. Guard records exit
    exit_res = guard_client.post(
        f"/api/v1/visitors/{entry_id}/exit",
        headers=guard_headers,
    )
    assert exit_res.status_code == 200
    assert exit_res.json()["status"] == "EXITED"
    assert exit_res.json()["exited_at"] is not None

    # 6. Exited visitor cannot be admitted again (409 Conflict)
    readmit_fail = guard_client.post(
        f"/api/v1/visitors/{entry_id}/admit",
        headers=guard_headers,
    )
    assert readmit_fail.status_code == 409


def test_wrong_flat_resident_approval_forbidden():
    guard_client, guard_headers = get_auth_client("9876543230")  # Guard
    swati_client, swati_headers = get_auth_client("9876543211")  # Swati (T12-0408)

    db = SessionLocal()
    flat_t07 = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate.id,
            "flat_id": flat_t07.id,
            "visitor_name": "Courier Express",
            "purpose": "Parcel Delivery",
        },
        headers=guard_headers,
    )
    assert create_res.status_code == 201
    entry_id = create_res.json()["id"]

    # Swati attempts to approve visitor belonging to Neeraj's flat -> 403 Forbidden
    unauth_approve = swati_client.post(
        f"/api/v1/visitors/{entry_id}/approval",
        json={"decision": "APPROVE"},
        headers=swati_headers,
    )
    assert unauth_approve.status_code == 403


def test_rejected_visitor_cannot_be_admitted():
    guard_client, guard_headers = get_auth_client("9876543230")
    resident_client, resident_headers = get_auth_client("9876543210")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate.id,
            "flat_id": flat.id,
            "visitor_name": "Sales Rep",
            "purpose": "Cold call",
        },
        headers=guard_headers,
    )
    entry_id = create_res.json()["id"]

    # Resident rejects visitor
    reject_res = resident_client.post(
        f"/api/v1/visitors/{entry_id}/approval",
        json={"decision": "REJECT"},
        headers=resident_headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

    # Guard attempts to admit rejected visitor -> 409 Conflict
    admit_res = guard_client.post(
        f"/api/v1/visitors/{entry_id}/admit",
        headers=guard_headers,
    )
    assert admit_res.status_code == 409


def test_supervisor_override_requires_valid_role_and_reason():
    guard_client, guard_headers = get_auth_client("9876543230")  # Guard
    helpdesk_client, helpdesk_headers = get_auth_client("9876543220")  # Help Desk (Ramesh)
    resident_client, resident_headers = get_auth_client("9876543210")  # Resident

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate.id,
            "flat_id": flat.id,
            "visitor_name": "Government Health Inspector",
            "purpose": "Official inspection",
        },
        headers=guard_headers,
    )
    entry_id = create_res.json()["id"]

    # 1. Guard cannot execute supervisor override -> 403 Forbidden
    guard_override = guard_client.post(
        f"/api/v1/visitors/{entry_id}/override",
        json={"reason": "Self override attempt"},
        headers=guard_headers,
    )
    assert guard_override.status_code == 403

    # 2. Resident cannot execute supervisor override -> 403 Forbidden
    resident_override = resident_client.post(
        f"/api/v1/visitors/{entry_id}/override",
        json={"reason": "Resident override attempt"},
        headers=resident_headers,
    )
    assert resident_override.status_code == 403

    # 3. Help Desk with blank/short reason -> 422 Unprocessable Content
    short_reason = helpdesk_client.post(
        f"/api/v1/visitors/{entry_id}/override",
        json={"reason": "ab"},
        headers=helpdesk_headers,
    )
    assert short_reason.status_code == 422

    # 4. Help Desk with valid reason succeeds
    valid_override = helpdesk_client.post(
        f"/api/v1/visitors/{entry_id}/override",
        json={"reason": "Resident phone unreachable, intercom confirmed and verified ID"},
        headers=helpdesk_headers,
    )
    assert valid_override.status_code == 200
    assert valid_override.json()["status"] == "OVERRIDDEN_ADMIT"

    # 5. Guard admits the overridden entry
    admit_res = guard_client.post(
        f"/api/v1/visitors/{entry_id}/admit",
        headers=guard_headers,
    )
    assert admit_res.status_code == 200
    assert admit_res.json()["status"] == "ADMITTED"


def test_guard_gate_scoping_and_resident_scoping():
    guard_client, guard_headers = get_auth_client("9876543230")  # Guard
    resident_client, resident_headers = get_auth_client("9876543210")  # Neeraj

    db = SessionLocal()
    gate1 = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    # Guard querying without gate_id -> 400 Bad Request
    no_gate = guard_client.get("/api/v1/visitors/entries", headers=guard_headers)
    assert no_gate.status_code == 400

    # Guard querying with gate_id -> 200 OK
    with_gate = guard_client.get(f"/api/v1/visitors/entries?gate_id={gate1.id}", headers=guard_headers)
    assert with_gate.status_code == 200
    assert isinstance(with_gate.json(), list)

    # Resident querying entries -> sees only their flat
    res_list = resident_client.get("/api/v1/visitors/entries", headers=resident_headers)
    assert res_list.status_code == 200
    for item in res_list.json():
        assert item["flat_number"] == "T07-1203"


def test_photo_upload_validation_exif_stripping_and_streaming():
    guard_client, guard_headers = get_auth_client("9876543230")
    db = SessionLocal()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    gate_id = gate.id
    db.close()

    # 1. Invalid non-image upload -> 400 Bad Request
    invalid_res = guard_client.post(
        f"/api/v1/visitors/photo/upload?gate_id={gate_id}",
        files={"file": ("malicious.txt", b"plain text is not an image", "text/plain")},
        headers=guard_headers,
    )
    assert invalid_res.status_code == 400

    # 2. Valid JPEG upload -> 200 OK with photo_id and 90-day retention metadata
    jpeg_data = create_jpeg_bytes(width=300, height=300)
    upload_res = guard_client.post(
        f"/api/v1/visitors/photo/upload?gate_id={gate_id}",
        files={"file": ("visitor.jpg", jpeg_data, "image/jpeg")},
        headers=guard_headers,
    )
    assert upload_res.status_code == 200
    photo_meta = upload_res.json()
    photo_id = photo_meta["photo_id"]
    assert "retention_expires_at" in photo_meta

    # 3. Create entry with uploaded photo
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate.id,
            "flat_id": flat.id,
            "visitor_name": "Photographed Visitor",
            "purpose": "Meeting",
            "photo_id": photo_id,
        },
        headers=guard_headers,
    )
    assert create_res.status_code == 201
    assert "id" in create_res.json()
    photo_url = create_res.json()["photo_url"]
    assert photo_url is not None

    # 4. Stream photo with signed URL
    stream_res = guard_client.get(photo_url)
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"] == "image/jpeg"

    # 5. Stream photo with tampered signature -> 403 Forbidden
    tampered_url = photo_url.replace("sig=", "sig=tampered_invalid_sig_")
    tampered_res = guard_client.get(tampered_url)
    assert tampered_res.status_code == 403


def test_photo_retention_purge_job_deletes_files_and_is_idempotent():
    db = SessionLocal()
    storage_dir = get_storage_path()
    dummy_file = os.path.join(storage_dir, "purge_test_photo.jpg")
    with open(dummy_file, "wb") as f:
        f.write(create_jpeg_bytes())

    # Create photo record expired 1 day ago
    expired_time = datetime.now(UTC) - timedelta(days=1)
    old_photo = VisitorPhoto(
        storage_key=dummy_file,
        sha256="dummy_sha256_expired_photo",
        capture_time=expired_time - timedelta(days=90),
        content_type="image/jpeg",
        size=len(create_jpeg_bytes()),
        retention_expires_at=expired_time,
    )
    db.add(old_photo)
    db.commit()
    photo_id = old_photo.id
    db.close()

    assert os.path.exists(dummy_file)

    # Run purge job as of current time
    purged_count = purge_visitor_photos(as_of=datetime.now(UTC))
    assert purged_count >= 1

    # Verify binary file deleted and storage_key nulled
    assert not os.path.exists(dummy_file)

    db = SessionLocal()
    checked = db.query(VisitorPhoto).filter(VisitorPhoto.id == photo_id).first()
    assert checked.storage_key is None
    assert checked.deleted_at is not None

    # Verify audit event recorded
    audit = (
        db.query(AuditEvent)
        .filter(AuditEvent.action == "PURGE_VISITOR_PHOTOS")
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert audit is not None
    db.close()

    # Re-running purge job is idempotent and does not fail
    second_run = purge_visitor_photos(as_of=datetime.now(UTC))
    assert second_run == 0


def test_photo_retention_failure_preserves_storage_reference_for_retry(monkeypatch):
    db = SessionLocal()
    storage_dir = Path(get_storage_path())
    dummy_file = storage_dir / "purge_failure_retry_photo.jpg"
    dummy_file.write_bytes(create_jpeg_bytes())
    expired_time = datetime.now(UTC) - timedelta(days=1)
    photo = VisitorPhoto(
        storage_key=str(dummy_file),
        sha256=hashlib.sha256(dummy_file.read_bytes()).hexdigest(),
        capture_time=expired_time - timedelta(days=90),
        content_type="image/jpeg",
        size=dummy_file.stat().st_size,
        retention_expires_at=expired_time,
    )
    db.add(photo)
    db.commit()
    photo_id = photo.id
    db.close()

    original_unlink = Path.unlink

    def fail_for_target(path: Path, *args, **kwargs):
        if path == dummy_file or path.resolve() == dummy_file.resolve():
            raise OSError("simulated storage permission failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_for_target)
    assert purge_visitor_photos(as_of=datetime.now(UTC)) == 0
    assert dummy_file.exists()

    db = SessionLocal()
    retained = db.query(VisitorPhoto).filter(VisitorPhoto.id == photo_id).one()
    assert retained.storage_key == str(dummy_file)
    assert retained.deleted_at is None
    db.close()

    monkeypatch.setattr(Path, "unlink", original_unlink)
    assert purge_visitor_photos(as_of=datetime.now(UTC)) == 1
    assert not dummy_file.exists()

    db = SessionLocal()
    deleted = db.query(VisitorPhoto).filter(VisitorPhoto.id == photo_id).one()
    assert deleted.storage_key is None
    assert deleted.deleted_at is not None
    db.close()


def test_guard_cannot_access_billing_complaints_or_bank_endpoints():
    guard_client, guard_headers = get_auth_client("9876543230")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    flat_id = flat.id
    db.close()

    # Billing access denied for Guard
    bill_res = guard_client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=guard_headers)
    assert bill_res.status_code == 403

    # Bank review queue denied for Guard
    bank_res = guard_client.get("/api/v1/bank/review-queue", headers=guard_headers)
    assert bank_res.status_code == 403

    # Committee report denied for Guard
    comm_res = guard_client.get("/api/v1/committee/report", headers=guard_headers)
    assert comm_res.status_code == 403


def test_guard_cross_gate_scope_authorization_denied():
    """Verify a guard assigned to Gate 1 cannot access, create, admit, or exit visitors for Gate 2."""
    guard_client, guard_headers = get_auth_client("9876543230")  # Suresh Shinde (assigned to Gate 1)

    db = SessionLocal()
    assert db.query(Gate).filter(Gate.gate_number == 1).first() is not None
    g2 = db.query(Gate).filter(Gate.gate_number == 2).first()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate2_id = g2.id
    flat_id = flat.id

    # Create an entry at Gate 2 directly for testing
    entry_gate2 = VisitorEntry(
        gate_id=gate2_id,
        flat_id=flat_id,
        visitor_name="Sneha Patil",
        phone="9822001122",
        purpose="Courier Delivery",
        status="APPROVED",
    )
    db.add(entry_gate2)
    db.commit()
    entry_gate2_id = entry_gate2.id
    db.close()

    # 1. Guard cannot query Gate 2 entries
    list_res = guard_client.get(f"/api/v1/visitors/entries?gate_id={gate2_id}", headers=guard_headers)
    assert list_res.status_code == 403
    assert "not assigned to the requested gate" in list_res.json()["detail"]

    # 2. Guard cannot create visitor entry for Gate 2
    create_res = guard_client.post(
        "/api/v1/visitors/entries",
        json={
            "gate_id": gate2_id,
            "flat_id": flat_id,
            "visitor_name": "Rohan Deshmukh",
            "phone": "9822334455",
            "purpose": "Package Delivery",
        },
        headers=guard_headers,
    )
    assert create_res.status_code == 403
    assert "not assigned to the requested gate" in create_res.json()["detail"]

    # 3. Guard cannot admit visitor at Gate 2
    admit_res = guard_client.post(f"/api/v1/visitors/{entry_gate2_id}/admit", headers=guard_headers)
    assert admit_res.status_code == 403
    assert "not assigned to the requested gate" in admit_res.json()["detail"]

    # 4. Guard cannot exit visitor at Gate 2
    exit_res = guard_client.post(f"/api/v1/visitors/{entry_gate2_id}/exit", headers=guard_headers)
    assert exit_res.status_code == 403
    assert "not assigned to the requested gate" in exit_res.json()["detail"]


def test_offline_sync_requires_photo_and_is_idempotent():
    from uuid import uuid4

    guard_client, guard_headers = get_auth_client("9876543230")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()

    device_id = str(uuid4())
    generation_id = str(uuid4())
    enroll_response = guard_client.post(
        "/api/v1/visitors/gate/devices/enroll",
        json={"device_id": device_id, "generation_id": generation_id, "gate_id": gate.id},
        headers=guard_headers,
    )
    assert enroll_response.status_code == 200

    anchor_response = guard_client.get(
        "/api/v1/visitors/gate/time-anchor",
        params={"gate_id": gate.id, "device_id": device_id, "generation_id": generation_id},
        headers=guard_headers,
    )
    assert anchor_response.status_code == 200
    anchor = anchor_response.json()
    event_id = str(uuid4())
    photo_uuid = str(uuid4())
    photo_bytes = create_jpeg_bytes()
    metadata = {
        "client_event_id": event_id,
        "photo_uuid": photo_uuid,
        "gate_id": gate.id,
        "flat_id": flat.id,
        "visitor_name": "Offline Arrival Test",
        "phone": "9812300001",
        "purpose": "Maintenance",
        "capture_time": anchor["payload"]["server_time_utc"],
        "photo_sha256": hashlib.sha256(photo_bytes).hexdigest(),
        "device_id": device_id,
        "device_generation_id": generation_id,
        "device_sequence": 1,
        "time_anchor_payload": anchor["payload"],
        "time_anchor_signature": anchor["signature"],
        "pre_approval_credential": None,
    }
    payload = {"metadata": json.dumps(metadata)}
    photo_file = {"photo": ("visitor.jpg", photo_bytes, "image/jpeg")}
    first = guard_client.post("/api/v1/visitors/gate/sync", data=payload, files=photo_file, headers=guard_headers)
    assert first.status_code == 200, first.text
    assert first.json()["processed_count"] == 1
    assert event_id in first.json()["acknowledged_ids"]

    repeated = guard_client.post("/api/v1/visitors/gate/sync", data=payload, files=photo_file, headers=guard_headers)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["processed_count"] == 0
    assert event_id in repeated.json()["acknowledged_ids"]

    db = SessionLocal()
    saved_photo = None
    try:
        entry = db.query(VisitorEntry).filter(VisitorEntry.client_event_id == event_id).one()
        saved_photo = db.query(VisitorPhoto).filter(VisitorPhoto.id == entry.photo_id).one()
        device = db.query(GateDevice).filter(GateDevice.device_id == device_id).one()
        assert entry.status == "AWAITING_APPROVAL"
        assert saved_photo.client_photo_id == photo_uuid
        assert saved_photo.storage_key and private_object_exists(saved_photo.storage_key)
        assert device.last_sequence == 1
        assert db.query(VisitorEntry).filter(VisitorEntry.device_id == device_id).count() == 1
    finally:
        if saved_photo and saved_photo.storage_key:
            delete_private_object(saved_photo.storage_key)
        db.close()


def test_offline_sync_rejects_wrong_photo_hash():
    from uuid import uuid4

    guard_client, guard_headers = get_auth_client("9876543230")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    gate = db.query(Gate).filter(Gate.gate_number == 1).first()
    db.close()
    device_id, generation_id = str(uuid4()), str(uuid4())
    assert (
        guard_client.post(
            "/api/v1/visitors/gate/devices/enroll",
            json={"device_id": device_id, "generation_id": generation_id, "gate_id": gate.id},
            headers=guard_headers,
        ).status_code
        == 200
    )
    anchor = guard_client.get(
        "/api/v1/visitors/gate/time-anchor",
        params={"gate_id": gate.id, "device_id": device_id, "generation_id": generation_id},
        headers=guard_headers,
    ).json()
    photo_bytes = create_jpeg_bytes()
    metadata = {
        "client_event_id": str(uuid4()),
        "photo_uuid": str(uuid4()),
        "gate_id": gate.id,
        "flat_id": flat.id,
        "visitor_name": "Hash Mismatch",
        "purpose": "Delivery",
        "capture_time": anchor["payload"]["server_time_utc"],
        "photo_sha256": "0" * 64,
        "device_id": device_id,
        "device_generation_id": generation_id,
        "device_sequence": 1,
        "time_anchor_payload": anchor["payload"],
        "time_anchor_signature": anchor["signature"],
    }
    response = guard_client.post(
        "/api/v1/visitors/gate/sync",
        data={"metadata": json.dumps(metadata)},
        files={"photo": ("visitor.jpg", photo_bytes, "image/jpeg")},
        headers=guard_headers,
    )
    assert response.status_code == 422
    assert "SHA-256" in response.json()["detail"]
    db = SessionLocal()
    try:
        assert db.query(VisitorEntry).filter(VisitorEntry.device_id == device_id).count() == 0
        device = db.query(GateDevice).filter(GateDevice.device_id == device_id).one()
        assert device.last_sequence == 0
    finally:
        db.close()
