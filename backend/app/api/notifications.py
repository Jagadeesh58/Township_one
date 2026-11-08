"""
Township One - In-App Notifications API Endpoints.

Provides:
- Fetching user in-app notifications
- Marking notifications as read
- Unread count badge support
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, verify_csrf
from backend.app.models.entities import User, Notification
from backend.app.schemas.notifications import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches in-app notifications for the authenticated user."""
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)

    notifications = q.order_by(Notification.created_at.desc()).limit(limit).all()

    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            message=n.message,
            channel=n.channel or "IN_APP",
            status="READ" if n.is_read else "UNREAD",
            created_at=n.created_at,
            read_at=n.created_at if n.is_read else None
        )
        for n in notifications
    ]


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns number of unread notifications for badge display."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"unread_count": count}


@router.post("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db)
):
    """Marks a single notification as read."""
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    n.is_read = True
    db.commit()
    return {"status": "READ", "id": n.id}


@router.post("/read-all")
def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db)
):
    """Marks all notifications for the user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "ALL_READ"}
