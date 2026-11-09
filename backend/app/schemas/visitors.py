from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class VisitorStatus(str, Enum):
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ADMITTED = "ADMITTED"
    EXITED = "EXITED"
    EXPIRED = "EXPIRED"
    OVERRIDDEN_ADMIT = "OVERRIDDEN_ADMIT"


class VisitorEntryCreate(BaseModel):
    gate_id: str
    flat_id: str
    visitor_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    purpose: str = Field(..., min_length=2, max_length=100)
    photo_id: Optional[str] = None
    client_event_id: Optional[str] = None
    source: str = "ONLINE"


class VisitorEntryResponse(BaseModel):
    id: str
    gate_id: str
    flat_id: str
    flat_number: Optional[str] = None
    tower_number: Optional[str] = None
    visitor_name: str
    phone: Optional[str] = None
    purpose: str
    status: VisitorStatus
    created_by_guard: Optional[str] = None
    approval_decided_by: Optional[str] = None
    approval_decided_at: Optional[datetime] = None
    admitted_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None
    photo_id: Optional[str] = None
    photo_url: Optional[str] = None
    pre_approval_id: Optional[str] = None
    source: str
    client_event_id: Optional[str] = None
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisitorApprovalDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT"]


class SupervisorOverrideRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class PreApprovalCreate(BaseModel):
    flat_id: str
    guest_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    purpose: str = Field(..., min_length=2, max_length=100)
    gate_id: Optional[str] = None
    valid_from: datetime
    valid_until: datetime
    max_uses: int = Field(1, ge=1, le=10)


class PreApprovalResponse(BaseModel):
    id: str
    flat_id: str
    guest_name: str
    phone: Optional[str] = None
    purpose: str
    gate_id: Optional[str] = None
    valid_from: datetime
    valid_until: datetime
    max_uses: int
    used_count: int
    code: Optional[str] = None  # Returned only on creation
    credential_jwt: Optional[str] = None
    is_revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestCodeVerifyRequest(BaseModel):
    gate_id: str
    code: Optional[str] = None
    credential_jwt: Optional[str] = None


class GuestCodeVerifyResponse(BaseModel):
    valid: bool
    message: str
    pre_approval_id: Optional[str] = None
    flat_id: Optional[str] = None
    guest_name: Optional[str] = None
    remaining_uses: int = 0
    conflict_flagged: bool = False


class OfflineSyncItem(BaseModel):
    client_event_id: str
    gate_id: str
    flat_id: str
    visitor_name: str
    phone: Optional[str] = None
    purpose: str
    capture_time: datetime
    photo_sha256: Optional[str] = None
    pre_approval_id: Optional[str] = None


class OfflineSyncRequest(BaseModel):
    events: List[OfflineSyncItem]


class OfflineSyncResponse(BaseModel):
    processed_count: int
    acknowledged_ids: List[str]
    conflicts: List[dict]
