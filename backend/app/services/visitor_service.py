import hashlib
import hmac
import io
import json
import os
import secrets
from datetime import UTC, datetime
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
    FlatMembership,
    PreApproval,
    SupervisorOverride,
    VisitorEntry,
    VisitorEvent,
    VisitorPhoto,
)
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

# In-memory ECDSA P-256 signing key for guest credentials
_ECDSA_PRIVATE_KEY: ec.EllipticCurvePrivateKey | None = None


def get_ecdsa_private_key() -> ec.EllipticCurvePrivateKey:
    global _ECDSA_PRIVATE_KEY
    if _ECDSA_PRIVATE_KEY is None:
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
    base = getattr(settings, "STORAGE_DIR", "private_storage")
    photos_dir = os.path.join(base, "visitor_photos")
    os.makedirs(photos_dir, exist_ok=True)
    return photos_dir


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
            FlatMembership.can_approve_visitors == True,
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
    db: Session, gate_id: str, raw_code: str | None = None, credential_jwt: str | None = None
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
                    PreApproval.flat_id == data["fid"],
                    PreApproval.guest_name == data["name"],
                    PreApproval.is_revoked == False,
                )
                .first()
            )

            conflict = False
            if pre_app:
                if pre_app.used_count >= pre_app.max_uses:
                    conflict = True
                    return {
                        "valid": False,
                        "message": "Guest credential maximum usage limit reached.",
                        "conflict_flagged": True,
                    }
                pre_app.used_count += 1
                db.flush()

            return {
                "valid": True,
                "message": "Offline ECDSA credential successfully verified.",
                "flat_id": data["fid"],
                "guest_name": data["name"],
                "remaining_uses": max(0, data.get("max", 1) - (pre_app.used_count if pre_app else 1)),
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


def sync_offline_entries(db: Session, guard_user_id: str, items: list[OfflineSyncItem]) -> dict[str, Any]:
    """
    Idempotent offline gate sync. Deduplicates by client_event_id UNIQUE.
    Returns processed count, acknowledged IDs, and flagged conflicts.
    """
    acknowledged: list[str] = []
    conflicts: list[dict] = []

    for item in items:
        existing = db.query(VisitorEntry).filter(VisitorEntry.client_event_id == item.client_event_id).first()

        if existing:
            acknowledged.append(item.client_event_id)
            continue

        # Check pre-approval usage if linked
        conflict_flagged = False
        if item.pre_approval_id:
            pre_app = db.query(PreApproval).filter(PreApproval.id == item.pre_approval_id).first()
            if pre_app and pre_app.used_count >= pre_app.max_uses:
                conflict_flagged = True
                conflicts.append(
                    {
                        "client_event_id": item.client_event_id,
                        "reason": f"Guest code {item.pre_approval_id} previously used at another disconnected gate.",
                    }
                )
            elif pre_app:
                pre_app.used_count += 1

        entry = VisitorEntry(
            gate_id=item.gate_id,
            flat_id=item.flat_id,
            visitor_name=item.visitor_name,
            phone=item.phone,
            purpose=item.purpose,
            status=VisitorStatus.APPROVED.value
            if item.pre_approval_id and not conflict_flagged
            else VisitorStatus.AWAITING_APPROVAL.value,
            created_by_guard=guard_user_id,
            pre_approval_id=item.pre_approval_id,
            source="OFFLINE_SYNC",
            client_event_id=item.client_event_id,
            version=1,
            created_at=item.capture_time,
            updated_at=datetime.now(UTC),
        )
        db.add(entry)
        db.flush()

        event = VisitorEvent(
            visitor_entry_id=entry.id,
            actor_user_id=guard_user_id,
            actor_role="GUARD",
            event_type="OFFLINE_SYNC_INGESTED",
            from_status=None,
            to_status=entry.status,
            notes=f"Synced from offline queue. ClientEventId: {item.client_event_id}"
            + (" [CONFLICT]" if conflict_flagged else ""),
        )
        db.add(event)
        acknowledged.append(item.client_event_id)

    db.flush()
    return {
        "processed_count": len(items),
        "acknowledged_ids": acknowledged,
        "conflicts": conflicts,
    }


def purge_visitor_photos(as_of: datetime | None = None, db: Session | None = None) -> int:
    """
    Server-side 90-day retention purge job.
    Deletes photo files and nulls storage_key for all records where retention_expires_at <= as_of.
    Idempotent and accepts an injectable clock.
    """
    cutoff = as_of or datetime.now(UTC)
    from backend.app.core.database import SessionLocal

    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        photos = (
            db.query(VisitorPhoto)
            .filter(VisitorPhoto.deleted_at.is_(None), VisitorPhoto.retention_expires_at <= cutoff)
            .all()
        )

        purged_count = 0
        for photo in photos:
            if photo.storage_key and os.path.exists(photo.storage_key):
                try:
                    os.remove(photo.storage_key)
                except OSError:
                    pass
            photo.storage_key = None
            photo.deleted_at = cutoff
            purged_count += 1

        if purged_count > 0:
            audit = AuditEvent(
                entity_type="VISITOR_PHOTO",
                entity_id="batch",
                action="PURGE_VISITOR_PHOTOS",
                actor_user_id=None,
                actor_role="SYSTEM",
                reason=f"Purged {purged_count} visitor photos exceeding 90-day retention cutoff {cutoff.isoformat()}.",
            )
            db.add(audit)
            db.commit()

        return purged_count

    finally:
        if own_session:
            db.close()
