from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from backend.app.models.entities import (
    Amenity,
    AmenitySlot,
    AmenityRule,
    AmenityClosure,
    AmenityBooking,
    FlatMembership,
    AuditEvent,
)
from backend.app.schemas.amenities import (
    AmenityBookingCreate,
    AmenityClosureCreate,
)


def get_effective_now() -> datetime:
    try:
        from backend.app.core.config import settings
        dt = datetime.fromisoformat(settings.DEMO_AS_OF_DATE.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def get_slot_with_lock(db: Session, slot_id: str) -> AmenitySlot:
    """Acquires row-level exclusive lock on PostgreSQL; falls back gracefully on SQLite."""
    try:
        slot = db.query(AmenitySlot).filter(AmenitySlot.id == slot_id).with_for_update().first()
    except Exception:
        slot = db.query(AmenitySlot).filter(AmenitySlot.id == slot_id).first()
    return slot


def book_amenity_slot(
    db: Session,
    payload: AmenityBookingCreate,
    user_id: str
) -> AmenityBooking:
    # 1. Idempotency check
    existing = db.query(AmenityBooking).filter(
        AmenityBooking.idempotency_key == payload.idempotency_key
    ).first()
    if existing:
        return existing

    # 2. Authorization: Resident must have membership in flat
    membership = db.query(FlatMembership).filter(
        FlatMembership.flat_id == payload.flat_id,
        FlatMembership.user_id == user_id,
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User does not hold active membership in this flat."
        )

    # 3. Lock slot row and verify existence
    slot = get_slot_with_lock(db, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity slot not found.")

    amenity = db.query(Amenity).filter(Amenity.id == slot.amenity_id).first()
    if not amenity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated amenity not found.")

    # 4. Check for active closures
    closure = db.query(AmenityClosure).filter(
        AmenityClosure.amenity_id == slot.amenity_id,
        AmenityClosure.start_date <= slot.slot_date,
        AmenityClosure.end_date >= slot.slot_date,
    ).first()
    if closure:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot book slot: Amenity is closed from {closure.start_date} to {closure.end_date} ({closure.reason})."
        )

    # 5. Check booking rules (advance window and daily limit)
    rule = db.query(AmenityRule).filter(AmenityRule.amenity_id == slot.amenity_id).first()
    today = get_effective_now().date()
    if rule:
        max_advance = today + timedelta(days=rule.booking_window_days)
        if slot.slot_date < today or slot.slot_date > max_advance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bookings are restricted to within {rule.booking_window_days} days in advance."
            )

        # Check flat daily booking limit
        flat_bookings_count = db.query(AmenityBooking).join(AmenitySlot).filter(
            AmenityBooking.flat_id == payload.flat_id,
            AmenityBooking.status == "CONFIRMED",
            AmenitySlot.amenity_id == slot.amenity_id,
            AmenitySlot.slot_date == slot.slot_date,
        ).count()
        if flat_bookings_count >= rule.max_daily_slots_per_flat:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Flat limit reached: Maximum {rule.max_daily_slots_per_flat} slot(s) allowed per flat per day."
            )

    # 6. Enforce strict capacity limit
    if slot.booked_count >= slot.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot is fully booked. No remaining capacity available."
        )

    # 7. Increment booked count and create booking record
    slot.booked_count += 1
    slot.version += 1

    booking = AmenityBooking(
        flat_id=payload.flat_id,
        slot_id=payload.slot_id,
        user_id=user_id,
        status="CONFIRMED",
        fee=amenity.hourly_fee,
        fee_status="PAID_TEST",
        idempotency_key=payload.idempotency_key,
        version=1,
    )
    db.add(booking)
    db.flush()

    # 8. Append-only AuditEvent
    audit = AuditEvent(
        entity_type="AMENITY_BOOKING",
        entity_id=booking.id,
        action="BOOK_AMENITY_SLOT",
        actor_user_id=user_id,
        actor_role="RESIDENT",
        new_state={"status": "CONFIRMED", "slot_id": slot.id, "flat_id": payload.flat_id},
        reason=f"Booked {amenity.name} for flat {payload.flat_id} on {slot.slot_date} at {slot.start_time}.",
    )
    db.add(audit)
    db.flush()
    return booking


def cancel_amenity_booking(
    db: Session,
    booking_id: str,
    user_id: str,
    user_roles: List[str]
) -> AmenityBooking:
    booking = db.query(AmenityBooking).filter(AmenityBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    is_staff = "ADMIN" in user_roles or "HELPDESK" in user_roles or "HELP_DESK" in user_roles
    if not is_staff and booking.user_id != user_id:
        # Check flat membership
        membership = db.query(FlatMembership).filter(
            FlatMembership.flat_id == booking.flat_id,
            FlatMembership.user_id == user_id,
        ).first()
        if not membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot cancel another flat's booking.")

    if booking.status == "CANCELLED":
        return booking

    slot = get_slot_with_lock(db, booking.slot_id)
    if slot:
        # Check cancellation policy if resident
        if not is_staff:
            rule = db.query(AmenityRule).filter(AmenityRule.amenity_id == slot.amenity_id).first()
            if rule:
                slot_datetime = datetime.combine(slot.slot_date, slot.start_time, tzinfo=timezone.utc)
                now_utc = get_effective_now()
                cutoff_time = slot_datetime - timedelta(hours=rule.cancellation_cutoff_hours)
                if now_utc > cutoff_time:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cancellation window closed. Must cancel at least {rule.cancellation_cutoff_hours} hours prior to slot start."
                    )

        if slot.booked_count > 0:
            slot.booked_count -= 1
            slot.version += 1

    booking.status = "CANCELLED"
    booking.fee_status = "CANCELLED"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.version += 1

    audit = AuditEvent(
        entity_type="AMENITY_BOOKING",
        entity_id=booking.id,
        action="CANCEL_AMENITY_BOOKING",
        actor_user_id=user_id,
        actor_role="STAFF" if is_staff else "RESIDENT",
        new_state={"status": "CANCELLED"},
        reason=f"Cancelled booking {booking.id} for slot {booking.slot_id}.",
    )
    db.add(audit)
    db.flush()
    return booking


def create_amenity_closure(
    db: Session,
    payload: AmenityClosureCreate,
    staff_user_id: str
) -> AmenityClosure:
    amenity = db.query(Amenity).filter(Amenity.id == payload.amenity_id).first()
    if not amenity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Amenity not found.")

    closure = AmenityClosure(
        amenity_id=payload.amenity_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        created_by_user_id=staff_user_id,
    )
    db.add(closure)
    db.flush()

    # Cancel conflicting bookings during closure window per policy
    affected_bookings = db.query(AmenityBooking).join(AmenitySlot).filter(
        AmenitySlot.amenity_id == payload.amenity_id,
        AmenitySlot.slot_date >= payload.start_date,
        AmenitySlot.slot_date <= payload.end_date,
        AmenityBooking.status == "CONFIRMED",
    ).all()

    for b in affected_bookings:
        b.status = "CANCELLED"
        b.fee_status = "CANCELLED"
        b.cancelled_at = datetime.now(timezone.utc)
        if b.slot and b.slot.booked_count > 0:
            b.slot.booked_count -= 1

    audit = AuditEvent(
        entity_type="AMENITY_CLOSURE",
        entity_id=closure.id,
        action="CREATE_AMENITY_CLOSURE",
        actor_user_id=staff_user_id,
        actor_role="STAFF",
        reason=f"Closure added for {amenity.name} from {payload.start_date} to {payload.end_date}. Cancelled {len(affected_bookings)} conflicting bookings.",
    )
    db.add(audit)
    db.flush()
    return closure
