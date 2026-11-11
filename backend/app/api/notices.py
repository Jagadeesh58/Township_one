from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import (
    Flat,
    FlatMembership,
    Notice,
    NoticeRead,
    NoticeRevision,
    Tower,
    User,
)
from backend.app.schemas.notices import (
    NoticeCreate,
    NoticeRevisionResponse,
)
from backend.app.services.amenity_service import get_effective_now
from backend.app.services.notice_service import (
    create_notice,
    publish_notice,
    record_notice_read,
    resolve_language_body,
    update_notice_create_revision,
    withdraw_notice,
)

router = APIRouter(prefix="/notices", tags=["notices"])


def get_user_roles(user: User) -> list[str]:
    if user.is_active is False:
        return []
    return [r.role_code for r in user.role_assignments if r.is_active is True]


def can_manage_notices(user: User) -> bool:
    # Help Desk retains the staff publishing rights already used by the workflow.
    return any(role in ("ADMIN", "COMMITTEE", "MANAGEMENT", "HELPDESK", "HELP_DESK") for role in get_user_roles(user))


def as_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get("", response_model=list[NoticeRevisionResponse])
def list_active_notices(
    lang: str = Query("en"),
    tower_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    now = get_effective_now()
    is_staff = any(r in ("ADMIN", "HELPDESK", "HELP_DESK", "COMMITTEE") for r in roles)

    query = db.query(Notice).filter(Notice.status == "PUBLISHED")

    if not is_staff:
        # Resident scoping: find towers where resident holds flats
        user_tower_ids = (
            db.query(Flat.tower_id)
            .join(FlatMembership)
            .filter(FlatMembership.user_id == current_user.id, FlatMembership.is_active.is_(True))
            .distinct()
            .all()
        )
        resident_towers = [t[0] for t in user_tower_ids]

        # Filter by expiry and audience
        query = query.filter(
            Notice.published_at <= now,
            (Notice.expires_at.is_(None)) | (Notice.expires_at >= now),
            (Notice.target_audience == "ALL") | (Notice.target_tower_id.in_(resident_towers)),
        )
    else:
        if tower_id:
            query = query.filter((Notice.target_audience == "ALL") | (Notice.target_tower_id == tower_id))

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
        is_read = (
            db.query(NoticeRead)
            .filter(NoticeRead.notice_revision_id == rev.id, NoticeRead.user_id == current_user.id)
            .first()
            is not None
        )

        tower = db.query(Tower).filter(Tower.id == rev.tower_id).first() if rev.tower_id else None

        result.append(
            NoticeRevisionResponse(
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
            )
        )

    return result


@router.get("/manage")
def list_managed_notices(
    lang: str = Query("en"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")
    notices = db.query(Notice).order_by(Notice.id.desc()).all()
    result = []
    for notice in notices:
        revision = db.query(NoticeRevision).filter(NoticeRevision.id == notice.current_revision_id).first()
        if not revision:
            continue
        body, is_fallback, fallback_label = resolve_language_body(revision, lang)
        tower = db.query(Tower).filter(Tower.id == revision.tower_id).first() if revision.tower_id else None
        result.append(
            {
                "id": notice.id,
                "status": notice.status,
                "revision_count": db.query(NoticeRevision).filter(NoticeRevision.notice_id == notice.id).count(),
                "current_revision": NoticeRevisionResponse(
                    id=revision.id,
                    notice_id=revision.notice_id,
                    revision_number=revision.revision_number,
                    title=revision.title,
                    body=body,
                    body_en=revision.body_en,
                    body_hi=revision.body_hi,
                    body_mr=revision.body_mr,
                    is_fallback_language=is_fallback,
                    fallback_language_label=fallback_label,
                    publish_at=revision.publish_at,
                    expires_at=revision.expires_at,
                    audience=revision.audience,
                    tower_id=revision.tower_id,
                    tower_number=tower.code if tower else None,
                    severity=revision.severity,
                    created_at=revision.created_at,
                    is_read=False,
                ).model_dump(),
            }
        )
    return result


@router.post("/{notice_id}/publish")
def publish_notice_endpoint(
    notice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")
    notice = publish_notice(db, notice_id, current_user.id)
    db.commit()
    return {"id": notice.id, "status": notice.status, "published_at": notice.published_at}


@router.get("/{notice_id}/revisions", response_model=list[NoticeRevisionResponse])
def get_notice_revisions(
    notice_id: str,
    lang: str = Query("en"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")

    revisions = (
        db.query(NoticeRevision)
        .filter(NoticeRevision.notice_id == notice_id)
        .order_by(NoticeRevision.revision_number.desc())
        .all()
    )

    result = []
    for rev in revisions:
        body, is_fallback, fallback_label = resolve_language_body(rev, lang)
        tower = db.query(Tower).filter(Tower.id == rev.tower_id).first() if rev.tower_id else None
        result.append(
            NoticeRevisionResponse(
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
            )
        )

    return result


@router.post("", status_code=status.HTTP_201_CREATED)
def create_notice_endpoint(
    payload: NoticeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")

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
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")

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
    if not can_manage_notices(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Committee notice access is required.")

    notice = withdraw_notice(db, notice_id, current_user.id)
    db.commit()
    return {"id": notice.id, "status": notice.status}


@router.post("/revisions/{revision_id}/read")
def mark_revision_read_endpoint(
    revision_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revision = db.query(NoticeRevision).filter(NoticeRevision.id == revision_id).first()
    if not revision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice revision not found.")
    notice = db.query(Notice).filter(Notice.id == revision.notice_id).first()
    if not notice or notice.status != "PUBLISHED":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice is not available.")
    if not can_manage_notices(current_user):
        now = get_effective_now()
        published_at = as_utc(notice.published_at)
        expires_at = as_utc(notice.expires_at)
        if (published_at and published_at > now) or (expires_at and expires_at < now):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice is not available.")
        memberships = (
            db.query(FlatMembership)
            .join(Flat)
            .filter(
                FlatMembership.user_id == current_user.id,
                FlatMembership.is_active.is_(True),
            )
            .all()
        )
        if not memberships:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active flat membership is required.")
        tower_ids = {membership.flat.tower_id for membership in memberships}
        if revision.audience != "ALL" and revision.tower_id not in tower_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Notice is outside this resident's audience."
            )
    try:
        record_notice_read(db, revision_id, current_user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"status": "ok", "revision_id": revision_id}
