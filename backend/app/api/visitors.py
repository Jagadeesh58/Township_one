import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Response
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import (
    User,
    VisitorEntry,
    VisitorPhoto,
    PreApproval,
    Flat,
    Tower,
    FlatMembership,
    Gate,
)
from backend.app.schemas.visitors import (
    VisitorStatus,
    VisitorEntryCreate,
    VisitorEntryResponse,
    VisitorApprovalDecision,
    SupervisorOverrideRequest,
    PreApprovalCreate,
    PreApprovalResponse,
    GuestCodeVerifyRequest,
    GuestCodeVerifyResponse,
    OfflineSyncRequest,
    OfflineSyncResponse,
)
from backend.app.services.visitor_service import (
    transition_visitor_entry,
    admit_visitor,
    exit_visitor,
    apply_supervisor_override,
    validate_and_process_photo,
    generate_signed_photo_url,
    verify_photo_signature,
    create_pre_approval,
    verify_guest_code,
    sync_offline_entries,
    get_storage_path,
    get_ecdsa_public_key_pem,
)

router = APIRouter(prefix="/visitors", tags=["visitors"])


def get_user_roles(user: User) -> List[str]:
    return [r.role_code for r in user.role_assignments]


@router.get("/entries", response_model=List[VisitorEntryResponse])
def list_visitor_entries(
    gate_id: Optional[str] = Query(None),
    flat_id: Optional[str] = Query(None),
    status_filter: Optional[VisitorStatus] = Query(None),
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Guard must specify a gate_id to view entries."
            )
        query = query.filter(VisitorEntry.gate_id == gate_id)

    # 2. Residents see only entries for flats they belong to
    elif "RESIDENT" in roles and "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles:
        user_flat_ids = [
            m.flat_id for m in current_user.flat_memberships if m.can_approve_visitors
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

        result.append(VisitorEntryResponse(
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
        ))

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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only guards or administrators can record visitor arrival."
        )

    flat = db.query(Flat).filter(Flat.id == payload.flat_id).first()
    if not flat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified flat does not exist."
        )

    gate = db.query(Gate).filter(Gate.id == payload.gate_id).first()
    if not gate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified gate does not exist."
        )

    # Check client_event_id deduplication
    if payload.client_event_id:
        existing = db.query(VisitorEntry).filter(
            VisitorEntry.client_event_id == payload.client_event_id
        ).first()
        if existing:
            return existing

    entry = VisitorEntry(
        gate_id=payload.gate_id,
        flat_id=payload.flat_id,
        visitor_name=payload.visitor_name,
        phone=payload.phone,
        purpose=payload.purpose,
        status=VisitorStatus.AWAITING_APPROVAL.value,
        created_by_guard=current_user.id,
        photo_id=payload.photo_id,
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
    membership = db.query(FlatMembership).filter(
        FlatMembership.flat_id == entry.flat_id,
        FlatMembership.user_id == current_user.id,
        FlatMembership.can_approve_visitors == True,
    ).first()

    roles = get_user_roles(current_user)
    if not membership and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to approve visitors for this flat."
        )

    target_status = VisitorStatus.APPROVED if decision_payload.decision == "APPROVE" else VisitorStatus.REJECTED
    entry.approval_decided_by = current_user.id
    entry.approval_decided_at = datetime.now(timezone.utc)

    transition_visitor_entry(
        db,
        entry,
        target_status,
        current_user.id,
        "RESIDENT" if membership else "ADMIN",
        notes=f"Resident {decision_payload.decision.lower()}d visitor arrival."
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only on-duty guards can record visitor exit.")

    entry = db.query(VisitorEntry).filter(VisitorEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visitor entry not found.")

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
    matching_role = "ADMIN" if "ADMIN" in roles else ("HELPDESK" if ("HELPDESK" in roles or "HELP_DESK" in roles) else None)
    if not matching_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor override requires HELPDESK or ADMIN privileges."
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only guards or admins can upload visitor photos.")

    content = await file.read()
    sha256_hash, content_type, file_size, clean_bytes = validate_and_process_photo(content, file.filename or "photo.jpg")

    now = datetime.now(timezone.utc)
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

    # Save to private storage
    storage_dir = get_storage_path()
    file_path = os.path.join(storage_dir, f"{photo.id}.jpg")
    with open(file_path, "wb") as f:
        f.write(clean_bytes)

    photo.storage_key = file_path
    db.commit()

    return {
        "photo_id": photo.id,
        "sha256": sha256_hash,
        "capture_time": now.isoformat(),
        "retention_expires_at": retention_expires_at.isoformat(),
        "data_protection_notice": "Visitor photograph collected for security logging and automatically purged after 90 days."
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or expired photo signature."
        )

    photo = db.query(VisitorPhoto).filter(VisitorPhoto.id == photo_id).first()
    if not photo or not photo.storage_key or not os.path.exists(photo.storage_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photograph file not found or retention period expired.")

    return FileResponse(photo.storage_key, media_type="image/jpeg")


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


@router.get("/pre-approvals", response_model=List[PreApprovalResponse])
def list_pre_approvals(
    flat_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_flat_ids = [
        m.flat_id for m in current_user.flat_memberships if m.can_approve_visitors
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only guards or admins can verify guest credentials.")

    result = verify_guest_code(db, payload.gate_id, payload.code, payload.credential_jwt)
    db.commit()
    return GuestCodeVerifyResponse(**result)


# =========================================================================
# Gate Offline Mode Endpoints
# =========================================================================

@router.get("/gate/public-key")
def get_gate_public_key():
    """Provides ECDSA P-256 public key for enrolled gate devices to verify credentials offline."""
    return {
        "algorithm": "ECDSA_P256_SHA256",
        "public_key_pem": get_ecdsa_public_key_pem(),
        "offline_notice": "While offline a gate cannot know about later revocations or use at another disconnected gate."
    }


@router.get("/gate/time-anchor")
def get_time_anchor():
    """Issues device time anchor for offline timestamp verification."""
    now = datetime.now(timezone.utc)
    return {
        "server_time_utc": now.isoformat(),
        "timestamp_unix": int(now.timestamp()),
        "validity_window_seconds": 86400,
    }


@router.post("/gate/sync", response_model=OfflineSyncResponse)
def sync_offline_entries_endpoint(
    payload: OfflineSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "GUARD" not in roles and "ADMIN" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only guards can synchronize offline gate queues.")

    res = sync_offline_entries(db, current_user.id, payload.events)
    db.commit()
    return OfflineSyncResponse(**res)
