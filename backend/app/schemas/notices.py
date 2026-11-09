from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body_en: str = Field(..., min_length=5)
    body_hi: str | None = None
    body_mr: str | None = None
    audience: str = "ALL"  # ALL, TOWER
    tower_id: str | None = None
    severity: str = "NORMAL"  # NORMAL, CRITICAL
    publish_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeRevisionResponse(BaseModel):
    id: str
    notice_id: str
    revision_number: int
    title: str
    body: str
    body_en: str
    body_hi: str | None = None
    body_mr: str | None = None
    is_fallback_language: bool = False
    fallback_language_label: str | None = None
    publish_at: datetime
    expires_at: datetime | None = None
    audience: str
    tower_id: str | None = None
    tower_number: str | None = None
    severity: str
    created_at: datetime
    is_read: bool = False

    model_config = ConfigDict(from_attributes=True)


class NoticeItemResponse(BaseModel):
    id: str
    status: str
    current_revision: NoticeRevisionResponse
    revision_count: int

    model_config = ConfigDict(from_attributes=True)
