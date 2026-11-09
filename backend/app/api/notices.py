from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import (
    User,
    Notice,
    NoticeRevision,
    NoticeRead,
    Tower,
    Flat,
    FlatMembership,
)
from backend.app.schemas.notices import (
    NoticeCreate,
    NoticeRevisionResponse,
)
from backend.app.services.notice_service import (
    create_notice,
    update_notice_create_revision,
    withdraw_notice,
    record_notice_read,
    resolve_language_body,
)
from backend.app.services.amenity_service import get_effective_now

router = APIRouter(prefix="/notices", tags=["notices"])


def get_user_roles(user: User) -> List[str]:
    return [r.role_code for r in user.role_assignments]


@router.get("", response_model=List[NoticeRevisionResponse])
def list_active_notices(
    lang: str = Query("en"),
    tower_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    now = get_effective_now()
    is_staff = any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles)

    query = db.query(Notice).filter(Notice.status == "PUBLISHED")

    if not is_staff:
        # Resident scoping: find towers where resident holds flats
        user_tower_ids = db.query(Flat.tower_id).join(FlatMembership).filter(
            FlatMembership.user_id == current_user.id
        ).distinct().all()
        resident_towers = [t[0] for t in user_tower_ids]

        # Filter by expiry and audience
        query = query.filter(
            Notice.published_at <= now,
            (Notice.expires_at.is_(None)) | (Notice.expires_at >= now),
            (Notice.target_audience == "ALL") | (Notice.target_tower_id.in_(resident_towers))
        )
    else:
        if tower_id:
            query = query.filter(
                (Notice.target_audience == "ALL") | (Notice.target_tower_id == tower_id)
            )

    notices = query.order_by(Notice.published_at.desc()).all()

    # Build response using current revisions
    result = []
    for n in notices:
        if not n.current_revision_id:
            continue
        rev = db.query(NoticeRevision).filter(NoticeRevision.id == n.current_revision_id).first()
        if not rev:
            continue

        body, is_fallback, fallback_label = resolve_language_body(rev, lang)
        is_read = db.query(NoticeRead).filter(
            NoticeRead.notice_revision_id == rev.id,
            NoticeRead.user_id == current_user.id
        ).first() is not None

        tower = db.query(Tower).filter(Tower.id == rev.tower_id).first() if rev.tower_id else None

        result.append(NoticeRevisionResponse(
            id=rev.id,
            notice_id=rev.notice_id,
            revision_number=rev.revision_number,
            title=rev.title,
            body=body,
            body_en=rev.body_en,
            body_hi=rev.body_hi,
            body_mr=rev.body_mr,
            is_fallback_language=is_fallback,
            fallback_language_label=fallback_label,
            publish_at=rev.publish_at,
            expires_at=rev.expires_at,
            audience=rev.audience,
            tower_id=rev.tower_id,
            tower_number=tower.code if tower else None,
            severity=rev.severity,
            created_at=rev.created_at,
            is_read=is_read,
        ))

    return result


@router.get("/{notice_id}/revisions", response_model=List[NoticeRevisionResponse])
def get_notice_revisions(
    notice_id: str,
    lang: str = Query("en"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if not any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only staff and committee can view full revision history."
        )

    revisions = db.query(NoticeRevision).filter(
        NoticeRevision.notice_id == notice_id
    ).order_by(NoticeRevision.revision_number.desc()).all()

    result = []
    for rev in revisions:
        body, is_fallback, fallback_label = resolve_language_body(rev, lang)
        tower = db.query(Tower).filter(Tower.id == rev.tower_id).first() if rev.tower_id else None
        result.append(NoticeRevisionResponse(
            id=rev.id,
            notice_id=rev.notice_id,
            revision_number=rev.revision_number,
            title=rev.title,
            body=body,
            body_en=rev.body_en,
            body_hi=rev.body_hi,
            body_mr=rev.body_mr,
            is_fallback_language=is_fallback,
            fallback_language_label=fallback_label,
            publish_at=rev.publish_at,
            expires_at=rev.expires_at,
            audience=rev.audience,
            tower_id=rev.tower_id,
            tower_number=tower.code if tower else None,
            severity=rev.severity,
            created_at=rev.created_at,
            is_read=False,
        ))

    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def create_notice_endpoint(
    payload: NoticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if not any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only committee and authorized staff can create notices."
        )

    notice = create_notice(db, payload, current_user.id)
    db.commit()
    db.refresh(notice)
    return {"id": notice.id, "title": notice.title, "status": notice.status}


@router.post("/{notice_id}/revisions", status_code=status.HTTP_201_CREATED)
def update_notice_endpoint(
    notice_id: str,
    payload: NoticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if not any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only committee and authorized staff can edit notices."
        )

    new_rev = update_notice_create_revision(db, notice_id, payload, current_user.id)
    db.commit()
    db.refresh(new_rev)
    return {"notice_id": notice_id, "revision_id": new_rev.id, "revision_number": new_rev.revision_number}


@router.post("/{notice_id}/withdraw")
def withdraw_notice_endpoint(
    notice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if not any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only committee and authorized staff can withdraw notices."
        )

    notice = withdraw_notice(db, notice_id, current_user.id)
    db.commit()
    return {"id": notice.id, "status": notice.status}


@router.post("/revisions/{revision_id}/read")
def mark_revision_read_endpoint(
    revision_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record_notice_read(db, revision_id, current_user.id)
    db.commit()
    return {"status": "ok", "revision_id": revision_id}
