from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    phone: str | None = Field(None, max_length=20)
    purpose: str = Field(..., min_length=2, max_length=100)
    photo_id: str | None = None
    guest_code: str | None = Field(None, min_length=6, max_length=6)
    pre_approval_credential: str | None = Field(None, min_length=32, max_length=4096)
    client_event_id: str | None = None
    source: str = "ONLINE"


class VisitorEntryResponse(BaseModel):
    id: str
    gate_id: str
    flat_id: str
    flat_number: str | None = None
    tower_number: str | None = None
    visitor_name: str
    phone: str | None = None
    purpose: str
    status: VisitorStatus
    created_by_guard: str | None = None
    approval_decided_by: str | None = None
    approval_decided_at: datetime | None = None
    admitted_at: datetime | None = None
    exited_at: datetime | None = None
    photo_id: str | None = None
    photo_url: str | None = None
    pre_approval_id: str | None = None
    source: str
    client_event_id: str | None = None
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
    phone: str | None = Field(None, max_length=20)
    purpose: str = Field(..., min_length=2, max_length=100)
    gate_id: str | None = None
    valid_from: datetime
    valid_until: datetime
    max_uses: int = Field(1, ge=1, le=10)


class PreApprovalResponse(BaseModel):
    id: str
    flat_id: str
    guest_name: str
    phone: str | None = None
    purpose: str
    gate_id: str | None = None
    valid_from: datetime
    valid_until: datetime
    max_uses: int
    used_count: int
    code: str | None = None  # Returned only on creation
    credential_jwt: str | None = None
    is_revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuestCodeVerifyRequest(BaseModel):
    gate_id: str
    code: str | None = None
    credential_jwt: str | None = None


class GuestCodeVerifyResponse(BaseModel):
    valid: bool
    message: str
    pre_approval_id: str | None = None
    flat_id: str | None = None
    guest_name: str | None = None
    remaining_uses: int = 0
    conflict_flagged: bool = False


class GateDeviceEnrollmentRequest(BaseModel):
    device_id: str = Field(..., min_length=16, max_length=64)
    generation_id: str = Field(..., min_length=16, max_length=64)
    gate_id: str


class GateDeviceEnrollmentResponse(BaseModel):
    device_id: str
    generation_id: str
    gate_id: str
    last_sequence: int
    is_active: bool


class OfflineSyncItem(BaseModel):
    client_event_id: str = Field(..., min_length=16, max_length=64)
    photo_uuid: str = Field(..., min_length=16, max_length=64)
    gate_id: str
    flat_id: str
    visitor_name: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=20)
    purpose: str = Field(..., min_length=2, max_length=100)
    capture_time: datetime
    photo_sha256: str = Field(..., pattern=r"^[a-fA-F0-9]{64}$")
    device_id: str = Field(..., min_length=16, max_length=64)
    device_generation_id: str = Field(..., min_length=16, max_length=64)
    device_sequence: int = Field(..., ge=1)
    time_anchor_payload: dict[str, str | int]
    time_anchor_signature: str = Field(..., min_length=16)
    pre_approval_credential: str | None = None


class OfflineSyncResponse(BaseModel):
    processed_count: int
    acknowledged_ids: list[str]
    conflicts: list[dict]
