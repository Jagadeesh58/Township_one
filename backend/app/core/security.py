from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.entities import User, UserRoleAssignment, FlatMembership, Flat

security = HTTPBearer(auto_error=False)

# In-memory OTP Store: {phone: {"otp": str, "expires_at": datetime, "attempts": int, "used": bool}}
OTP_STORE: Dict[str, Dict[str, Any]] = {}
REVOKED_TOKENS: set = set()


def create_otp_challenge(phone: str) -> str:
    now = datetime.now(timezone.utc)
    # Clear older or expired OTP
    otp_code = settings.DEMO_OTP_CODE  # Deterministic demo code 123456
    OTP_STORE[phone] = {
        "otp": otp_code,
        "expires_at": now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
        "attempts": 0,
        "used": False
    }
    return otp_code


def verify_otp_challenge(phone: str, otp: str) -> bool:
    record = OTP_STORE.get(phone)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active OTP challenge found. Please request an OTP.")

    if record["used"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has already been used.")

    now = datetime.now(timezone.utc)
    if now > record["expires_at"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP has expired. Please request a new one.")

    record["attempts"] += 1
    if record["attempts"] > 3:
        record["used"] = True
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many invalid attempts. OTP invalidated.")

    if record["otp"] != otp:
        return False

    # Mark as used (one-time use)
    record["used"] = True
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a Bearer token."
        )

    token = credentials.credentials
    if token in REVOKED_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please sign in again."
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")
    return user


def require_role(allowed_roles: List[str]):
    def role_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        active_roles = [
            ra.role_code for ra in current_user.role_assignments if ra.is_active
        ]
        if "ADMIN" in active_roles:
            return current_user  # Admin has full administrative override

        if not any(role in active_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def verify_flat_access(user: User, flat_id: str, action: str = "read") -> FlatMembership:
    """Server-side check ensuring user has permission to access the target flat."""
    # Check if user has active membership in this flat
    membership = next((m for m in user.flat_memberships if m.flat_id == flat_id and m.is_active), None)
    
    # Check if user is staff/committee with township-wide scope
    user_roles = [ra.role_code for ra in user.role_assignments if ra.is_active]
    if any(r in ["HELPDESK", "ACCOUNTS", "COMMITTEE", "ADMIN"] for r in user_roles):
        return None  # Authorized staff

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permissions for this flat."
        )

    if action == "pay" and not membership.can_pay_bills:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your membership does not permit bill payment.")
    if action == "visitor" and not membership.can_approve_visitors:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your membership does not permit visitor approval.")
    if action == "complaint" and not membership.can_raise_complaints:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your membership does not permit raising complaints.")

    return membership
