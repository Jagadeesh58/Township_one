"""
Township One — Complaint Lifecycle, Assignment, Timers, and Safety Services.

Handles:
- Explicit complaint state machine transitions (illegal transitions return HTTP 409).
- Deterministic shift and workload-based staff assignment.
- Human-gated first_response_at tracking and demo SLA calculations.
- Optimistic concurrency locking for Help Desk classification corrections.
- Emergency rule evaluation independent of external AI providers.
- Append-only timeline events and audit records.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.models.entities import (
    Complaint, ComplaintEvent, ClassificationDecision, SafetyEvent, SafetyEventAction,
    StaffMember, StaffShift, StaffTeam, Notification, User, Flat, Tower, AuditEvent
)

# Explicit transition table: current_status -> set of allowed next_statuses
VALID_TRANSITIONS = {
    "SUBMITTED": {"ASSIGNED", "IN_PROGRESS"},
    "ASSIGNED": {"IN_PROGRESS", "AWAITING_RESIDENT", "RESOLVED"},
    "IN_PROGRESS": {"AWAITING_RESIDENT", "RESOLVED"},
    "AWAITING_RESIDENT": {"IN_PROGRESS", "RESOLVED"},
    "RESOLVED": {"CLOSED", "REOPEN_REQUESTED"},
    "CLOSED": {"REOPEN_REQUESTED"},
    "REOPEN_REQUESTED": {"ASSIGNED", "IN_PROGRESS"},
}

CATEGORY_TO_TEAM_MAP = {
    "PLUMBING": "Plumbing Team",
    "ELECTRICAL": "Electrical Team",
    "LIFT": "Lift Maintenance Team",
    "CLEANLINESS": "Housekeeping Team",
    "WATER_SUPPLY": "Water Supply Team",
    "SECURITY": "Security & Safety Team",
    "COMMON_AREA": "Common Area Team",
    "GENERAL": "General Maintenance Team",
    "UNCLASSIFIED": "General Maintenance Team"
}


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_sla_metrics(complaint: Complaint) -> dict:
    """
    Computes demo SLA target, remaining minutes, and overdue status.
    Labelled as demo SLA per product requirements.
    """
    sla_hours = settings.DEMO_SLA_HOURS.get(complaint.urgency, 24)
    created_dt = ensure_utc(complaint.created_at) or datetime.now(timezone.utc)
    target_dt = created_dt + timedelta(hours=sla_hours)
    now_dt = datetime.now(timezone.utc)

    # If already responded, use first_response_at, else now
    resp_dt = ensure_utc(complaint.first_response_at)
    effective_dt = resp_dt or now_dt
    is_overdue = effective_dt > target_dt
    remaining_seconds = (target_dt - now_dt).total_seconds()

    return {
        "demo_sla_hours": sla_hours,
        "target_response_time": target_dt.isoformat(),
        "is_overdue": is_overdue,
        "remaining_minutes": max(0, int(remaining_seconds // 60)) if not is_overdue else 0,
        "overdue_minutes": int(abs(remaining_seconds) // 60) if is_overdue else 0,
        "has_first_response": resp_dt is not None,
        "first_response_at": resp_dt.isoformat() if resp_dt else None
    }


def find_eligible_staff(db: Session, category: str, tower_id: Optional[str] = None) -> Optional[StaffMember]:
    """
    Deterministically assigns on-duty staff member with lowest active workload.
    Ties broken deterministically by staff.id.
    """
    dept_map = {
        "PLUMBING": "Plumbing",
        "ELECTRICAL": "Electrical",
        "LIFT": "Operations",
        "CLEANLINESS": "Housekeeping",
        "WATER_SUPPLY": "Plumbing",
        "SECURITY": "Security",
        "COMMON_AREA": "Operations",
        "GENERAL": "Operations",
        "UNCLASSIFIED": "Operations"
    }
    target_dept = dept_map.get(category, "Operations")

    # Query on-duty staff in this department
    on_duty_staff = (
        db.query(StaffMember)
        .join(StaffShift, StaffMember.id == StaffShift.staff_id)
        .filter(
            StaffMember.department == target_dept,
            StaffMember.is_available == True,
            StaffShift.is_on_duty == True
        )
        .all()
    )

    if not on_duty_staff:
        # Fallback: any available staff in that department
        on_duty_staff = (
            db.query(StaffMember)
            .filter(StaffMember.department == target_dept, StaffMember.is_available == True)
            .all()
        )

    if not on_duty_staff:
        return None

    # Count active workload per staff candidate
    staff_ids = [s.id for s in on_duty_staff]
    active_statuses = ("SUBMITTED", "ASSIGNED", "IN_PROGRESS", "AWAITING_RESIDENT")

    workload_counts = dict(
        db.query(Complaint.assigned_staff_id, func.count(Complaint.id))
        .filter(
            Complaint.assigned_staff_id.in_(staff_ids),
            Complaint.status.in_(active_statuses)
        )
        .group_by(Complaint.assigned_staff_id)
        .all()
    )

    # Sort deterministically by (workload, staff_id)
    sorted_staff = sorted(
        on_duty_staff,
        key=lambda s: (workload_counts.get(s.id, 0), s.id)
    )

    return sorted_staff[0]


def transition_complaint_status(
    db: Session,
    complaint: Complaint,
    target_status: str,
    actor_user: User,
    actor_role: str,
    notes: Optional[str] = None
) -> Complaint:
    """
    Executes a validated status transition.
    Enforces the explicit transition rules; raises HTTP 409 Conflict if illegal.
    """
    current_status = complaint.status
    allowed_next = VALID_TRANSITIONS.get(current_status, set())

    if target_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal complaint status transition from '{current_status}' to '{target_status}'. "
                   f"Allowed target statuses: {sorted(list(allowed_next))}."
        )

    now_utc = datetime.now(timezone.utc)
    complaint.status = target_status
    complaint.version += 1

    # Human action records first_response_at if not previously recorded
    if complaint.first_response_at is None and actor_role in ("HELPDESK", "ADMIN", "STAFF"):
        complaint.first_response_at = now_utc

    if target_status == "RESOLVED":
        complaint.resolved_at = now_utc
    elif target_status == "CLOSED":
        complaint.closed_at = now_utc

    # Append-only timeline event
    event = ComplaintEvent(
        complaint_id=complaint.id,
        actor_user_id=actor_user.id,
        actor_role=actor_role,
        event_type="STATUS_CHANGED",
        from_status=current_status,
        to_status=target_status,
        notes=notes,
        created_at=now_utc
    )
    db.add(event)

    # Append-only audit record
    db.add(AuditEvent(
        entity_type="COMPLAINT",
        entity_id=complaint.id,
        action="STATUS_CHANGED",
        actor_user_id=actor_user.id,
        actor_role=actor_role,
        old_state={"status": current_status},
        new_state={"status": target_status},
        reason=notes,
        created_at=now_utc
    ))

    # In-app notification to resident
    db.add(Notification(
        user_id=complaint.user_id,
        notification_type="COMPLAINT_UPDATE",
        title=f"Complaint #{complaint.ticket_number} Updated",
        message=f"Status changed to {target_status}. Notes: {notes or 'No additional notes'}",
        payload={"complaint_id": complaint.id, "status": target_status}
    ))

    return complaint


def correct_classification(
    db: Session,
    complaint: Complaint,
    new_category: str,
    new_urgency: str,
    reason: str,
    expected_version: int,
    actor_user: User,
    actor_role: str
) -> ClassificationDecision:
    """
    Help Desk one-tap correction with optimistic concurrency locking.
    Fails with HTTP 409 if expected_version != complaint.version.
    """
    if complaint.version != expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Optimistic lock conflict: complaint has been modified by another user. "
                   f"Expected version {expected_version}, current version {complaint.version}."
        )

    # If complaint is flagged as safety escalation, human or AI cannot lower urgency below CRITICAL
    if complaint.is_safety_escalation and new_urgency != "CRITICAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot lower urgency on a verified safety escalation ticket."
        )

    now_utc = datetime.now(timezone.utc)
    old_cat = complaint.category
    old_urg = complaint.urgency

    complaint.category = new_category
    complaint.urgency = new_urgency
    complaint.version += 1

    # Record first response if not set
    if complaint.first_response_at is None and actor_role in ("HELPDESK", "ADMIN"):
        complaint.first_response_at = now_utc

    # Save ClassificationDecision
    decision = ClassificationDecision(
        complaint_id=complaint.id,
        actor_type="HUMAN_HELP_DESK",
        actor_user_id=actor_user.id,
        category=new_category,
        urgency=new_urgency,
        short_reason=reason,
        language=complaint.language,
        confidence=1.0,
        needs_human_review=False,
        expected_version=expected_version,
        is_active=True,
        created_at=now_utc
    )
    db.add(decision)

    # Append timeline event
    db.add(ComplaintEvent(
        complaint_id=complaint.id,
        actor_user_id=actor_user.id,
        actor_role=actor_role,
        event_type="CATEGORY_CORRECTED",
        notes=f"Corrected from {old_cat}/{old_urg} to {new_category}/{new_urgency}: {reason}",
        created_at=now_utc
    ))

    # Append audit event
    db.add(AuditEvent(
        entity_type="CLASSIFICATION",
        entity_id=complaint.id,
        action="CLASSIFICATION_CORRECTED",
        actor_user_id=actor_user.id,
        actor_role=actor_role,
        old_state={"category": old_cat, "urgency": old_urg},
        new_state={"category": new_category, "urgency": new_urgency},
        reason=reason,
        created_at=now_utc
    ))

    return decision
