from decimal import Decimal
"""
Township One — Authentication API Endpoints.

Provides phone OTP challenge request and verification, JWT session issuance,
persistent session logout revocation, and authenticated profile resolution.
"""

from typing import Optional
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response
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
                        area_sqft=str(Decimal(str(flat.area_sqft))),
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
def request_otp(
    payload: OTPRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered resident or staff account found with this phone number."
        )

    client_ip = request.client.host if request.client else None
    otp = create_otp_challenge(phone, db=db, ip_address=client_ip)
    response_data = {
        "message": "OTP sent successfully to registered mobile number.",
        "phone": phone,
        "expires_in_seconds": settings.OTP_EXPIRY_SECONDS
    }

    # Only include demo hint in development or demo environments
    if settings.APP_ENV.lower() in ("development", "demo"):
        response_data["demo_hint"] = f"Demo OTP is {otp}"

    return response_data


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(
    payload: OTPVerify,
    response: Response,
    db: Session = Depends(get_db)
):
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    is_valid = verify_otp_challenge(phone, payload.otp.strip(), db=db)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP code. Please check and try again.")

    token = create_access_token(data={"sub": user.id, "phone": user.phone})
    csrf_token = secrets.token_urlsafe(32)
    is_secure = (settings.APP_ENV.lower() not in ["development", "test"])

    # HttpOnly session cookie
    response.set_cookie(
        key="township_session",
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        path="/"
    )
    # Readable double-submit CSRF cookie
    response.set_cookie(
        key="township_csrf",
        value=csrf_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,
        samesite="lax",
        secure=is_secure,
        path="/"
    )

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
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = request.cookies.get("township_session")
    if token:
        revoke_token_persisted(token=token, user_id=current_user.id, db=db)

    is_secure = (settings.APP_ENV.lower() not in ["development", "test"])
    response.delete_cookie(
        key="township_session",
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_secure
    )
    response.delete_cookie(
        key="township_csrf",
        path="/",
        httponly=False,
        samesite="lax",
        secure=is_secure
    )
    return {"message": "Logged out successfully. Session revoked."}
