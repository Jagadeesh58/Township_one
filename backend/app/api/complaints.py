"""
Township One — Complaint Lifecycle, AI Triage, Duplicates & Help Desk API Endpoints.

Provides:
- Resident Complaint submission (with trilingual emergency detection & AI classification)
- Private photo upload, EXIF stripping, and signed streaming
- Flat-scoped resident views with strict cross-resident IDOR protections
- Resident rating (1-5 after RESOLVED) and reopen requests
- Help Desk queue with SLA countdown badges and filters
- Explicit status transitions (with 409 Conflict on illegal transition)
- One-tap classification correction with optimistic version locking
- Semantic duplicate detection and incident group linking
- Safety escalation event management
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role, verify_csrf, verify_flat_access
from backend.app.ml.classifier import predict_category_and_urgency
from backend.app.ml.duplicates import find_duplicate_candidates
from backend.app.ml.emergency import detect_emergency
from backend.app.models.entities import (
    AuditEvent,
    ClassificationDecision,
    Complaint,
    ComplaintAttachment,
    ComplaintEvent,
    Flat,
    IncidentGroup,
    IncidentGroupMember,
    Notification,
    SafetyEvent,
    SafetyEventAction,
    Tower,
    User,
)
from backend.app.schemas.complaints import (
    ClassificationCorrectionRequest,
    ClassificationDecisionResponse,
    ComplaintEventResponse,
    ComplaintResponse,
    LinkDuplicateRequest,
    RatingRequest,
    ReopenRequest,
    SafetyEventActionRequest,
    SafetyEventResponse,
    StatusTransitionRequest,
)
from backend.app.services.complaints import (
    CATEGORY_TO_TEAM_MAP,
    compute_sla_metrics,
    correct_classification,
    find_eligible_staff,
    transition_complaint_status,
)
from backend.app.services.storage import (
    generate_signed_photo_url,
    read_private_object,
    save_complaint_photo,
    verify_signed_photo_token,
)

router = APIRouter(prefix="/complaints", tags=["Complaints & Help Desk"])


def to_complaint_response(c: Complaint, db: Session, user: User | None = None) -> ComplaintResponse:
    sla_info = compute_sla_metrics(c)

    flat = db.query(Flat).filter(Flat.id == c.flat_id).first()
    flat_num = flat.flat_number if flat else None
    tower_name = None
    if c.tower_id:
        t = db.query(Tower).filter(Tower.id == c.tower_id).first()
        if t:
            tower_name = t.name

    staff_name = None
    if c.assigned_staff:
        staff_name = c.assigned_staff.name

    # Signed photo URL if attachment exists
    photo_url = None
    att = db.query(ComplaintAttachment).filter(ComplaintAttachment.complaint_id == c.id).first()
    if att:
        photo_url = generate_signed_photo_url(att.storage_key)

    events_resp = [
        ComplaintEventResponse(
            id=ev.id,
            event_type=ev.event_type,
            from_status=ev.from_status,
            to_status=ev.to_status,
            notes=ev.notes,
            created_at=ev.created_at,
            actor_user_id=ev.actor_user_id,
        )
        for ev in (c.events or [])
    ]

    clf_resp = None
    if c.decisions:
        # Active or latest decision
        active_clf = next((cd for cd in c.decisions if cd.is_active), c.decisions[-1])
        clf_resp = ClassificationDecisionResponse(
            id=active_clf.id,
            provider=active_clf.actor_type or "system",
            model_version=active_clf.model_version,
            prompt_version=active_clf.prompt_version,
            predicted_category=active_clf.category,
            predicted_urgency=active_clf.urgency,
            confidence=active_clf.confidence,
            fallback_used=active_clf.fallback_used or False,
            needs_human_review=active_clf.needs_human_review or False,
            created_at=active_clf.created_at,
        )

    return ComplaintResponse(
        id=c.id,
        ticket_number=c.ticket_number,
        flat_id=c.flat_id,
        flat_number=flat_num,
        tower_id=c.tower_id,
        tower_name=tower_name,
        title=c.title,
        description=c.description,
        category=c.category,
        urgency=c.urgency,
        status=c.status,
        version=c.version or 1,
        is_safety_escalation=c.is_safety_escalation or False,
        language=c.language or "en",
        assigned_staff_id=c.assigned_staff_id,
        assigned_staff_name=staff_name,
        assigned_team=c.assigned_team,
        created_at=c.created_at or datetime.now(UTC),
        first_response_at=c.first_response_at,
        resolved_at=c.resolved_at,
        closed_at=c.closed_at,
        rating=c.rating,
        feedback=getattr(c, "feedback", None) or c.resolution_summary,
        reopen_reason=c.reopen_reason,
        photo_url=photo_url,
        sla_remaining_minutes=sla_info.get("remaining_minutes"),
        is_overdue=sla_info.get("is_overdue", False),
        events=events_resp,
        classification_decision=clf_resp,
    )


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def raise_complaint(
    flat_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    language: str | None = Form("en"),
    photo: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Raises a new resident maintenance complaint.
    1. Enforces resident flat membership and permission to lodge complaints.
    2. Runs deterministic life-safety emergency detector (CRITICAL urgency).
    3. Executes AI / Local classifier for category and urgency prediction.
    4. Deterministically assigns on-duty staff member.
    5. Saves and strips EXIF from optional private photo.
    """
    # 1. Authorize flat access
    verify_flat_access(current_user, flat_id, action="raise_complaint")

    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flat not found")

    full_text = f"{title.strip()} {description.strip()}"
    now_utc = datetime.now(UTC)

    # 2. Emergency Rule Evaluation (Deterministic)
    emergency_info = detect_emergency(full_text)
    is_emergency = emergency_info.get("is_emergency", False)

    category: str
    urgency: str
    is_safety_escalation: bool = False
    provider: str
    model_version: str | None = None
    fallback_used: bool = False
    needs_review: bool = False
    confidence_val: float = 0.95

    hazard_to_category = {
        "FIRE": "COMMON_AREA",
        "SMOKE": "COMMON_AREA",
        "GAS_LEAK": "PLUMBING",
        "LIFT_TRAPPED": "LIFT",
        "ELECTRIC_SHOCK_SPARKING": "ELECTRICAL",
    }

    if is_emergency:
        is_safety_escalation = True
        urgency = "CRITICAL"
        hazard_type = str(emergency_info.get("hazard_type") or emergency_info.get("trigger") or "GENERAL")
        category = hazard_to_category.get(hazard_type, "GENERAL")
        provider = "rule_emergency_engine"
        confidence_val = 1.0
    else:
        # 3. AI / Local Model Classification
        clf_res = predict_category_and_urgency(full_text)
        pred_cat = clf_res.get("category", "UNCLASSIFIED")
        category = pred_cat if pred_cat != "UNCLASSIFIED" else "GENERAL"
        urgency = clf_res.get("urgency", "MEDIUM")
        provider = clf_res.get("provider", "local_nb")
        model_version = clf_res.get("model_version")
        fallback_used = clf_res.get("fallback_used", False)
        needs_review = clf_res.get("needs_human_review", False)
        confidence_val = clf_res.get("confidence", 0.8)

    # 4. Deterministic Staff Assignment
    assigned_staff = find_eligible_staff(db, category, tower_id=flat.tower_id)
    assigned_team = CATEGORY_TO_TEAM_MAP.get(category, "General Maintenance Team")
    initial_status = "ASSIGNED" if assigned_staff else "SUBMITTED"

    # Safe ticket number generator that never collides with seeded ticket numbers
    existing_tickets = db.query(Complaint.ticket_number).all()
    max_seq = 1000
    for (t_num,) in existing_tickets:
        if t_num and t_num.startswith("CMP-2026-"):
            try:
                suffix = int(t_num.split("-")[-1])
                if suffix > max_seq:
                    max_seq = suffix
            except ValueError:
                pass
    ticket_num = f"CMP-2026-{max_seq + 1}"

    complaint = Complaint(
        ticket_number=ticket_num,
        flat_id=flat.id,
        tower_id=flat.tower_id,
        user_id=current_user.id,
        title=title.strip(),
        description=description.strip(),
        category=category,
        urgency=urgency,
        status=initial_status,
        version=1,
        is_safety_escalation=is_safety_escalation,
        language=language or "en",
        assigned_staff_id=assigned_staff.id if assigned_staff else None,
        assigned_team=assigned_team,
        created_at=now_utc,
    )
    db.add(complaint)
    db.flush()

    # Classification decision record
    clf_record = ClassificationDecision(
        complaint_id=complaint.id,
        actor_type=provider,
        model_version=model_version,
        prompt_version="v1.0",
        category=category,
        urgency=urgency,
        confidence=confidence_val,
        fallback_used=fallback_used,
        needs_human_review=needs_review,
        language=language or "en",
        is_active=True,
        created_at=now_utc,
    )
    db.add(clf_record)

    # Initial timeline event
    db.add(
        ComplaintEvent(
            complaint_id=complaint.id,
            actor_user_id=current_user.id,
            actor_role="RESIDENT",
            event_type="SUBMITTED",
            to_status=initial_status,
            notes=f"Complaint lodged via resident portal. Initial triage: {category} ({urgency})",
            created_at=now_utc,
        )
    )

    # Safety event record if emergency
    if is_safety_escalation:
        safety_ev = SafetyEvent(
            complaint_id=complaint.id,
            trigger_pattern=str(emergency_info.get("hazard_type") or emergency_info.get("trigger") or "HAZARD"),
            matched_text=f"Emergency trigger: {emergency_info.get('match_snippet') or emergency_info.get('matched_text') or 'Safety rule matched'}",
            language=language or "en",
            duty_manager_notified=True,
            status="ACTIVE",
            created_at=now_utc,
        )
        db.add(safety_ev)

        # Notify duty manager
        db.add(
            Notification(
                user_id=current_user.id,
                notification_type="SAFETY_ESCALATION",
                title=f"URGENT: Safety Escalation #{ticket_num}",
                message=f"Critical safety incident detected in Flat {flat.flat_number}: {title}",
                payload={"complaint_id": complaint.id, "urgency": "CRITICAL"},
            )
        )

    # 5. Handle Photo Attachment
    if photo and photo.filename:
        photo_bytes = await photo.read()
        if len(photo_bytes) > 0:
            storage_key, mime_type, file_size, file_sha256 = save_complaint_photo(photo_bytes, photo.filename)
            attachment = ComplaintAttachment(
                complaint_id=complaint.id,
                storage_key=storage_key,
                file_name=photo.filename,
                content_type=mime_type,
                file_size=file_size,
                file_sha256=file_sha256,
                created_at=now_utc,
            )
            db.add(attachment)

    db.commit()
    db.refresh(complaint)
    return to_complaint_response(complaint, db, current_user)


@router.get("/my", response_model=list[ComplaintResponse])
def list_my_complaints(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves complaints for flats where current resident has an active membership.
    Strictly isolated: residents cannot see complaints from other flats.
    """
    user_flat_ids = [fm.flat_id for fm in current_user.flat_memberships if fm.is_active]
    if not user_flat_ids:
        return []

    complaints = (
        db.query(Complaint).filter(Complaint.flat_id.in_(user_flat_ids)).order_by(Complaint.created_at.desc()).all()
    )

    return [to_complaint_response(c, db, current_user) for c in complaints]


@router.get("/helpdesk/queue")
def get_helpdesk_queue(
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = None,
    urgency: str | None = None,
    tower_id: str | None = None,
    overdue_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN", "MANAGEMENT", "OPERATIONS", "COMMITTEE"])),
    db: Session = Depends(get_db),
):
    """
    Help Desk triage dashboard queue with filters and SLA status calculation.
    """
    q = db.query(Complaint)
    if status_filter:
        q = q.filter(Complaint.status == status_filter)
    if category:
        q = q.filter(Complaint.category == category)
    if urgency:
        q = q.filter(Complaint.urgency == urgency)
    if tower_id:
        q = q.filter(Complaint.tower_id == tower_id)

    complaints = q.order_by(Complaint.is_safety_escalation.desc(), Complaint.created_at.desc()).all()

    items = []
    for c in complaints:
        resp = to_complaint_response(c, db, current_user)
        if overdue_only and not resp.is_overdue:
            continue
        items.append(resp)

    total = len(items)
    offset = (page - 1) * page_size
    paged_items = items[offset : offset + page_size]

    return {"page": page, "page_size": page_size, "total": total, "items": paged_items}


@router.get("/safety-events", response_model=list[SafetyEventResponse])
def list_safety_events(
    status_filter: str | None = Query("OPEN", alias="status"),
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN", "COMMITTEE", "MANAGEMENT"])),
    db: Session = Depends(get_db),
):
    """Lists life-safety escalation events."""
    q = db.query(SafetyEvent)
    if status_filter:
        q = q.filter(SafetyEvent.status == status_filter)

    events = q.order_by(SafetyEvent.created_at.desc()).all()

    results = []
    for ev in events:
        c = db.query(Complaint).filter(Complaint.id == ev.complaint_id).first()
        flat_num = None
        ticket = None
        if c:
            ticket = c.ticket_number
            f = db.query(Flat).filter(Flat.id == c.flat_id).first()
            if f:
                flat_num = f.flat_number

        results.append(
            SafetyEventResponse(
                id=ev.id,
                complaint_id=ev.complaint_id,
                event_type=ev.trigger_pattern,
                details=ev.matched_text,
                status=ev.status,
                created_at=ev.created_at or datetime.now(UTC),
                ticket_number=ticket,
                flat_number=flat_num,
            )
        )
    return results


@router.post("/safety-events/{event_id}/action")
def acknowledge_safety_event(
    event_id: str,
    action_req: SafetyEventActionRequest,
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN", "MANAGEMENT"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """Acknowledges or dismisses a safety event with mandatory audit trail."""
    ev = db.query(SafetyEvent).filter(SafetyEvent.id == event_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety event not found")

    now_utc = datetime.now(UTC)
    old_status = ev.status
    target_status = "ACKNOWLEDGED" if action_req.action == "ACKNOWLEDGE" else "DISMISSED"
    ev.status = target_status

    db.add(
        SafetyEventAction(
            safety_event_id=ev.id,
            actor_user_id=current_user.id,
            action=action_req.action,
            notes=action_req.notes,
            created_at=now_utc,
        )
    )

    db.add(
        AuditEvent(
            entity_type="SAFETY",
            entity_id=ev.id,
            action=f"SAFETY_EVENT_{action_req.action}",
            actor_user_id=current_user.id,
            actor_role="HELPDESK",
            old_state={"status": old_status},
            new_state={"status": target_status},
            reason=action_req.notes,
            created_at=now_utc,
        )
    )

    db.commit()
    return {"status": target_status, "safety_event_id": ev.id}


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint_detail(
    complaint_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Retrieves full detail of a single complaint.
    Strictly verifies user has active membership for the flat or is authorized staff.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    user_roles = [ra.role_code for ra in current_user.role_assignments if ra.is_active]
    is_staff = any(r in ["HELPDESK", "ADMIN", "MANAGEMENT", "MAINTENANCE", "OPERATIONS"] for r in user_roles)

    if not is_staff:
        # Check flat membership
        has_membership = any(fm.flat_id == complaint.flat_id and fm.is_active for fm in current_user.flat_memberships)
        if not has_membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    return to_complaint_response(complaint, db, current_user)


@router.post("/{complaint_id}/transition", response_model=ComplaintResponse)
def transition_status(
    complaint_id: str,
    trans_req: StatusTransitionRequest,
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN", "STAFF", "MAINTENANCE", "OPERATIONS"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Transitions complaint lifecycle status.
    Raises HTTP 409 Conflict if transition is illegal according to explicit state machine.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    if trans_req.expected_version is not None and complaint.version != trans_req.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Optimistic lock conflict: complaint has been modified (version {complaint.version} != expected {trans_req.expected_version})",
        )

    user_roles = [ra.role_code for ra in current_user.role_assignments if ra.is_active]
    role = "ADMIN" if "ADMIN" in user_roles else ("HELPDESK" if "HELPDESK" in user_roles else "STAFF")

    updated = transition_complaint_status(
        db=db,
        complaint=complaint,
        target_status=trans_req.status,
        actor_user=current_user,
        actor_role=role,
        notes=trans_req.notes,
    )

    db.commit()
    db.refresh(updated)
    return to_complaint_response(updated, db, current_user)


@router.post("/{complaint_id}/correct-classification")
def correct_complaint_classification(
    complaint_id: str,
    corr_req: ClassificationCorrectionRequest,
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Help Desk one-tap correction for category and urgency.
    Protected by optimistic locking (expected_version, raises 409 on mismatch).
    Safety escalations cannot be downgraded below CRITICAL.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    user_roles = [ra.role_code for ra in current_user.role_assignments if ra.is_active]
    role = "ADMIN" if "ADMIN" in user_roles else "HELPDESK"

    correct_classification(
        db=db,
        complaint=complaint,
        new_category=corr_req.category,
        new_urgency=corr_req.urgency,
        reason=corr_req.reason,
        expected_version=corr_req.expected_version,
        actor_user=current_user,
        actor_role=role,
    )

    db.commit()
    db.refresh(complaint)
    return to_complaint_response(complaint, db, current_user)


@router.post("/{complaint_id}/rate", response_model=ComplaintResponse)
def rate_complaint(
    complaint_id: str,
    rate_req: RatingRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """Resident rates complaint resolution (1-5 stars) after status is RESOLVED."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    # Flat check
    has_membership = any(fm.flat_id == complaint.flat_id and fm.is_active for fm in current_user.flat_memberships)
    if not has_membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: not a resident of this flat")

    if complaint.status not in ["RESOLVED", "CLOSED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Complaints can only be rated once resolved."
        )

    complaint.rating = rate_req.rating
    if rate_req.feedback:
        complaint.resolution_summary = rate_req.feedback
    complaint.version += 1

    db.add(
        ComplaintEvent(
            complaint_id=complaint.id,
            actor_user_id=current_user.id,
            actor_role="RESIDENT",
            event_type="RATED",
            notes=f"Resident submitted rating: {rate_req.rating}/5 stars. Feedback: {rate_req.feedback or 'None'}",
            created_at=datetime.now(UTC),
        )
    )

    db.commit()
    db.refresh(complaint)
    return to_complaint_response(complaint, db, current_user)


@router.post("/{complaint_id}/reopen", response_model=ComplaintResponse)
def request_reopen(
    complaint_id: str,
    reopen_req: ReopenRequest,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """Resident requests reopening a RESOLVED or CLOSED complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    has_membership = any(fm.flat_id == complaint.flat_id and fm.is_active for fm in current_user.flat_memberships)
    if not has_membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: not a resident of this flat")

    complaint.reopen_reason = reopen_req.reason

    updated = transition_complaint_status(
        db=db,
        complaint=complaint,
        target_status="REOPEN_REQUESTED",
        actor_user=current_user,
        actor_role="RESIDENT",
        notes=f"Resident requested reopen: {reopen_req.reason}",
    )

    db.commit()
    db.refresh(updated)
    return to_complaint_response(updated, db, current_user)


@router.get("/{complaint_id}/duplicate-candidates")
def get_duplicate_candidates(
    complaint_id: str,
    threshold: float = 0.15,
    limit: int = 10,
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """Finds near-duplicate tickets in the same tower using char n-gram TF-IDF cosine similarity."""
    target_comp = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not target_comp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    # Fetch other open/in-progress complaints from the same tower
    candidates = (
        db.query(Complaint)
        .filter(Complaint.id != target_comp.id, Complaint.tower_id == target_comp.tower_id)
        .order_by(Complaint.created_at.desc())
        .limit(50)
        .all()
    )

    cand_dicts = [
        {
            "id": c.id,
            "ticket_number": c.ticket_number,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "urgency": c.urgency,
            "status": c.status,
            "tower_id": c.tower_id,
            "created_at": c.created_at,
        }
        for c in candidates
    ]

    scored = find_duplicate_candidates(
        new_text=f"{target_comp.title} {target_comp.description}",
        existing_complaints=cand_dicts,
        threshold=threshold,
        max_candidates=limit,
        tower_id=target_comp.tower_id,
    )

    return {"candidates": scored}


@router.post("/{complaint_id}/link-duplicate")
def link_duplicate(
    complaint_id: str,
    link_req: LinkDuplicateRequest,
    current_user: User = Depends(require_role(["HELPDESK", "ADMIN"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Links a complaint to an incident group.
    Both tickets remain open and independently trackable.
    """
    c1 = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    c2 = db.query(Complaint).filter(Complaint.id == link_req.target_complaint_id).first()
    if not c1 or not c2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    now_utc = datetime.now(UTC)

    # Find or create IncidentGroup
    group = None
    if c2.incident_group_id:
        group = db.query(IncidentGroup).filter(IncidentGroup.id == c2.incident_group_id).first()

    if not group:
        group = IncidentGroup(
            tower_id=c1.tower_id or c2.tower_id or "default",
            category=c1.category,
            title=f"Incident Group: {c1.title[:50]}",
            status="ACTIVE",
            created_at=now_utc,
        )
        db.add(group)
        db.flush()

        # Link c2
        c2.incident_group_id = group.id
        db.add(
            IncidentGroupMember(
                incident_group_id=group.id, complaint_id=c2.id, linked_by_user_id=current_user.id, created_at=now_utc
            )
        )

    # Link c1
    c1.incident_group_id = group.id
    c1.duplicate_of_id = c2.id
    db.add(
        IncidentGroupMember(
            incident_group_id=group.id, complaint_id=c1.id, linked_by_user_id=current_user.id, created_at=now_utc
        )
    )

    db.add(
        ComplaintEvent(
            complaint_id=c1.id,
            actor_user_id=current_user.id,
            actor_role="HELPDESK",
            event_type="DUPLICATE_LINKED",
            notes=f"Linked to primary incident ticket #{c2.ticket_number} under Incident Group {group.id}",
            created_at=now_utc,
        )
    )

    db.commit()
    return {
        "status": "LINKED",
        "incident_group_id": group.id,
        "complaint_id": c1.id,
        "primary_ticket": c2.ticket_number,
    }


def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Returns authenticated User if session cookie is valid, else None without raising 401."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


@router.get("/photos/{storage_key}")
def stream_complaint_photo(
    storage_key: str,
    exp: int | None = Query(None),
    sig: str | None = Query(None),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    Secure photo streaming.
    Requires either a valid signed token (<= 5 min) or authenticated staff / flat membership.
    """
    has_valid_signature = False
    if exp is not None and sig is not None:
        has_valid_signature = verify_signed_photo_token(storage_key, exp, sig)

    if not has_valid_signature and not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired photo signature")

    att = db.query(ComplaintAttachment).filter(ComplaintAttachment.storage_key == storage_key).first()
    if not att:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    if not has_valid_signature and current_user:
        user_roles = [ra.role_code for ra in current_user.role_assignments if ra.is_active]
        is_staff = any(r in ["HELPDESK", "ADMIN", "MANAGEMENT", "MAINTENANCE", "OPERATIONS"] for r in user_roles)
        if not is_staff:
            c = db.query(Complaint).filter(Complaint.id == att.complaint_id).first()
            if not c:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
            has_membership = any(fm.flat_id == c.flat_id and fm.is_active for fm in current_user.flat_memberships)
            if not has_membership:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    content = read_private_object(storage_key)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo file not found")

    return Response(
        content, media_type=att.content_type or "image/jpeg", headers={"Cache-Control": "private, no-store"}
    )
