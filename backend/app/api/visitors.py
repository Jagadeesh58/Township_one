import json
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import (
    Flat,
    FlatMembership,
    Gate,
    GateDevice,
    PreApproval,
    Tower,
    User,
    VisitorEntry,
    VisitorPhoto,
)
from backend.app.schemas.visitors import (
    GateDeviceEnrollmentRequest,
    GateDeviceEnrollmentResponse,
    GuestCodeVerifyRequest,
    GuestCodeVerifyResponse,
    OfflineSyncItem,
    OfflineSyncResponse,
    PreApprovalCreate,
    PreApprovalResponse,
    SupervisorOverrideRequest,
    VisitorApprovalDecision,
    VisitorEntryCreate,
    VisitorEntryResponse,
    VisitorStatus,
)
from backend.app.services.storage import delete_private_object, read_private_object, write_private_object
from backend.app.services.visitor_service import (
    admit_visitor,
    apply_supervisor_override,
    create_pre_approval,
    exit_visitor,
    generate_signed_photo_url,
    get_ecdsa_private_key,
    get_ecdsa_public_key_pem,
    sync_offline_entry_with_photo,
    transition_visitor_entry,
    validate_and_process_photo,
    verify_guest_code,
    verify_photo_signature,
    visitor_photo_storage_key,
)

router = APIRouter(prefix="/visitors", tags=["visitors"])


@router.get("/gates")
def list_guard_gates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = set(get_user_roles(current_user))
    if "ADMIN" in roles:
        query = db.query(Gate)
    elif "GUARD" in roles:
        assigned = get_guard_assigned_gate_ids(current_user)
        if not assigned:
            raise HTTPException(status_code=403, detail="No active gate assignment is configured for this guard.")
        query = db.query(Gate).filter(Gate.id.in_(assigned))
    else:
        raise HTTPException(status_code=403, detail="Gate operator access is required.")
    return [
        {"id": gate.id, "gate_number": gate.gate_number, "name": gate.name, "description": gate.location_description}
        for gate in query.order_by(Gate.gate_number).all()
    ]


def get_user_roles(user: User) -> list[str]:
    if user.is_active is False:
        return []
    return [r.role_code for r in user.role_assignments if r.is_active is True]


def get_guard_assigned_gate_ids(user: User) -> set[str]:
    return {
        r.scope_id
        for r in user.role_assignments
        if r.is_active is True and r.role_code == "GUARD" and r.scope_type == "GATE" and r.scope_id
    }


def enforce_guard_gate_scope(user: User, gate_id: str) -> None:
    roles = set(get_user_roles(user))
    if "ADMIN" in roles:
        return
    assigned_gates = get_guard_assigned_gate_ids(user)
    if "GUARD" not in roles or not assigned_gates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active guard role with an assigned gate is required.",
        )
    if gate_id not in assigned_gates:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This guard is not assigned to the requested gate.",
        )


def active_visitor_membership(db: Session, user_id: str, flat_id: str) -> FlatMembership | None:
    return (
        db.query(FlatMembership)
        .filter(
            FlatMembership.user_id == user_id,
            FlatMembership.flat_id == flat_id,
            FlatMembership.is_active.is_(True),
            FlatMembership.can_approve_visitors.is_(True),
        )
        .first()
    )


@router.get("/entries", response_model=list[VisitorEntryResponse])
def list_visitor_entries(
    gate_id: str | None = Query(None),
    flat_id: str | None = Query(None),
    status_filter: VisitorStatus | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    query = db.query(VisitorEntry)

    # Scoping:
    # 1. Guards see entries at their selected gate
    if "GUARD" in roles and "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles:
        if not gate_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Guard must specify a gate_id to view entries."
            )
        enforce_guard_gate_scope(current_user, gate_id)
        query = query.filter(VisitorEntry.gate_id == gate_id)

    # 2. Residents see only entries for flats they belong to
    elif "RESIDENT" in roles and "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles:
        user_flat_ids = [
            m.flat_id for m in current_user.flat_memberships if m.is_active is True and m.can_approve_visitors is True
        ]
        if not user_flat_ids:
            return []
        query = query.filter(VisitorEntry.flat_id.in_(user_flat_ids))
        if flat_id and flat_id in user_flat_ids:
            query = query.filter(VisitorEntry.flat_id == flat_id)

    # 3. Staff / Admin can filter by flat or gate
    else:
        if gate_id:
            query = query.filter(VisitorEntry.gate_id == gate_id)
        if flat_id:
            query = query.filter(VisitorEntry.flat_id == flat_id)

    if status_filter:
        query = query.filter(VisitorEntry.status == status_filter.value)

    entries = query.order_by(VisitorEntry.created_at.desc()).limit(100).all()

    # Enrich with flat number, tower, photo signed URL
    result = []
    for entry in entries:
        flat = db.query(Flat).filter(Flat.id == entry.flat_id).first()
        tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None

        photo_url = None
        if entry.photo_id:
            photo_url = generate_signed_photo_url(entry.id, entry.photo_id)

        result.append(
            VisitorEntryResponse(
                id=entry.id,
                gate_id=entry.gate_id,
                flat_id=entry.flat_id,
                flat_number=flat.flat_number if flat else None,
                tower_number=tower.code if tower else None,
                visitor_name=entry.visitor_name,
                phone=entry.phone,
                purpose=entry.purpose,
                status=VisitorStatus(entry.status),
                created_by_guard=entry.created_by_guard,
                approval_decided_by=entry.approval_decided_by,
                approval_decided_at=entry.approval_decided_at,
                admitted_at=entry.admitted_at,
                exited_at=entry.exited_at,
                photo_id=entry.photo_id,
                photo_url=photo_url,
                pre_approval_id=entry.pre_approval_id,
                source=entry.source,
                client_event_id=entry.client_event_id,
                version=entry.version,
                created_at=entry.created_at,
            )
        )

    return result


@router.post("/entries", response_model=VisitorEntryResponse, status_code=status.HTTP_201_CREATED)
def create_visitor_entry(
    payload: VisitorEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only guards or administrators can record visitor arrival."
        )

    enforce_guard_gate_scope(current_user, payload.gate_id)

    flat = db.query(Flat).filter(Flat.id == payload.flat_id).first()
    if not flat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified flat does not exist.")

    gate = db.query(Gate).filter(Gate.id == payload.gate_id).first()
    if not gate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified gate does not exist.")

    # Check client_event_id deduplication
    if payload.client_event_id:
        existing = db.query(VisitorEntry).filter(VisitorEntry.client_event_id == payload.client_event_id).first()
        if existing:
            return existing

    pre_approval_id = None
    entry_status = VisitorStatus.AWAITING_APPROVAL.value
    if payload.guest_code or payload.pre_approval_credential:
        verification = verify_guest_code(
            db,
            payload.gate_id,
            payload.guest_code,
            payload.pre_approval_credential,
            consume=True,
        )
        if not verification.get("valid"):
            db.rollback()
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=verification.get("message"))
        if verification.get("flat_id") != payload.flat_id:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Guest credential does not match the selected flat.",
            )
        if str(verification.get("guest_name", "")).strip().casefold() != payload.visitor_name.strip().casefold():
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Guest credential does not match the visitor name.",
            )
        pre_approval_id = verification.get("pre_approval_id")
        entry_status = VisitorStatus.APPROVED.value

    entry = VisitorEntry(
        gate_id=payload.gate_id,
        flat_id=payload.flat_id,
        visitor_name=payload.visitor_name,
        phone=payload.phone,
        purpose=payload.purpose,
        status=entry_status,
        created_by_guard=current_user.id,
        photo_id=payload.photo_id,
        pre_approval_id=pre_approval_id,
        source=payload.source,
        client_event_id=payload.client_event_id,
        version=1,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None
    photo_url = generate_signed_photo_url(entry.id, entry.photo_id) if entry.photo_id else None

    return VisitorEntryResponse(
        id=entry.id,
        gate_id=entry.gate_id,
        flat_id=entry.flat_id,
        flat_number=flat.flat_number,
        tower_number=tower.code if tower else None,
        visitor_name=entry.visitor_name,
        phone=entry.phone,
        purpose=entry.purpose,
        status=VisitorStatus(entry.status),
        created_by_guard=entry.created_by_guard,
        approval_decided_by=entry.approval_decided_by,
        approval_decided_at=entry.approval_decided_at,
        admitted_at=entry.admitted_at,
        exited_at=entry.exited_at,
        photo_id=entry.photo_id,
        photo_url=photo_url,
        pre_approval_id=entry.pre_approval_id,
        source=entry.source,
        client_event_id=entry.client_event_id,
        version=entry.version,
        created_at=entry.created_at,
    )


@router.post("/{entry_id}/approval", response_model=VisitorEntryResponse)
def decide_visitor_approval(
    entry_id: str,
    decision_payload: VisitorApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(VisitorEntry).filter(VisitorEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found.")

    # Server-side authorization: User must belong to this flat with approval permission
    membership = active_visitor_membership(db, current_user.id, entry.flat_id)

    roles = get_user_roles(current_user)
    if not membership and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to approve visitors for this flat.",
        )

    target_status = VisitorStatus.APPROVED if decision_payload.decision == "APPROVE" else VisitorStatus.REJECTED
    entry.approval_decided_by = current_user.id
    entry.approval_decided_at = datetime.now(UTC)

    transition_visitor_entry(
        db,
        entry,
        target_status,
        current_user.id,
        "RESIDENT" if membership else "ADMIN",
        notes=f"Resident {decision_payload.decision.lower()}d visitor arrival.",
    )
    db.commit()
    db.refresh(entry)

    flat = db.query(Flat).filter(Flat.id == entry.flat_id).first()
    tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None
    photo_url = generate_signed_photo_url(entry.id, entry.photo_id) if entry.photo_id else None

    return VisitorEntryResponse(
        id=entry.id,
        gate_id=entry.gate_id,
        flat_id=entry.flat_id,
        flat_number=flat.flat_number if flat else None,
        tower_number=tower.code if tower else None,
        visitor_name=entry.visitor_name,
        phone=entry.phone,
        purpose=entry.purpose,
        status=VisitorStatus(entry.status),
        created_by_guard=entry.created_by_guard,
        approval_decided_by=entry.approval_decided_by,
        approval_decided_at=entry.approval_decided_at,
        admitted_at=entry.admitted_at,
        exited_at=entry.exited_at,
        photo_id=entry.photo_id,
        photo_url=photo_url,
        pre_approval_id=entry.pre_approval_id,
        source=entry.source,
        client_event_id=entry.client_event_id,
        version=entry.version,
        created_at=entry.created_at,
    )


@router.post("/{entry_id}/admit", response_model=VisitorEntryResponse)
def admit_visitor_endpoint(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only on-duty guards can admit visitors.")

    entry = db.query(VisitorEntry).filter(VisitorEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found.")

    enforce_guard_gate_scope(current_user, entry.gate_id)

    admit_visitor(db, entry, current_user.id)
    db.commit()
    db.refresh(entry)

    flat = db.query(Flat).filter(Flat.id == entry.flat_id).first()
    tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None
    photo_url = generate_signed_photo_url(entry.id, entry.photo_id) if entry.photo_id else None

    return VisitorEntryResponse(
        id=entry.id,
        gate_id=entry.gate_id,
        flat_id=entry.flat_id,
        flat_number=flat.flat_number if flat else None,
        tower_number=tower.code if tower else None,
        visitor_name=entry.visitor_name,
        phone=entry.phone,
        purpose=entry.purpose,
        status=VisitorStatus(entry.status),
        created_by_guard=entry.created_by_guard,
        approval_decided_by=entry.approval_decided_by,
        approval_decided_at=entry.approval_decided_at,
        admitted_at=entry.admitted_at,
        exited_at=entry.exited_at,
        photo_id=entry.photo_id,
        photo_url=photo_url,
        pre_approval_id=entry.pre_approval_id,
        source=entry.source,
        client_event_id=entry.client_event_id,
        version=entry.version,
        created_at=entry.created_at,
    )


@router.post("/{entry_id}/exit", response_model=VisitorEntryResponse)
def exit_visitor_endpoint(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only on-duty guards can record visitor exit."
        )

    entry = db.query(VisitorEntry).filter(VisitorEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found.")

    enforce_guard_gate_scope(current_user, entry.gate_id)

    exit_visitor(db, entry, current_user.id)
    db.commit()
    db.refresh(entry)

    flat = db.query(Flat).filter(Flat.id == entry.flat_id).first()
    tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None
    photo_url = generate_signed_photo_url(entry.id, entry.photo_id) if entry.photo_id else None

    return VisitorEntryResponse(
        id=entry.id,
        gate_id=entry.gate_id,
        flat_id=entry.flat_id,
        flat_number=flat.flat_number if flat else None,
        tower_number=tower.code if tower else None,
        visitor_name=entry.visitor_name,
        phone=entry.phone,
        purpose=entry.purpose,
        status=VisitorStatus(entry.status),
        created_by_guard=entry.created_by_guard,
        approval_decided_by=entry.approval_decided_by,
        approval_decided_at=entry.approval_decided_at,
        admitted_at=entry.admitted_at,
        exited_at=entry.exited_at,
        photo_id=entry.photo_id,
        photo_url=photo_url,
        pre_approval_id=entry.pre_approval_id,
        source=entry.source,
        client_event_id=entry.client_event_id,
        version=entry.version,
        created_at=entry.created_at,
    )


@router.post("/{entry_id}/override", response_model=VisitorEntryResponse)
def supervisor_override_endpoint(
    entry_id: str,
    payload: SupervisorOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    matching_role = (
        "ADMIN" if "ADMIN" in roles else ("HELPDESK" if ("HELPDESK" in roles or "HELP_DESK" in roles) else None)
    )
    if not matching_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor override requires HELPDESK or ADMIN privileges."
        )

    entry = db.query(VisitorEntry).filter(VisitorEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found.")

    apply_supervisor_override(db, entry, current_user.id, matching_role, payload.reason)
    db.commit()
    db.refresh(entry)

    flat = db.query(Flat).filter(Flat.id == entry.flat_id).first()
    tower = db.query(Tower).filter(Tower.id == flat.tower_id).first() if flat else None
    photo_url = generate_signed_photo_url(entry.id, entry.photo_id) if entry.photo_id else None

    return VisitorEntryResponse(
        id=entry.id,
        gate_id=entry.gate_id,
        flat_id=entry.flat_id,
        flat_number=flat.flat_number if flat else None,
        tower_number=tower.code if tower else None,
        visitor_name=entry.visitor_name,
        phone=entry.phone,
        purpose=entry.purpose,
        status=VisitorStatus(entry.status),
        created_by_guard=entry.created_by_guard,
        approval_decided_by=entry.approval_decided_by,
        approval_decided_at=entry.approval_decided_at,
        admitted_at=entry.admitted_at,
        exited_at=entry.exited_at,
        photo_id=entry.photo_id,
        photo_url=photo_url,
        pre_approval_id=entry.pre_approval_id,
        source=entry.source,
        client_event_id=entry.client_event_id,
        version=entry.version,
        created_at=entry.created_at,
    )


@router.post("/photo/upload")
async def upload_visitor_photo(
    file: UploadFile = File(...),
    gate_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only guards or admins can upload visitor photos."
        )

    enforce_guard_gate_scope(current_user, gate_id)
    content = await file.read()
    sha256_hash, content_type, file_size, clean_bytes = validate_and_process_photo(
        content, file.filename or "photo.jpg"
    )

    now = datetime.now(UTC)
    retention_expires_at = now + timedelta(days=90)

    photo = VisitorPhoto(
        sha256=sha256_hash,
        capture_time=now,
        content_type=content_type,
        size=file_size,
        retention_expires_at=retention_expires_at,
    )
    db.add(photo)
    db.flush()

    # Persist in the configured private object store; never write uploads to the web root.
    storage_key = visitor_photo_storage_key(photo.id)
    try:
        write_private_object(storage_key, clean_bytes, content_type)
        photo.storage_key = storage_key
        db.commit()
    except Exception:
        db.rollback()
        try:
            delete_private_object(storage_key)
        except Exception:
            pass
        raise

    return {
        "photo_id": photo.id,
        "sha256": sha256_hash,
        "capture_time": now.isoformat(),
        "retention_expires_at": retention_expires_at.isoformat(),
        "data_protection_notice": "Visitor photograph collected for security logging and automatically purged after 90 days.",
    }


@router.get("/{entry_id}/photo")
def stream_visitor_photo(
    entry_id: str,
    photo_id: str = Query(...),
    expires: int = Query(...),
    sig: str = Query(...),
    db: Session = Depends(get_db),
):
    if not verify_photo_signature(entry_id, photo_id, expires, sig):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Invalid or expired photo signature."
        )

    photo = db.query(VisitorPhoto).filter(VisitorPhoto.id == photo_id).first()
    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photograph file not found or retention period expired."
        )

    expiry = photo.retention_expires_at
    if expiry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photograph file not found or retention period expired.",
        )
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if photo.deleted_at is not None or expiry <= datetime.now(UTC) or not photo.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photograph file not found or retention period expired."
        )
    content = read_private_object(photo.storage_key)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photograph file not found or retention period expired."
        )
    return Response(
        content, media_type=photo.content_type or "image/jpeg", headers={"Cache-Control": "private, no-store"}
    )


# =========================================================================
# Pre-Approvals & Offline Guest Code Endpoints
# =========================================================================


@router.post("/pre-approvals", response_model=PreApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_pre_approval_endpoint(
    payload: PreApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pre_app, raw_code = create_pre_approval(db, payload, current_user.id)
    db.commit()
    db.refresh(pre_app)

    resp = PreApprovalResponse.model_validate(pre_app)
    resp.code = raw_code
    return resp


@router.get("/pre-approvals", response_model=list[PreApprovalResponse])
def list_pre_approvals(
    flat_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_flat_ids = [
        m.flat_id for m in current_user.flat_memberships if m.is_active is True and m.can_approve_visitors is True
    ]
    roles = get_user_roles(current_user)
    query = db.query(PreApproval)

    if "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles:
        if not user_flat_ids:
            return []
        query = query.filter(PreApproval.flat_id.in_(user_flat_ids))
        if flat_id and flat_id in user_flat_ids:
            query = query.filter(PreApproval.flat_id == flat_id)
    elif flat_id:
        query = query.filter(PreApproval.flat_id == flat_id)

    items = query.order_by(PreApproval.created_at.desc()).all()
    return items


@router.post("/guest-code/verify", response_model=GuestCodeVerifyResponse)
def verify_guest_code_endpoint(
    payload: GuestCodeVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only guards or admins can verify guest credentials."
        )

    enforce_guard_gate_scope(current_user, payload.gate_id)
    result = verify_guest_code(db, payload.gate_id, payload.code, payload.credential_jwt, consume=False)
    db.commit()
    return GuestCodeVerifyResponse(**result)


# =========================================================================
# Gate Offline Mode Endpoints
# =========================================================================


@router.post("/gate/devices/enroll", response_model=GateDeviceEnrollmentResponse)
def enroll_gate_device(
    payload: GateDeviceEnrollmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_guard_gate_scope(current_user, payload.gate_id)
    device = db.query(GateDevice).filter(GateDevice.device_id == payload.device_id).with_for_update().first()
    if device is None:
        device = GateDevice(
            device_id=payload.device_id,
            generation_id=payload.generation_id,
            gate_id=payload.gate_id,
            enrolled_by_user_id=current_user.id,
            is_active=True,
            last_sequence=0,
        )
        db.add(device)
    elif not device.is_active:
        raise HTTPException(status_code=403, detail="This gate device has been disabled.")
    elif device.generation_id != payload.generation_id:
        raise HTTPException(
            status_code=409,
            detail="Device generation differs from its server enrollment. An administrator must re-enroll this device.",
        )
    elif device.gate_id != payload.gate_id:
        raise HTTPException(status_code=403, detail="This device is enrolled for another gate.")
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    db.refresh(device)
    return GateDeviceEnrollmentResponse(
        device_id=device.device_id,
        generation_id=device.generation_id,
        gate_id=device.gate_id,
        last_sequence=device.last_sequence,
        is_active=device.is_active,
    )


@router.get("/gate/public-key")
def get_gate_public_key(current_user: User = Depends(get_current_user)):
    """Returns the configured signing public key to an authenticated gate operator."""
    roles = set(get_user_roles(current_user))
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Gate operator access is required.")
    return {
        "algorithm": "ECDSA_P256_SHA256",
        "public_key_pem": get_ecdsa_public_key_pem(),
        "offline_notice": "While offline a gate cannot know about later revocations or use at another disconnected gate.",
    }


@router.get("/gate/time-anchor")
def get_time_anchor(
    gate_id: str = Query(...),
    device_id: str = Query(..., min_length=16, max_length=64),
    generation_id: str = Query(..., min_length=16, max_length=64),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns a signed, gate-scoped UTC time anchor for offline capture evidence."""
    enforce_guard_gate_scope(current_user, gate_id)
    device = (
        db.query(GateDevice)
        .filter(
            GateDevice.device_id == device_id,
            GateDevice.generation_id == generation_id,
            GateDevice.gate_id == gate_id,
            GateDevice.is_active.is_(True),
        )
        .first()
    )
    if not device:
        raise HTTPException(status_code=403, detail="Gate device must be enrolled before obtaining a time anchor.")
    now = datetime.now(UTC)
    payload = {
        "user_id": current_user.id,
        "gate_id": gate_id,
        "device_id": device_id,
        "device_generation_id": generation_id,
        "server_time_utc": now.isoformat(),
        "timestamp_unix": int(now.timestamp()),
        "valid_until_unix": int(now.timestamp()) + 86400,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = get_ecdsa_private_key().sign(payload_bytes, ec.ECDSA(hashes.SHA256())).hex()
    return {"payload": payload, "signature": signature, "algorithm": "ECDSA_P256_SHA256"}


@router.post("/gate/sync", response_model=OfflineSyncResponse)
async def sync_offline_entry_endpoint(
    metadata: str = Form(...),
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = set(get_user_roles(current_user))
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only active guards can synchronize gate entries."
        )
    try:
        item = OfflineSyncItem.model_validate_json(metadata)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Offline visitor metadata is invalid.") from exc
    enforce_guard_gate_scope(current_user, item.gate_id)
    photo_bytes = await photo.read(5 * 1024 * 1024 + 1)
    if len(photo_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Visitor photograph exceeds 5 MB.")
    result = sync_offline_entry_with_photo(db, current_user.id, item, photo_bytes)
    return OfflineSyncResponse(**result)
