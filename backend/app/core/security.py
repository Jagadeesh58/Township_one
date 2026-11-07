"""
Township One — Authentication and Role-Based Access Control Core.

Responsibility:
- Cryptographic OTP generation, salt-hashed storage, rate limiting, and single-use verification.
- Cryptographic JWT access token issuance (PyJWT HS256) with unique JTI identifiers.
- Persistent session revocation backed by database table `revoked_tokens` and in-memory cache.
- Resource-scoped authorization: flat membership, family permissions, committee aggregate boundary, staff boundaries.

Documentation:
docs/authentication-and-access-control.md
"""

import uuid
import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.entities import User, UserRoleAssignment, FlatMembership, Flat, RevokedToken, OTPChallenge
from backend.app.services.sms import get_sms_provider

security = HTTPBearer(auto_error=False)

# In-memory OTP Store: {phone: {"otp_hash": str, "salt": str, "expires_at": datetime, "attempts": int, "used": bool, "request_timestamps": List[datetime]}}
OTP_STORE: Dict[str, Dict[str, Any]] = {}
REVOKED_TOKENS: set = set()


def create_otp_challenge(phone: str, db: Optional[Session] = None) -> str:
    """
    Creates an OTP challenge with rate-limiting, salt-hashed storage, and configurable expiration.
    In production mode, a cryptographically secure random 6-digit OTP is generated and dispatched
    via SMSProvider. In dev/test mode, the deterministic demo code is used.
    When a database session is provided, OTP challenges are persistently stored in `otp_challenges` table.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=10)

    # Rate limiting: max 5 OTP requests per 10 minutes
    if db is not None:
        recent_count = db.query(OTPChallenge).filter(
            OTPChallenge.phone == phone,
            OTPChallenge.created_at > window_start
        ).count()
        if recent_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: Too many OTP requests for this phone number. Please wait before retrying."
            )
    else:
        record = OTP_STORE.get(phone, {"request_timestamps": []})
        recent_requests = [ts for ts in record.get("request_timestamps", []) if ts > window_start]
        if len(recent_requests) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: Too many OTP requests for this phone number. Please wait before retrying."
            )

    sms_provider = get_sms_provider()

    if settings.APP_ENV.lower() == "production":
        otp_code = f"{secrets.randbelow(900000) + 100000:06d}"
    else:
        otp_code = settings.DEMO_OTP_CODE

    salt = secrets.token_hex(16)
    otp_hash = hashlib.sha256(f"{salt}:{otp_code}".encode("utf-8")).hexdigest()
    expires_at = now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)

    if db is not None:
        challenge = OTPChallenge(
            phone=phone,
            otp_hash=otp_hash,
            salt=salt,
            expires_at=expires_at,
            attempts=0,
            is_used=False,
            created_at=now
        )
        db.add(challenge)
        db.commit()

    # Maintain in-memory cache as well
    rec = OTP_STORE.setdefault(phone, {"request_timestamps": []})
    rec_timestamps = [ts for ts in rec.get("request_timestamps", []) if ts > window_start]
    rec_timestamps.append(now)
    OTP_STORE[phone] = {
        "otp_hash": otp_hash,
        "salt": salt,
        "expires_at": expires_at,
        "attempts": 0,
        "used": False,
        "request_timestamps": rec_timestamps
    }

    # Dispatch via SMS provider
    sms_provider.send_otp(phone, otp_code)

    return otp_code


def verify_otp_challenge(phone: str, otp: str, db: Optional[Session] = None) -> bool:
    """
    Verifies OTP challenge enforcing salt-hash validation, expiration, single-use, and max 3 invalid attempts.
    """
    now = datetime.now(timezone.utc)

    if db is not None:
        challenge = db.query(OTPChallenge).filter(
            OTPChallenge.phone == phone
        ).order_by(OTPChallenge.created_at.desc()).first()

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active OTP challenge found. Please request an OTP."
            )

        if challenge.is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has already been used."
            )

        exp = challenge.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )

        challenge.attempts += 1
        if challenge.attempts > 3:
            challenge.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid attempts. OTP invalidated."
            )

        attempt_hash = hashlib.sha256(f"{challenge.salt}:{otp}".encode("utf-8")).hexdigest()
        if not hmac.compare_digest(challenge.otp_hash, attempt_hash):
            db.commit()
            return False

        challenge.is_used = True
        db.commit()

        if phone in OTP_STORE:
            OTP_STORE[phone]["used"] = True

        return True

    # Fallback to in-memory store
    record = OTP_STORE.get(phone)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP challenge found. Please request an OTP."
        )

    if record["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has already been used."
        )

    if now > record["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    record["attempts"] += 1
    if record["attempts"] > 3:
        record["used"] = True
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invalid attempts. OTP invalidated."
        )

    attempt_hash = hashlib.sha256(f"{record['salt']}:{otp}".encode("utf-8")).hexdigest()
    if not hmac.compare_digest(record["otp_hash"], attempt_hash):
        return False

    record["used"] = True
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a cryptographically signed JWT with unique JTI identifier for revocation tracking.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "iat": now, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def revoke_token_persisted(token: str, user_id: str, db: Session):
    """
    Persists token revocation to database table `revoked_tokens` and in-memory set.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
        jti = payload.get("jti") or token
        exp_ts = payload.get("exp")
        exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else datetime.now(timezone.utc) + timedelta(days=1)
    except Exception:
        jti = token
        exp_dt = datetime.now(timezone.utc) + timedelta(days=1)

    REVOKED_TOKENS.add(jti)
    REVOKED_TOKENS.add(token)

    # Persist to database for multi-process and restart survival
    try:
        revoked_rec = RevokedToken(
            token_jti=jti,
            user_id=user_id,
            expires_at=exp_dt
        )
        db.add(revoked_rec)
        db.commit()
    except Exception:
        db.rollback()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates bearer token, checks database & in-memory revocation, and resolves active user.
    """
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
        jti = payload.get("jti")
        if jti and jti in REVOKED_TOKENS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please sign in again."
            )

        # Check database revocation table
        if jti:
            is_db_revoked = db.query(RevokedToken).filter(RevokedToken.token_jti == jti).first()
            if is_db_revoked:
                REVOKED_TOKENS.add(jti)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked. Please sign in again."
                )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials."
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Invalid or expired token."
        )

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found."
        )
    return user


def require_role(allowed_roles: List[str]):
    """
    Enforces server-side role-based access control.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = [ra.role_code for ra in current_user.role_assignments if ra.is_active]
        if not any(role in user_roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required role in {allowed_roles}. Your roles: {user_roles}"
            )
        return current_user
    return role_checker


def verify_flat_access(user: User, flat_id: str, action: str = "read") -> FlatMembership:
    """
    Strict server-side resource authorization:
    - Block Committee members from resident-level financial drill-downs (HTTP 403).
    - Block Help Desk and Security Guards from financial records (HTTP 403).
    - Enforce active FlatMembership and action permissions (`can_pay_bills`).
    """
    user_roles = [ra.role_code for ra in user.role_assignments if ra.is_active]

    # SECURITY FIX C: Committee members are strictly barred from individual flat finances
    if "COMMITTEE" in user_roles and "ADMIN" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Committee members can only access aggregate reports, not individual flat records."
        )

    # Help Desk and Guards cannot access resident billing or payments
    if action in ["read", "pay"]:
        if "GUARD" in user_roles and "ADMIN" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Gate security staff do not have access to billing or payment records."
            )
        if "HELPDESK" in user_roles and "ADMIN" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Helpdesk staff cannot access resident billing or payment records."
            )

    # Admins and Accounts staff can read financial summaries
    if "ADMIN" in user_roles or ("ACCOUNTS" in user_roles and action == "read"):
        dummy_membership = FlatMembership(
            flat_id=flat_id,
            user_id=user.id,
            member_type="STAFF",
            can_pay_bills=False,
            can_approve_visitors=False,
            can_raise_complaints=False
        )
        return dummy_membership

    # Ordinary resident / tenant / family membership verification
    membership = next(
        (fm for fm in user.flat_memberships if fm.flat_id == flat_id and fm.is_active),
        None
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have an active membership for this flat."
        )

    if action == "pay" and not membership.can_pay_bills:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Your flat membership does not permit bill payment."
        )

    if action == "approve_visitor" and not membership.can_approve_visitors:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Your flat membership does not permit visitor approvals."
        )

    if action == "raise_complaint" and not membership.can_raise_complaints:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Your flat membership does not permit lodging complaints."
        )

    return membership
