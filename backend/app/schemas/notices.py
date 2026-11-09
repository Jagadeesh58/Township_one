from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body_en: str = Field(..., min_length=5)
    body_hi: Optional[str] = None
    body_mr: Optional[str] = None
    audience: str = "ALL"  # ALL, TOWER
    tower_id: Optional[str] = None
    severity: str = "NORMAL"  # NORMAL, CRITICAL
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class NoticeRevisionResponse(BaseModel):
    id: str
    notice_id: str
    revision_number: int
    title: str
    body: str
    body_en: str
    body_hi: Optional[str] = None
    body_mr: Optional[str] = None
    is_fallback_language: bool = False
    fallback_language_label: Optional[str] = None
    publish_at: datetime
    expires_at: Optional[datetime] = None
    audience: str
    tower_id: Optional[str] = None
    tower_number: Optional[str] = None
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
