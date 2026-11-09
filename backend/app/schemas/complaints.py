from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreateRequest(BaseModel):
    flat_id: str
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=5, max_length=2000)
    language: str | None = "en"


class ComplaintEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    notes: str | None = None
    created_at: datetime
    actor_user_id: str | None = None


class ClassificationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    model_version: str | None = None
    prompt_version: str | None = None
    predicted_category: str
    predicted_urgency: str
    confidence: float | None = None
    fallback_used: bool = False
    needs_human_review: bool = False
    created_at: datetime


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    flat_id: str
    flat_number: str | None = None
    tower_id: str | None = None
    tower_name: str | None = None
    title: str
    description: str
    category: str
    urgency: str
    status: str
    version: int = 1
    is_safety_escalation: bool = False
    language: str = "en"
    assigned_staff_id: str | None = None
    assigned_staff_name: str | None = None
    assigned_team: str | None = None
    created_at: datetime
    first_response_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    rating: int | None = None
    feedback: str | None = None
    reopen_reason: str | None = None
    photo_url: str | None = None
    sla_remaining_minutes: int | None = None
    is_overdue: bool = False
    events: list[ComplaintEventResponse] | None = None
    classification_decision: ClassificationDecisionResponse | None = None


class StatusTransitionRequest(BaseModel):
    status: str
    notes: str | None = None
    expected_version: int | None = None


class ClassificationCorrectionRequest(BaseModel):
    category: str
    urgency: str
    reason: str
    expected_version: int


class RatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    feedback: str | None = None


class ReopenRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class LinkDuplicateRequest(BaseModel):
    target_complaint_id: str


class SafetyEventActionRequest(BaseModel):
    action: str  # ACKNOWLEDGE, DISMISS
    notes: str | None = None


class SafetyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    complaint_id: str
    event_type: str
    details: str | None = None
    status: str
    created_at: datetime
    ticket_number: str | None = None
    flat_number: str | None = None
