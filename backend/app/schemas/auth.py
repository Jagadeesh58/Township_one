from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    phone: str = Field(..., description="10-digit mobile number, e.g. 9876543210")


class OTPVerify(BaseModel):
    phone: str
    otp: str = Field(..., description="6-digit OTP code, demo code is 123456")


class RoleAssignmentResponse(BaseModel):
    role_code: str
    scope_type: str
    scope_id: str | None = None


class FlatMembershipResponse(BaseModel):
    flat_id: str
    flat_number: str
    floor_number: int
    area_sqft: str
    member_type: str
    can_pay_bills: bool
    can_approve_visitors: bool
    can_raise_complaints: bool


class UserProfileResponse(BaseModel):
    id: str
    phone: str
    name: str
    email: str | None = None
    roles: list[RoleAssignmentResponse]
    flats: list[FlatMembershipResponse]


class AuthResponse(BaseModel):
    user: UserProfileResponse
