from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreateRequest(BaseModel):
    flat_id: str
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5, max_length=2000)
    language: Optional[str] = "en"


class ComplaintEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    actor_user_id: Optional[str] = None


class ClassificationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    predicted_category: str
    predicted_urgency: str
    confidence: Optional[float] = None
    fallback_used: bool = False
    needs_human_review: bool = False
    created_at: datetime


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    flat_id: str
    flat_number: Optional[str] = None
    tower_id: Optional[str] = None
    tower_name: Optional[str] = None
    title: str
    description: str
    category: str
    urgency: str
    status: str
    version: int = 1
    is_safety_escalation: bool = False
    language: str = "en"
    assigned_staff_id: Optional[str] = None
    assigned_staff_name: Optional[str] = None
    assigned_team: Optional[str] = None
    created_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    reopen_reason: Optional[str] = None
    photo_url: Optional[str] = None
    sla_remaining_minutes: Optional[int] = None
    is_overdue: bool = False
    events: Optional[List[ComplaintEventResponse]] = None
    classification_decision: Optional[ClassificationDecisionResponse] = None


class StatusTransitionRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    expected_version: Optional[int] = None


class ClassificationCorrectionRequest(BaseModel):
    category: str
    urgency: str
    reason: str
    expected_version: int


class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class ReopenRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class LinkDuplicateRequest(BaseModel):
    target_complaint_id: str


class SafetyEventActionRequest(BaseModel):
    action: str  # ACKNOWLEDGE, DISMISS
    notes: Optional[str] = None


class SafetyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_id: str
    event_type: str
    details: Optional[str] = None
    status: str
    created_at: datetime
    ticket_number: Optional[str] = None
    flat_number: Optional[str] = None
