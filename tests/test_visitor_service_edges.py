"""Focused edge-case coverage for visitor photo, credential and lifecycle rules."""

import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Flat, Gate, User, VisitorEntry
from backend.app.schemas.visitors import PreApprovalCreate, VisitorStatus
from backend.app.services import visitor_service as service


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


def _seed_context(db):
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").one()
    gate = db.query(Gate).filter(Gate.gate_number == 1).one()
    resident = db.query(User).filter(User.phone == "9876543210").one()
    guard = db.query(User).filter(User.phone == "9876543230").one()
    return flat, gate, resident, guard


def _pem_for(key: ec.EllipticCurvePrivateKey) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")


def _credential(payload: dict, key: ec.EllipticCurvePrivateKey | None = None) -> str:
    signing_key = key or service.get_ecdsa_private_key()
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"{raw.hex()}.{signing_key.sign(raw, ec.ECDSA(hashes.SHA256())).hex()}"


def _jpeg(width: int = 20, height: int = 20) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color=(30, 90, 120)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _preapproval_payload(flat_id: str, gate_id: str, *, start=None, end=None, guest_name="Edge Guest"):
    now = datetime.now(UTC)
    return {
        "cid": "edge-credential-id",
        "fid": flat_id,
        "name": guest_name,
        "from": (start or now - timedelta(hours=1)).isoformat(),
        "until": (end or now + timedelta(hours=2)).isoformat(),
        "gate": gate_id,
        "max": 2,
    }


def test_signing_key_loads_from_file_and_rejects_invalid_or_wrong_curve(tmp_path, monkeypatch):
    original_key = service._ECDSA_PRIVATE_KEY
    key = ec.generate_private_key(ec.SECP256R1())
    key_path = tmp_path / "signing.pem"
    key_path.write_text(_pem_for(key), encoding="utf-8")
    monkeypatch.setattr(settings, "APP_ENV", "test")
    monkeypatch.setattr(settings, "SIGNING_KEY", "")
    monkeypatch.setattr(settings, "SIGNING_KEY_FILE", str(key_path))
    service._ECDSA_PRIVATE_KEY = None
    try:
        loaded = service.get_ecdsa_private_key()
        assert loaded.public_key().public_numbers() == key.public_key().public_numbers()

        service._ECDSA_PRIVATE_KEY = None
        monkeypatch.setattr(settings, "SIGNING_KEY_FILE", str(tmp_path / "missing.pem"))
        with pytest.raises(RuntimeError, match="Unable to read"):
            service.get_ecdsa_private_key()

        monkeypatch.setattr(settings, "SIGNING_KEY_FILE", "")
        monkeypatch.setattr(settings, "SIGNING_KEY", "not-a-pem")
        with pytest.raises(RuntimeError, match="valid unencrypted PEM"):
            service.get_ecdsa_private_key()

        wrong_curve = ec.generate_private_key(ec.SECP384R1())
        monkeypatch.setattr(settings, "SIGNING_KEY", _pem_for(wrong_curve))
        with pytest.raises(RuntimeError, match="P-256"):
            service.get_ecdsa_private_key()
    finally:
        service._ECDSA_PRIVATE_KEY = original_key


def test_production_requires_stable_signing_key_and_development_warns(monkeypatch):
    original_key = service._ECDSA_PRIVATE_KEY
    monkeypatch.setattr(settings, "SIGNING_KEY", "")
    monkeypatch.setattr(settings, "SIGNING_KEY_FILE", "")
    service._ECDSA_PRIVATE_KEY = None
    try:
        monkeypatch.setattr(settings, "APP_ENV", "production")
        with pytest.raises(RuntimeError, match="required in production"):
            service.get_ecdsa_private_key()

        monkeypatch.setattr(settings, "APP_ENV", "development")
        warning = Mock()
        monkeypatch.setattr(service._logger, "warning", warning)
        first = service.get_ecdsa_private_key()
        warning.assert_called_once()
        assert "ephemeral development" in warning.call_args.args[0]
        assert service.get_ecdsa_private_key() is first
    finally:
        service._ECDSA_PRIVATE_KEY = original_key


def test_photo_validation_rejects_size_format_and_dimensions():
    with pytest.raises(HTTPException) as size_error:
        service.validate_and_process_photo(b"x" * (5 * 1024 * 1024 + 1), "large.jpg")
    assert size_error.value.status_code == 400

    gif_buffer = io.BytesIO()
    Image.new("RGB", (5, 5)).save(gif_buffer, format="GIF")
    with pytest.raises(HTTPException) as format_error:
        service.validate_and_process_photo(gif_buffer.getvalue(), "unsupported.gif")
    assert "Unsupported image format" in str(format_error.value.detail)

    with pytest.raises(HTTPException) as dimension_error:
        service.validate_and_process_photo(_jpeg(4001, 1), "too-wide.jpg")
    assert "dimensions" in str(dimension_error.value.detail)

    with pytest.raises(HTTPException, match="Invalid image file"):
        service.validate_and_process_photo(b"not-an-image", "broken.jpg")


def test_signed_photo_url_accepts_valid_signature_and_rejects_tampering_and_expiry():
    signed_url = service.generate_signed_photo_url("entry-1", "photo-1", expires_in_seconds=1000)
    query = dict(part.split("=", 1) for part in signed_url.split("?", 1)[1].split("&"))
    expires = int(query["expires"])
    assert expires <= int(datetime.now(UTC).timestamp()) + 300
    assert service.verify_photo_signature("entry-1", "photo-1", expires, query["sig"])
    assert not service.verify_photo_signature("entry-1", "other-photo", expires, query["sig"])
    assert not service.verify_photo_signature("entry-1", "photo-1", 1, query["sig"])


def test_visitor_transition_and_supervisor_override_reject_invalid_paths(db_session):
    flat, gate, _, guard = _seed_context(db_session)
    entry = VisitorEntry(
        gate_id=gate.id,
        flat_id=flat.id,
        visitor_name="Transition Guest",
        purpose="Test transition",
        status=VisitorStatus.AWAITING_APPROVAL.value,
    )
    db_session.add(entry)
    db_session.flush()

    with pytest.raises(HTTPException) as illegal:
        service.transition_visitor_entry(db_session, entry, VisitorStatus.EXITED, guard.id, "GUARD")
    assert illegal.value.status_code == 409

    with pytest.raises(HTTPException) as denied:
        service.apply_supervisor_override(db_session, entry, guard.id, "GUARD", "Reason long enough")
    assert denied.value.status_code == 403

    with pytest.raises(HTTPException) as short_reason:
        service.apply_supervisor_override(db_session, entry, guard.id, "HELPDESK", "no")
    assert short_reason.value.status_code == 400

    with pytest.raises(HTTPException) as cannot_exit:
        service.exit_visitor(db_session, entry, guard.id)
    assert cannot_exit.value.status_code == 409

    overridden = service.apply_supervisor_override(
        db_session, entry, guard.id, "HELPDESK", "Verified exceptional entry"
    )
    assert overridden.status == VisitorStatus.OVERRIDDEN_ADMIT.value
    admitted = service.admit_visitor(db_session, overridden, guard.id)
    assert admitted.status == VisitorStatus.ADMITTED.value
    exited = service.exit_visitor(db_session, admitted, guard.id)
    assert exited.status == VisitorStatus.EXITED.value

    with pytest.raises(HTTPException) as readmit:
        service.admit_visitor(db_session, exited, guard.id)
    assert readmit.value.status_code == 409


def test_guest_credential_verification_rejects_malformed_expired_wrong_gate_and_missing_record(db_session):
    flat, gate, resident, _ = _seed_context(db_session)
    now = datetime.now(UTC)
    malformed = service.verify_guest_code(db_session, gate.id, credential_jwt="not-a-token")
    assert malformed["valid"] is False

    bad_hex = service.verify_guest_code(db_session, gate.id, credential_jwt="zz.ab")
    assert bad_hex["valid"] is False

    expired_payload = _preapproval_payload(flat.id, gate.id, start=now - timedelta(days=2), end=now - timedelta(days=1))
    expired = service.verify_guest_code(db_session, gate.id, credential_jwt=_credential(expired_payload), consume=False)
    assert expired["valid"] is False
    assert "expired" in expired["message"].lower()

    other_gate = db_session.query(Gate).filter(Gate.gate_number == 2).one()
    payload = _preapproval_payload(flat.id, gate.id)
    signed = _credential(payload)
    wrong_gate = service.verify_guest_code(db_session, other_gate.id, credential_jwt=signed)
    assert wrong_gate["valid"] is False
    assert "restricted" in wrong_gate["message"].lower()

    request = PreApprovalCreate(
        flat_id=flat.id,
        guest_name="Missing Record Guest",
        purpose="Test",
        gate_id=gate.id,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=1),
        max_uses=1,
    )
    preapproval, _ = service.create_pre_approval(db_session, request, resident.id)
    db_session.flush()
    valid_credential = preapproval.credential_jwt
    db_session.delete(preapproval)
    db_session.flush()
    missing = service.verify_guest_code(db_session, gate.id, credential_jwt=valid_credential)
    assert missing["valid"] is False
    assert "not an active" in missing["message"]


def test_capture_preapproval_validation_rejects_invalid_states_and_accepts_once(db_session):
    flat, gate, resident, _ = _seed_context(db_session)
    now = datetime.now(UTC)
    assert service._verify_preapproval_at_capture(db_session, gate.id, None, now) == (None, None)
    assert service._verify_preapproval_at_capture(db_session, gate.id, "broken", now)[1]
    assert service._verify_preapproval_at_capture(db_session, gate.id, "aa.bb", now)[1]

    payload = _preapproval_payload(flat.id, gate.id)
    signed = _credential(payload)
    wrong_gate = db_session.query(Gate).filter(Gate.gate_number == 2).one()
    assert "another gate" in service._verify_preapproval_at_capture(db_session, wrong_gate.id, signed, now)[1]
    outside_window = now + timedelta(days=2)
    assert "not valid" in service._verify_preapproval_at_capture(db_session, gate.id, signed, outside_window)[1]

    request = PreApprovalCreate(
        flat_id=flat.id,
        guest_name="Capture Guest",
        purpose="Test capture",
        gate_id=gate.id,
        valid_from=now - timedelta(hours=1),
        valid_until=now + timedelta(hours=1),
        max_uses=1,
    )
    preapproval, _ = service.create_pre_approval(db_session, request, resident.id)
    credential = preapproval.credential_jwt
    accepted, error = service._verify_preapproval_at_capture(db_session, gate.id, credential, now)
    assert accepted is preapproval
    assert error is None
    assert preapproval.used_count == 1
    accepted_again, error_again = service._verify_preapproval_at_capture(db_session, gate.id, credential, now)
    assert accepted_again is None
    assert "use limit" in error_again


def test_signed_time_anchor_rejects_bad_signature_scope_window_and_expired_capture(db_session):
    _, gate, _, guard = _seed_context(db_session)
    now = datetime.now(UTC)
    key = service.get_ecdsa_private_key()

    def make_anchor(
        anchor_time: datetime, *, user_id=guard.id, gate_id=gate.id, device_id="device-1", generation="gen-1"
    ):
        timestamp = int(anchor_time.timestamp())
        payload = {
            "user_id": user_id,
            "gate_id": gate_id,
            "device_id": device_id,
            "device_generation_id": generation,
            "server_time_utc": anchor_time.isoformat(),
            "timestamp_unix": timestamp,
            "valid_until_unix": timestamp + 86400,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        sig = key.sign(raw, ec.ECDSA(hashes.SHA256())).hex()
        return payload, sig

    payload, signature = make_anchor(now)
    with pytest.raises(HTTPException) as bad_sig:
        service.verify_offline_time_anchor(guard.id, gate.id, now, payload, "00", "device-1", "gen-1", now)
    assert bad_sig.value.status_code == 400

    with pytest.raises(HTTPException) as wrong_scope:
        service.verify_offline_time_anchor(guard.id, gate.id, now, payload, signature, "other-device", "gen-1", now)
    assert wrong_scope.value.status_code == 403

    inconsistent = dict(payload)
    inconsistent["timestamp_unix"] += 1
    raw = json.dumps(inconsistent, sort_keys=True, separators=(",", ":")).encode("utf-8")
    inconsistent_sig = key.sign(raw, ec.ECDSA(hashes.SHA256())).hex()
    with pytest.raises(HTTPException) as bad_window:
        service.verify_offline_time_anchor(
            guard.id, gate.id, now, inconsistent, inconsistent_sig, "device-1", "gen-1", now
        )
    assert bad_window.value.status_code == 400

    old_anchor_time = now - timedelta(days=91)
    old_payload, old_signature = make_anchor(old_anchor_time)
    with pytest.raises(HTTPException) as too_old:
        service.verify_offline_time_anchor(
            guard.id,
            gate.id,
            old_anchor_time,
            old_payload,
            old_signature,
            "device-1",
            "gen-1",
            now,
        )
    assert too_old.value.status_code == 410

    future_capture = now + timedelta(minutes=10)
    with pytest.raises(HTTPException) as future:
        service.verify_offline_time_anchor(
            guard.id, gate.id, future_capture, payload, signature, "device-1", "gen-1", now
        )
    assert future.value.status_code == 400


def test_offline_sync_rejects_missing_photo_and_replayed_sequence(db_session):
    from uuid import uuid4

    from backend.app.models.entities import GateDevice
    from backend.app.schemas.visitors import OfflineSyncItem

    flat, gate, _, guard = _seed_context(db_session)
    device_id, generation_id = str(uuid4()), str(uuid4())
    device = GateDevice(
        device_id=device_id,
        generation_id=generation_id,
        gate_id=gate.id,
        enrolled_by_user_id=guard.id,
        is_active=True,
        last_sequence=2,
    )
    db_session.add(device)
    db_session.flush()

    now = datetime.now(UTC)
    timestamp = int(now.timestamp())
    payload = {
        "user_id": guard.id,
        "gate_id": gate.id,
        "device_id": device_id,
        "device_generation_id": generation_id,
        "server_time_utc": now.isoformat(),
        "timestamp_unix": timestamp,
        "valid_until_unix": timestamp + 86400,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = service.get_ecdsa_private_key().sign(raw, ec.ECDSA(hashes.SHA256())).hex()
    photo = _jpeg()
    item = OfflineSyncItem(
        client_event_id=str(uuid4()),
        photo_uuid=str(uuid4()),
        gate_id=gate.id,
        flat_id=flat.id,
        visitor_name="Queued Visitor",
        phone=None,
        purpose="Delivery",
        capture_time=now,
        photo_sha256=hashlib.sha256(photo).hexdigest(),
        device_id=device_id,
        device_generation_id=generation_id,
        device_sequence=1,
        time_anchor_payload=payload,
        time_anchor_signature=signature,
        pre_approval_credential=None,
    )
    with pytest.raises(HTTPException) as missing_photo:
        service.sync_offline_entry_with_photo(db_session, guard.id, item, b"")
    assert missing_photo.value.status_code == 422

    with pytest.raises(HTTPException) as replay:
        service.sync_offline_entry_with_photo(db_session, guard.id, item, photo)
    assert replay.value.status_code == 409


def test_photo_stream_rejects_missing_retention_timestamp_and_expired_photo(monkeypatch):
    from types import SimpleNamespace

    from backend.app.api import visitors as visitor_api

    now = int(datetime.now(UTC).timestamp()) + 120
    entry_id, photo_id = "entry-expiry-test", "photo-expiry-test"
    signature = service.hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{entry_id}:{photo_id}:{now}".encode(),
        service.hashlib.sha256,
    ).hexdigest()

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.result

    class FakeDB:
        def __init__(self, result):
            self.result = result

        def query(self, *_args, **_kwargs):
            return Query(self.result)

    for expiry in (None, datetime.now(UTC) - timedelta(seconds=1)):
        photo = SimpleNamespace(retention_expires_at=expiry, deleted_at=None, storage_key="/missing/photo.jpg")
        with pytest.raises(HTTPException) as unavailable:
            visitor_api.stream_visitor_photo(entry_id, photo_id, now, signature, FakeDB(photo))
        assert unavailable.value.status_code == 404


def test_photo_stream_rejects_deleted_or_missing_storage(monkeypatch):
    from types import SimpleNamespace

    from backend.app.api import visitors as visitor_api

    now = int(datetime.now(UTC).timestamp()) + 120
    entry_id, photo_id = "entry-storage-test", "photo-storage-test"
    signature = service.hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{entry_id}:{photo_id}:{now}".encode(),
        service.hashlib.sha256,
    ).hexdigest()

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, *_args, **_kwargs):
            return self

        def first(self):
            return self.result

    class FakeDB:
        def __init__(self, result):
            self.result = result

        def query(self, *_args, **_kwargs):
            return Query(self.result)

    cases = [
        SimpleNamespace(
            retention_expires_at=datetime.now(UTC) + timedelta(days=1),
            deleted_at=datetime.now(UTC),
            storage_key="/missing/photo.jpg",
        ),
        SimpleNamespace(retention_expires_at=datetime.now(UTC) + timedelta(days=1), deleted_at=None, storage_key=None),
        SimpleNamespace(
            retention_expires_at=datetime.now(UTC) + timedelta(days=1),
            deleted_at=None,
            storage_key="/missing/photo.jpg",
        ),
    ]
    for photo in cases:
        with pytest.raises(HTTPException) as unavailable:
            visitor_api.stream_visitor_photo(entry_id, photo_id, now, signature, FakeDB(photo))
        assert unavailable.value.status_code == 404


def test_guest_code_use_limit_raw_code_and_preapproval_membership_enforcement(db_session):
    flat, gate, resident, guard = _seed_context(db_session)
    now = datetime.now(UTC)

    no_credential = service.verify_guest_code(db_session, gate.id)
    assert no_credential["valid"] is False

    invalid_code = service.verify_guest_code(db_session, gate.id, raw_code="000000")
    assert invalid_code["valid"] is False

    payload = PreApprovalCreate(
        flat_id=flat.id,
        guest_name="Limited Guest",
        purpose="Code branch test",
        gate_id=gate.id,
        valid_from=now - timedelta(minutes=5),
        valid_until=now + timedelta(hours=1),
        max_uses=1,
    )
    preapproval, raw_code = service.create_pre_approval(db_session, payload, resident.id)
    preapproval.used_count = preapproval.max_uses
    db_session.flush()
    exhausted_signed = service.verify_guest_code(
        db_session, gate.id, credential_jwt=preapproval.credential_jwt, consume=False
    )
    assert exhausted_signed["valid"] is False
    assert exhausted_signed["conflict_flagged"] is True

    exhausted_raw = service.verify_guest_code(db_session, gate.id, raw_code=raw_code, consume=False)
    assert exhausted_raw["valid"] is False
    assert "maximum" in exhausted_raw["message"].lower()

    entry = VisitorEntry(
        gate_id=gate.id,
        flat_id=flat.id,
        visitor_name="Already Approved",
        purpose="Override status test",
        status=VisitorStatus.APPROVED.value,
    )
    db_session.add(entry)
    db_session.flush()
    with pytest.raises(HTTPException) as invalid_override_state:
        service.apply_supervisor_override(db_session, entry, guard.id, "HELPDESK", "Cannot override approved")
    assert invalid_override_state.value.status_code == 409

    outsider = db_session.query(User).filter(User.phone == "9876543220").one()
    forbidden_payload = PreApprovalCreate(
        flat_id=flat.id,
        guest_name="Unauthorized Guest",
        purpose="Membership test",
        gate_id=gate.id,
        valid_from=now - timedelta(minutes=5),
        valid_until=now + timedelta(hours=1),
        max_uses=1,
    )
    with pytest.raises(HTTPException) as membership_denied:
        service.create_pre_approval(db_session, forbidden_payload, outsider.id)
    assert membership_denied.value.status_code == 403
