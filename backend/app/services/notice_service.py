from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    AuditEvent,
    Notice,
    NoticeRead,
    NoticeRevision,
)
from backend.app.schemas.notices import (
    NoticeCreate,
)
from backend.app.services.amenity_service import get_effective_now


def resolve_language_body(revision: NoticeRevision, lang: str = "en") -> tuple[str, bool, str | None]:
    """
    Returns (body_text, is_fallback, fallback_label).
    If requested language is unavailable, gracefully falls back to English with clear indicator.
    """
    lang = (lang or "en").lower()
    if lang == "mr" and revision.body_mr and revision.body_mr.strip():
        return revision.body_mr, False, None
    elif lang == "hi" and revision.body_hi and revision.body_hi.strip():
        return revision.body_hi, False, None
    elif lang in ("mr", "hi"):
        return revision.body_en, True, "Shown in English"
    return revision.body_en, False, None


def create_notice(db: Session, payload: NoticeCreate, author_user_id: str) -> Notice:
    now = get_effective_now()
    publish_at = payload.publish_at or now

    is_published = payload.status == "PUBLISHED"
    notice = Notice(
        title=payload.title,
        content=payload.body_en,
        target_audience=payload.audience,
        target_tower_id=payload.tower_id,
        priority=payload.severity,
        status=payload.status,
        published_at=publish_at if is_published else None,
        expires_at=payload.expires_at,
    )
    db.add(notice)
    db.flush()

    revision = NoticeRevision(
        notice_id=notice.id,
        revision_number=1,
        title=payload.title,
        body_en=payload.body_en,
        body_hi=payload.body_hi,
        body_mr=payload.body_mr,
        publish_at=publish_at,
        expires_at=payload.expires_at,
        audience=payload.audience,
        tower_id=payload.tower_id,
        severity=payload.severity,
        created_by_user_id=author_user_id,
        created_at=now,
    )
    db.add(revision)
    db.flush()

    notice.current_revision_id = revision.id

    audit = AuditEvent(
        entity_type="NOTICE",
        entity_id=notice.id,
        action="PUBLISH_NOTICE" if is_published else "CREATE_NOTICE_DRAFT",
        actor_user_id=author_user_id,
        actor_role="COMMITTEE",
        reason=f"{'Published' if is_published else 'Saved draft'} notice '{notice.title}' (Revision 1, Audience: {payload.audience}).",
    )
    db.add(audit)
    db.flush()
    return notice


def update_notice_create_revision(
    db: Session, notice_id: str, payload: NoticeCreate, author_user_id: str
) -> NoticeRevision:
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found.")

    latest_rev = (
        db.query(NoticeRevision)
        .filter(NoticeRevision.notice_id == notice_id)
        .order_by(NoticeRevision.revision_number.desc())
        .first()
    )

    next_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1
    now = get_effective_now()
    publish_at = payload.publish_at or now

    new_revision = NoticeRevision(
        notice_id=notice.id,
        revision_number=next_rev_num,
        title=payload.title,
        body_en=payload.body_en,
        body_hi=payload.body_hi,
        body_mr=payload.body_mr,
        publish_at=publish_at,
        expires_at=payload.expires_at,
        audience=payload.audience,
        tower_id=payload.tower_id,
        severity=payload.severity,
        created_by_user_id=author_user_id,
        created_at=now,
    )
    db.add(new_revision)
    db.flush()

    notice.title = payload.title
    notice.content = payload.body_en
    notice.target_audience = payload.audience
    notice.target_tower_id = payload.tower_id
    notice.priority = payload.severity
    notice.current_revision_id = new_revision.id
    notice.expires_at = payload.expires_at
    if notice.status == "PUBLISHED":
        notice.published_at = publish_at

    audit = AuditEvent(
        entity_type="NOTICE_REVISION",
        entity_id=new_revision.id,
        action="REVISE_NOTICE",
        actor_user_id=author_user_id,
        actor_role="STAFF",
        reason=f"Created Revision {next_rev_num} for notice {notice_id}.",
    )
    db.add(audit)
    db.flush()
    return new_revision


def publish_notice(db: Session, notice_id: str, author_user_id: str) -> Notice:
    notice = db.query(Notice).filter(Notice.id == notice_id).with_for_update().first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found.")
    if notice.status == "WITHDRAWN":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A withdrawn notice cannot be published again."
        )
    revision = db.query(NoticeRevision).filter(NoticeRevision.id == notice.current_revision_id).first()
    if not revision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notice has no current revision.")
    notice.status = "PUBLISHED"
    notice.published_at = revision.publish_at
    notice.expires_at = revision.expires_at
    db.add(
        AuditEvent(
            entity_type="NOTICE",
            entity_id=notice.id,
            action="PUBLISH_NOTICE",
            actor_user_id=author_user_id,
            actor_role="COMMITTEE",
            reason=f"Published notice {notice.id}, revision {revision.revision_number}.",
        )
    )
    db.flush()
    return notice


def withdraw_notice(db: Session, notice_id: str, author_user_id: str) -> Notice:
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found.")

    notice.status = "WITHDRAWN"

    audit = AuditEvent(
        entity_type="NOTICE",
        entity_id=notice.id,
        action="WITHDRAW_NOTICE",
        actor_user_id=author_user_id,
        actor_role="STAFF",
        reason=f"Withdrew notice '{notice.title}'.",
    )
    db.add(audit)
    db.flush()
    return notice


def record_notice_read(db: Session, revision_id: str, user_id: str) -> NoticeRead:
    existing = (
        db.query(NoticeRead)
        .filter(
            NoticeRead.notice_revision_id == revision_id,
            NoticeRead.user_id == user_id,
        )
        .first()
    )
    if existing:
        return existing

    read_record = NoticeRead(
        notice_revision_id=revision_id,
        user_id=user_id,
        read_at=datetime.now(UTC),
    )
    db.add(read_record)
    db.flush()
    return read_record
