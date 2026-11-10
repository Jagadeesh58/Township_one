import hashlib
import hmac
import io
import json
import logging
import os
import secrets
from pathlib import Path
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.entities import (
    AuditEvent,
    Flat,
    FlatMembership,
    Gate,
    GateDevice,
    PreApproval,
    SupervisorOverride,
    VisitorEntry,
    VisitorEvent,
    VisitorPhoto,
)
from backend.app.services.storage import delete_private_object, write_private_object
from backend.app.schemas.visitors import (
    OfflineSyncItem,
    PreApprovalCreate,
    VisitorStatus,
)

# Explicit status transitions map
VALID_TRANSITIONS = {
    VisitorStatus.AWAITING_APPROVAL: {
        VisitorStatus.APPROVED,
        VisitorStatus.REJECTED,
        VisitorStatus.OVERRIDDEN_ADMIT,
        VisitorStatus.EXPIRED,
    },
    VisitorStatus.APPROVED: {
        VisitorStatus.ADMITTED,
        VisitorStatus.EXPIRED,
    },
    VisitorStatus.OVERRIDDEN_ADMIT: {
        VisitorStatus.ADMITTED,
    },
    VisitorStatus.ADMITTED: {
        VisitorStatus.EXITED,
    },
    VisitorStatus.REJECTED: set(),
    VisitorStatus.EXITED: set(),
    VisitorStatus.EXPIRED: set(),
}

# Cached key material is loaded from stable configuration or generated only in development.
_ECDSA_PRIVATE_KEY: ec.EllipticCurvePrivateKey | None = None
_logger = logging.getLogger(__name__)


def get_ecdsa_private_key() -> ec.EllipticCurvePrivateKey:
    global _ECDSA_PRIVATE_KEY
    if _ECDSA_PRIVATE_KEY is not None:
        return _ECDSA_PRIVATE_KEY

    pem = settings.SIGNING_KEY.strip()
    key_file = settings.SIGNING_KEY_FILE.strip()
    if key_file:
        try:
            pem = Path(key_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError("Unable to read configured SIGNING_KEY_FILE.") from exc

    if pem:
        pem = pem.replace("\\n", "\n")
        try:
            key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("SIGNING_KEY must contain a valid unencrypted PEM private key.") from exc
        if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
            raise RuntimeError("SIGNING_KEY must be an ECDSA P-256 private key.")
        _ECDSA_PRIVATE_KEY = key
        return key

    if settings.APP_ENV.lower() == "production":
        raise RuntimeError("SIGNING_KEY or SIGNING_KEY_FILE is required in production.")

    _logger.warning("Using an ephemeral development guest-signing key; issued credentials will not survive restart.")
    _ECDSA_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
    return _ECDSA_PRIVATE_KEY


def get_ecdsa_public_key_pem() -> str:
    priv_key = get_ecdsa_private_key()
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return pub_pem.decode("utf-8")


def get_storage_path() -> str:
    """Legacy local visitor-photo directory helper retained for local fixtures."""
    base = getattr(settings, "STORAGE_DIR", "private_storage")
    photos_dir = os.path.join(base, "visitor_photos")
    os.makedirs(photos_dir, exist_ok=True)
    return photos_dir


def visitor_photo_storage_key(photo_id: str) -> str:
    """Return the private object key used by local storage and private object-storage adapters."""
    return f"visitor_photos/{photo_id}.jpg"


def validate_and_process_photo(photo_bytes: bytes, filename: str) -> tuple[str, str, int, bytes]:
    """
    Validates photo with Pillow (JPEG, PNG, WebP; max 5MB; max 4000x4000).
    Strips EXIF/GPS, re-encodes as clean JPEG, and returns (sha256, content_type, size, clean_bytes).
    """
    if len(photo_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Photo file size exceeds maximum permitted limit of 5 MB."
        )

    try:
        image = Image.open(io.BytesIO(photo_bytes))
        image_format = (image.format or "").upper()
        if image_format not in ("JPEG", "JPG", "PNG", "WEBP"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image format. Allowed formats: JPEG, PNG, WebP.",
            )

        width, height = image.size
        if width > 4000 or height > 4000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image dimensions exceed maximum allowed resolution of 4000x4000 pixels.",
            )

        # Convert to RGB and re-encode to strip EXIF and metadata
        rgb_image = image.convert("RGB")
        out_buf = io.BytesIO()
        rgb_image.save(out_buf, format="JPEG", quality=85, optimize=True)
        clean_bytes = out_buf.getvalue()

        sha256_hash = hashlib.sha256(clean_bytes).hexdigest()
        return sha256_hash, "image/jpeg", len(clean_bytes), clean_bytes

    except (OSError, SyntaxError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid image file: {str(exc)}")


def generate_signed_photo_url(visitor_id: str, photo_id: str, expires_in_seconds: int = 300) -> str:
    """Generates an HMAC-SHA256 signed URL valid for at most 5 minutes."""
    expires_at = int(datetime.now(UTC).timestamp()) + min(expires_in_seconds, 300)
    msg = f"{visitor_id}:{photo_id}:{expires_at}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"/api/v1/visitors/{visitor_id}/photo?photo_id={photo_id}&expires={expires_at}&sig={sig}"


def verify_photo_signature(visitor_id: str, photo_id: str, expires: int, sig: str) -> bool:
    now_ts = int(datetime.now(UTC).timestamp())
    if now_ts > expires:
        return False
    msg = f"{visitor_id}:{photo_id}:{expires}".encode()
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)


def transition_visitor_entry(
    db: Session,
    entry: VisitorEntry,
    target_status: VisitorStatus,
    actor_user_id: str | None,
    actor_role: str,
    notes: str | None = None,
) -> VisitorEntry:
    current = VisitorStatus(entry.status)
    if target_status not in VALID_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal state transition from {current.value} to {target_status.value}.",
        )

    old_status = entry.status
    entry.status = target_status.value
    entry.version += 1
    entry.updated_at = datetime.now(UTC)

    # Record append-only event
    event = VisitorEvent(
        visitor_entry_id=entry.id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_type=f"STATUS_TRANSITION_{target_status.value}",
        from_status=old_status,
        to_status=target_status.value,
        notes=notes,
    )
    db.add(event)

    # Record shared AuditEvent
    audit = AuditEvent(
        entity_type="VISITOR_ENTRY",
        entity_id=entry.id,
        action=f"VISITOR_{target_status.value}",
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        old_state={"status": old_status},
        new_state={"status": target_status.value},
        reason=notes or f"Transitioned from {old_status} to {target_status.value}",
    )
    db.add(audit)
    db.flush()
    return entry


def admit_visitor(db: Session, entry: VisitorEntry, guard_user_id: str) -> VisitorEntry:
    current = VisitorStatus(entry.status)
    if current not in (VisitorStatus.APPROVED, VisitorStatus.OVERRIDDEN_ADMIT):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot admit visitor with status '{current.value}'. Requires APPROVED or OVERRIDDEN_ADMIT.",
        )
    entry.admitted_at = datetime.now(UTC)
    return transition_visitor_entry(
        db, entry, VisitorStatus.ADMITTED, guard_user_id, "GUARD", "Visitor admitted at gate"
    )


def exit_visitor(db: Session, entry: VisitorEntry, guard_user_id: str) -> VisitorEntry:
    current = VisitorStatus(entry.status)
    if current != VisitorStatus.ADMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot exit visitor with status '{current.value}'. Visitor must currently be ADMITTED.",
        )
    entry.exited_at = datetime.now(UTC)
    return transition_visitor_entry(db, entry, VisitorStatus.EXITED, guard_user_id, "GUARD", "Visitor exited township")


def apply_supervisor_override(
    db: Session, entry: VisitorEntry, supervisor_user_id: str, supervisor_role: str, reason: str
) -> VisitorEntry:
    if supervisor_role not in ("HELPDESK", "HELP_DESK", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor override requires HELPDESK or ADMIN privileges."
        )
    if not reason or len(reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supervisor override requires an explicit, meaningful reason.",
        )

    current = VisitorStatus(entry.status)
    if current != VisitorStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Supervisor override can only be applied to AWAITING_APPROVAL entries, currently {current.value}.",
        )

    # Insert supervisor override record
    override = SupervisorOverride(
        visitor_entry_id=entry.id,
        actor_user_id=supervisor_user_id,
        reason=reason.strip(),
        override_type="OVERRIDDEN_ADMIT",
    )
    db.add(override)

    entry = transition_visitor_entry(
        db,
        entry,
        VisitorStatus.OVERRIDDEN_ADMIT,
        supervisor_user_id,
        supervisor_role,
        notes=f"SUPERVISOR OVERRIDE: {reason.strip()}",
    )
    return entry


def hash_pre_approval_code(raw_code: str, salt: str | None = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    code_hash = hashlib.sha256(f"{raw_code}:{salt}".encode()).hexdigest()
    return f"{salt}:{code_hash}"


def create_pre_approval(db: Session, payload: PreApprovalCreate, creator_user_id: str) -> tuple[PreApproval, str]:
    # Verify creator membership on flat
    membership = (
        db.query(FlatMembership)
        .filter(
            FlatMembership.flat_id == payload.flat_id,
            FlatMembership.user_id == creator_user_id,
            FlatMembership.can_approve_visitors.is_(True),
            FlatMembership.is_active.is_(True),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not hold visitor approval permission for this flat.",
        )

    # Generate 6-digit random guest code and compute salted SHA-256
    raw_code = f"{secrets.randbelow(900000) + 100000}"
    stored_verifier = hash_pre_approval_code(raw_code)

    # Sign compact offline credential with ECDSA P-256
    cred_id = secrets.token_hex(16)
    cred_payload = {
        "cid": cred_id,
        "fid": payload.flat_id,
        "name": payload.guest_name,
        "from": payload.valid_from.isoformat(),
        "until": payload.valid_until.isoformat(),
        "gate": payload.gate_id,
        "max": payload.max_uses,
    }
    payload_bytes = json.dumps(cred_payload, sort_keys=True).encode("utf-8")
    priv_key = get_ecdsa_private_key()
    signature = priv_key.sign(payload_bytes, ec.ECDSA(hashes.SHA256()))
    sig_hex = signature.hex()
    compact_token = f"{payload_bytes.hex()}.{sig_hex}"

    pre_app = PreApproval(
        flat_id=payload.flat_id,
        created_by_user_id=creator_user_id,
        guest_name=payload.guest_name,
        phone=payload.phone,
        purpose=payload.purpose,
        gate_id=payload.gate_id,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        max_uses=payload.max_uses,
        used_count=0,
        code_hash=stored_verifier,
        credential_jwt=compact_token,
        is_revoked=False,
    )
    db.add(pre_app)
    db.flush()

    return pre_app, raw_code


def verify_guest_code(
    db: Session,
    gate_id: str,
    raw_code: str | None = None,
    credential_jwt: str | None = None,
    *,
    consume: bool = True,
) -> dict[str, Any]:
    now = datetime.now(UTC)

    # 1. Verification via offline ECDSA compact credential
    if credential_jwt:
        parts = credential_jwt.split(".")
        if len(parts) != 2:
            return {"valid": False, "message": "Malformed offline credential format."}

        try:
            payload_bytes = bytes.fromhex(parts[0])
            sig_bytes = bytes.fromhex(parts[1])
            data = json.loads(payload_bytes.decode("utf-8"))

            priv_key = get_ecdsa_private_key()
            pub_key = priv_key.public_key()
            pub_key.verify(sig_bytes, payload_bytes, ec.ECDSA(hashes.SHA256()))

            valid_from = datetime.fromisoformat(data["from"])
            valid_until = datetime.fromisoformat(data["until"])

            if now < valid_from or now > valid_until:
                return {"valid": False, "message": "Offline guest credential has expired."}

            if data.get("gate") and data["gate"] != gate_id:
                return {"valid": False, "message": f"Credential is restricted to gate {data['gate']}."}

            # Check database state if online
            pre_app = (
                db.query(PreApproval)
                .filter(
                    PreApproval.credential_jwt == credential_jwt,
                    PreApproval.flat_id == data["fid"],
                    PreApproval.is_revoked.is_(False),
                )
                .first()
            )

            conflict = False
            if not pre_app:
                return {"valid": False, "message": "Credential is not an active server-issued pre-approval."}
            if pre_app.gate_id and pre_app.gate_id != gate_id:
                return {"valid": False, "message": "Credential is restricted to another gate."}
            if pre_app.used_count >= pre_app.max_uses:
                conflict = True
                return {
                    "valid": False,
                    "message": "Guest credential maximum usage limit reached.",
                    "conflict_flagged": True,
                }
            if consume:
                pre_app.used_count += 1
                db.flush()

            return {
                "valid": True,
                "message": "Offline ECDSA credential successfully verified.",
                "pre_approval_id": pre_app.id,
                "flat_id": data["fid"],
                "guest_name": data["name"],
                "remaining_uses": max(0, pre_app.max_uses - pre_app.used_count),
                "conflict_flagged": conflict,
            }

        except (InvalidSignature, ValueError, KeyError) as exc:
            return {"valid": False, "message": f"Cryptographic verification failed: {str(exc)}"}

    # 2. Verification via online 6-digit code
    if raw_code:
        candidates = (
            db.query(PreApproval)
            .filter(PreApproval.is_revoked == False, PreApproval.valid_from <= now, PreApproval.valid_until >= now)
            .all()
        )

        matched: PreApproval | None = None
        for cand in candidates:
            if ":" in cand.code_hash:
                salt, expected_hash = cand.code_hash.split(":", 1)
                computed = hashlib.sha256(f"{raw_code}:{salt}".encode()).hexdigest()
                if hmac.compare_digest(computed, expected_hash):
                    matched = cand
                    break

        if not matched:
            return {"valid": False, "message": "Invalid or expired guest code."}

        if matched.gate_id and matched.gate_id != gate_id:
            return {"valid": False, "message": "Guest code is not authorized for entry at this gate."}

        if matched.used_count >= matched.max_uses:
            return {"valid": False, "message": "Guest code has already reached maximum allowed uses."}

        if consume:
            matched.used_count += 1
            db.flush()

        return {
            "valid": True,
            "message": "Guest code verified successfully.",
            "pre_approval_id": matched.id,
            "flat_id": matched.flat_id,
            "guest_name": matched.guest_name,
            "remaining_uses": matched.max_uses - matched.used_count,
            "conflict_flagged": False,
        }

    return {"valid": False, "message": "Either raw guest code or offline credential token must be provided."}


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def verify_offline_time_anchor(
    user_id: str,
    gate_id: str,
    capture_time: datetime,
    anchor_payload: dict[str, Any],
    anchor_signature: str,
    device_id: str,
    device_generation_id: str,
    now: datetime | None = None,
) -> None:
    """Verify that capture metadata is bounded by a server-signed gate time anchor."""
    try:
        payload_bytes = json.dumps(anchor_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature_bytes = bytes.fromhex(anchor_signature)
        get_ecdsa_private_key().public_key().verify(signature_bytes, payload_bytes, ec.ECDSA(hashes.SHA256()))
        anchor_time = datetime.fromisoformat(str(anchor_payload["server_time_utc"]).replace("Z", "+00:00"))
        anchor_time = _as_utc(anchor_time)
        capture_time = _as_utc(capture_time)
        now = _as_utc(now or datetime.now(UTC))
        anchor_timestamp = int(anchor_payload["timestamp_unix"])
        anchor_valid_until = int(anchor_payload["valid_until_unix"])
    except (InvalidSignature, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Offline capture time anchor is invalid.") from exc

    if (
        anchor_payload.get("user_id") != user_id
        or anchor_payload.get("gate_id") != gate_id
        or anchor_payload.get("device_id") != device_id
        or anchor_payload.get("device_generation_id") != device_generation_id
    ):
        raise HTTPException(status_code=403, detail="Offline time anchor belongs to another guard, gate or device generation.")
    if int(anchor_time.timestamp()) != anchor_timestamp or anchor_valid_until <= anchor_timestamp:
        raise HTTPException(status_code=400, detail="Offline time anchor payload is inconsistent.")
    capture_ts = int(capture_time.timestamp())
    if capture_ts < anchor_timestamp - 300 or capture_ts > anchor_valid_until + 300:
        raise HTTPException(status_code=400, detail="Capture time falls outside the signed gate time window.")
    if capture_time > now + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Capture time cannot be in the future.")
    if capture_time < now - timedelta(days=90):
        raise HTTPException(status_code=410, detail="Visitor photograph is beyond the 90-day retention limit.")


def _verify_preapproval_at_capture(
    db: Session, gate_id: str, credential: str | None, capture_time: datetime
) -> tuple[PreApproval | None, str | None]:
    if not credential:
        return None, None
    parts = credential.split(".")
    if len(parts) != 2:
        return None, "Malformed pre-approval credential."
    try:
        payload_bytes = bytes.fromhex(parts[0])
        signature_bytes = bytes.fromhex(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
        get_ecdsa_private_key().public_key().verify(signature_bytes, payload_bytes, ec.ECDSA(hashes.SHA256()))
        start = _as_utc(datetime.fromisoformat(payload["from"]))
        end = _as_utc(datetime.fromisoformat(payload["until"]))
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return None, "Pre-approval signature is invalid."

    if payload.get("gate") and payload["gate"] != gate_id:
        return None, "Pre-approval is restricted to another gate."
    capture_time = _as_utc(capture_time)
    if not start <= capture_time <= end:
        return None, "Pre-approval was not valid at the recorded capture time."
    preapproval = db.query(PreApproval).filter(PreApproval.credential_jwt == credential).with_for_update().first()
    if not preapproval or preapproval.is_revoked:
        return None, "Pre-approval is no longer active on the server."
    if preapproval.gate_id and preapproval.gate_id != gate_id:
        return None, "Pre-approval gate does not match the visitor event."
    if preapproval.used_count >= preapproval.max_uses:
        return None, "Pre-approval use limit has already been reached."
    if preapproval.flat_id != payload.get("fid") or preapproval.guest_name != payload.get("name"):
        return None, "Pre-approval details do not match the signed credential."
    preapproval.used_count += 1
    db.flush()
    return preapproval, None


def sync_offline_entry_with_photo(
    db: Session,
    guard_user_id: str,
    item: OfflineSyncItem,
    photo_bytes: bytes,
) -> dict[str, Any]:
    """Atomically accept one offline event with its actual, hash-verified photograph."""
    from pathlib import Path

    now = datetime.now(UTC)
    if not photo_bytes:
        raise HTTPException(status_code=422, detail="Offline visitor photo is required.")
    raw_hash = hashlib.sha256(photo_bytes).hexdigest()
    if not hmac.compare_digest(raw_hash.lower(), item.photo_sha256.lower()):
        raise HTTPException(status_code=422, detail="Offline visitor photo SHA-256 does not match metadata.")
    capture_time = _as_utc(item.capture_time)
    verify_offline_time_anchor(
        guard_user_id, item.gate_id, capture_time,
        item.time_anchor_payload, item.time_anchor_signature,
        item.device_id, item.device_generation_id, now,
    )

    clean_hash, content_type, file_size, clean_bytes = validate_and_process_photo(
        photo_bytes, f"{item.photo_uuid}.upload"
    )
    existing = db.query(VisitorEntry).filter(VisitorEntry.client_event_id == item.client_event_id).first()
    if existing:
        existing_photo = db.query(VisitorPhoto).filter(VisitorPhoto.id == existing.photo_id).first()
        if existing_photo and existing_photo.client_photo_id == item.photo_uuid and hmac.compare_digest(
            existing_photo.sha256, clean_hash
        ):
            return {"processed_count": 0, "acknowledged_ids": [item.client_event_id], "conflicts": []}
        raise HTTPException(status_code=409, detail="Event UUID was previously used with different photo data.")

    device = (
        db.query(GateDevice)
        .filter(
            GateDevice.device_id == item.device_id,
            GateDevice.generation_id == item.device_generation_id,
            GateDevice.gate_id == item.gate_id,
            GateDevice.is_active.is_(True),
        )
        .with_for_update()
        .first()
    )
    if not device:
        raise HTTPException(status_code=403, detail="Gate device is not enrolled for this gate generation.")
    if item.device_sequence <= device.last_sequence:
        raise HTTPException(status_code=409, detail="Gate device sequence is stale or has already been used.")

    duplicate_photo = db.query(VisitorPhoto).filter(VisitorPhoto.client_photo_id == item.photo_uuid).first()
    if duplicate_photo:
        raise HTTPException(status_code=409, detail="Photo UUID has already been used by another event.")
    sequence_replay = (
        db.query(VisitorEntry)
        .filter(
            VisitorEntry.device_id == item.device_id,
            VisitorEntry.device_generation_id == item.device_generation_id,
            VisitorEntry.device_sequence == item.device_sequence,
        )
        .first()
    )
    if sequence_replay:
        raise HTTPException(status_code=409, detail="Gate device sequence has already been used.")

    preapproval, preapproval_error = _verify_preapproval_at_capture(
        db, item.gate_id, item.pre_approval_credential, capture_time
    )
    status_value = VisitorStatus.APPROVED.value if preapproval else VisitorStatus.AWAITING_APPROVAL.value

    photo = VisitorPhoto(
        client_photo_id=item.photo_uuid,
        sha256=clean_hash,
        capture_time=capture_time,
        content_type=content_type,
        size=file_size,
        retention_expires_at=capture_time + timedelta(days=90),
    )
    db.add(photo)
    db.flush()
    storage_key = visitor_photo_storage_key(photo.id)
    try:
        write_private_object(storage_key, clean_bytes, content_type)
        photo.storage_key = storage_key
        entry = VisitorEntry(
            gate_id=item.gate_id,
            flat_id=item.flat_id,
            visitor_name=item.visitor_name,
            phone=item.phone,
            purpose=item.purpose,
            status=status_value,
            created_by_guard=guard_user_id,
            photo_id=photo.id,
            pre_approval_id=preapproval.id if preapproval else None,
            source="OFFLINE_SYNC",
            client_event_id=item.client_event_id,
            device_id=item.device_id,
            device_generation_id=item.device_generation_id,
            device_sequence=item.device_sequence,
            version=1,
            created_at=capture_time,
            updated_at=now,
        )
        db.add(entry)
        device.last_sequence = item.device_sequence
        device.last_seen_at = now
        db.flush()
        db.add(
            VisitorEvent(
                visitor_entry_id=entry.id,
                actor_user_id=guard_user_id,
                actor_role="GUARD",
                event_type="OFFLINE_SYNC_ACCEPTED",
                from_status=None,
                to_status=status_value,
                notes=(
                    f"Offline event {item.client_event_id} accepted with verified photo."
                    + (f" Pre-approval held: {preapproval_error}" if preapproval_error else "")
                ),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        try:
            delete_private_object(storage_key)
        except Exception:
            _logger.exception("Unable to remove an uncommitted visitor photo after sync failure.")
        raise

    return {
        "processed_count": 1,
        "acknowledged_ids": [item.client_event_id],
        "conflicts": ([{"client_event_id": item.client_event_id, "reason": preapproval_error}]
                      if preapproval_error else []),
    }


def purge_visitor_photos(as_of: datetime | None = None, db: Session | None = None) -> int:
    """Delete due visitor photos and mark only verified deletions as deleted."""
    cutoff = _as_utc(as_of or datetime.now(UTC))
    from backend.app.core.database import SessionLocal

    own_session = db is None
    if own_session:
        db = SessionLocal()
    assert db is not None
    try:
        photos = (
            db.query(VisitorPhoto)
            .filter(VisitorPhoto.deleted_at.is_(None), VisitorPhoto.retention_expires_at <= cutoff)
            .all()
        )
        purged_count = 0
        failures: list[str] = []
        for photo in photos:
            try:
                if photo.storage_key:
                    delete_private_object(photo.storage_key)
                photo.storage_key = None
                photo.deleted_at = cutoff
                purged_count += 1
                db.flush()
            except OSError as exc:
                failures.append(f"{photo.id}: {exc}")
                db.expire(photo)

        if purged_count or failures:
            db.add(
                AuditEvent(
                    entity_type="VISITOR_PHOTO",
                    entity_id="batch",
                    action="PURGE_VISITOR_PHOTOS",
                    actor_user_id=None,
                    actor_role="SYSTEM",
                    reason=(
                        f"Verified deletions: {purged_count}; failed deletions: {len(failures)}; "
                        f"cutoff: {cutoff.isoformat()}. " + "; ".join(failures[:10])
                    ),
                )
            )
        db.commit()
        return purged_count
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()
