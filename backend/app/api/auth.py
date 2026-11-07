"""
Township One — Authentication API Endpoints.

Provides phone OTP challenge request and verification, JWT session issuance,
persistent session logout revocation, and authenticated profile resolution.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_otp_challenge, verify_otp_challenge, create_access_token,
    get_current_user, revoke_token_persisted
)
from backend.app.models.entities import User, Flat
from backend.app.schemas.auth import (
    OTPRequest, OTPVerify, TokenResponse, UserProfileResponse,
    RoleAssignmentResponse, FlatMembershipResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def build_user_profile(user: User, db: Session) -> UserProfileResponse:
    roles = [
        RoleAssignmentResponse(
            role_code=ra.role_code,
            scope_type=ra.scope_type,
            scope_id=ra.scope_id
        )
        for ra in user.role_assignments if ra.is_active
    ]

    flats = []
    for fm in user.flat_memberships:
        if fm.is_active:
            flat = db.query(Flat).filter(Flat.id == fm.flat_id).first()
            if flat:
                flats.append(
                    FlatMembershipResponse(
                        flat_id=flat.id,
                        flat_number=flat.flat_number,
                        floor_number=flat.floor_number,
                        area_sqft=float(flat.area_sqft),
                        member_type=fm.member_type,
                        can_pay_bills=fm.can_pay_bills,
                        can_approve_visitors=fm.can_approve_visitors,
                        can_raise_complaints=fm.can_raise_complaints,
                    )
                )

    return UserProfileResponse(
        id=user.id,
        phone=user.phone,
        name=user.name,
        email=user.email,
        roles=roles,
        flats=flats,
    )


@router.post("/otp/request")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered resident or staff account found with this phone number."
        )

    otp = create_otp_challenge(phone)
    response_data = {
        "message": "OTP sent successfully to registered mobile number.",
        "phone": phone,
        "expires_in_seconds": settings.OTP_EXPIRY_SECONDS
    }

    # Only include demo hint in non-production environments
    if settings.APP_ENV.lower() != "production":
        response_data["demo_hint"] = f"Demo OTP is {otp}"

    return response_data


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(payload: OTPVerify, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    is_valid = verify_otp_challenge(phone, payload.otp.strip())
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP code. Please check and try again.")

    token = create_access_token(data={"sub": user.id, "phone": user.phone})
    profile = build_user_profile(user, db)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=profile
    )


@router.get("/me", response_model=UserProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return build_user_profile(current_user, db)


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        revoke_token_persisted(token=token, user_id=current_user.id, db=db)
    return {"message": "Logged out successfully. Session revoked."}
