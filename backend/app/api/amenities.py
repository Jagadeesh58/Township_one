from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import (
    User,
    Amenity,
    AmenitySlot,
    AmenityRule,
    AmenityClosure,
    AmenityBooking,
    FlatMembership,
)
from backend.app.schemas.amenities import (
    AmenityResponse,
    AmenitySlotResponse,
    AmenityRuleResponse,
    AmenityClosureCreate,
    AmenityClosureResponse,
    AmenityBookingCreate,
    AmenityBookingResponse,
)
from backend.app.services.amenity_service import (
    book_amenity_slot,
    cancel_amenity_booking,
    create_amenity_closure,
    get_effective_now,
)

router = APIRouter(prefix="/amenities", tags=["amenities"])


def get_user_roles(user: User) -> List[str]:
    return [r.role_code for r in user.role_assignments]


@router.get("", response_model=List[AmenityResponse])
def list_amenities(db: Session = Depends(get_db)):
    amenities = db.query(Amenity).all()
    return amenities


@router.get("/{amenity_id}/slots", response_model=List[AmenitySlotResponse])
def list_amenity_slots(
    amenity_id: str,
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    query_date = target_date or get_effective_now().date()
    slots = db.query(AmenitySlot).filter(
        AmenitySlot.amenity_id == amenity_id,
        AmenitySlot.slot_date == query_date,
    ).order_by(AmenitySlot.start_time.asc()).all()

    # Check for active closures
    closures = db.query(AmenityClosure).filter(
        AmenityClosure.amenity_id == amenity_id,
        AmenityClosure.start_date <= query_date,
        AmenityClosure.end_date >= query_date,
    ).all()

    result = []
    for slot in slots:
        closure = next((c for c in closures if c.start_date <= slot.slot_date <= c.end_date), None)
        is_closed = closure is not None
        closure_reason = closure.reason if closure else None
        available = max(0, slot.capacity - slot.booked_count) if not is_closed else 0

        result.append(AmenitySlotResponse(
            id=slot.id,
            amenity_id=slot.amenity_id,
            slot_date=slot.slot_date,
            start_time=slot.start_time,
            end_time=slot.end_time,
            capacity=slot.capacity,
            booked_count=slot.booked_count,
            available_spots=available,
            is_closed=is_closed,
            closure_reason=closure_reason,
        ))

    return result


@router.get("/{amenity_id}/rules", response_model=AmenityRuleResponse)
def get_amenity_rules(amenity_id: str, db: Session = Depends(get_db)):
    rule = db.query(AmenityRule).filter(AmenityRule.amenity_id == amenity_id).first()
    if not rule:
        # Default policy
        return AmenityRuleResponse(
            id="default",
            amenity_id=amenity_id,
            booking_window_days=7,
            max_daily_slots_per_flat=1,
            cancellation_cutoff_hours=2,
        )
    return rule


@router.get("/bookings", response_model=List[AmenityBookingResponse])
def list_bookings(
    flat_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    query = db.query(AmenityBooking)

    # Resident scoping
    if "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles and "COMMITTEE" not in roles:
        user_flat_ids = [m.flat_id for m in current_user.flat_memberships]
        if not user_flat_ids:
            return []
        query = query.filter(AmenityBooking.flat_id.in_(user_flat_ids))
        if flat_id and flat_id in user_flat_ids:
            query = query.filter(AmenityBooking.flat_id == flat_id)
    elif flat_id:
        query = query.filter(AmenityBooking.flat_id == flat_id)

    bookings = query.order_by(AmenityBooking.created_at.desc()).limit(100).all()

    result = []
    for b in bookings:
        slot = b.slot
        amenity = slot.amenity if slot else None
        result.append(AmenityBookingResponse(
            id=b.id,
            flat_id=b.flat_id,
            slot_id=b.slot_id,
            user_id=b.user_id,
            amenity_name=amenity.name if amenity else None,
            slot_date=slot.slot_date if slot else None,
            start_time=slot.start_time if slot else None,
            end_time=slot.end_time if slot else None,
            status=b.status,
            fee=b.fee,
            fee_status=b.fee_status,
            idempotency_key=b.idempotency_key,
            version=b.version,
            created_at=b.created_at,
            cancelled_at=b.cancelled_at,
        ))

    return result


@router.post("/bookings", response_model=AmenityBookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: AmenityBookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = book_amenity_slot(db, payload, current_user.id)
    db.commit()
    db.refresh(booking)

    slot = booking.slot
    amenity = slot.amenity if slot else None

    return AmenityBookingResponse(
        id=booking.id,
        flat_id=booking.flat_id,
        slot_id=booking.slot_id,
        user_id=booking.user_id,
        amenity_name=amenity.name if amenity else None,
        slot_date=slot.slot_date if slot else None,
        start_time=slot.start_time if slot else None,
        end_time=slot.end_time if slot else None,
        status=booking.status,
        fee=booking.fee,
        fee_status=booking.fee_status,
        idempotency_key=booking.idempotency_key,
        version=booking.version,
        created_at=booking.created_at,
        cancelled_at=booking.cancelled_at,
    )


@router.post("/bookings/{booking_id}/cancel", response_model=AmenityBookingResponse)
def cancel_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    booking = cancel_amenity_booking(db, booking_id, current_user.id, roles)
    db.commit()
    db.refresh(booking)

    slot = booking.slot
    amenity = slot.amenity if slot else None

    return AmenityBookingResponse(
        id=booking.id,
        flat_id=booking.flat_id,
        slot_id=booking.slot_id,
        user_id=booking.user_id,
        amenity_name=amenity.name if amenity else None,
        slot_date=slot.slot_date if slot else None,
        start_time=slot.start_time if slot else None,
        end_time=slot.end_time if slot else None,
        status=booking.status,
        fee=booking.fee,
        fee_status=booking.fee_status,
        idempotency_key=booking.idempotency_key,
        version=booking.version,
        created_at=booking.created_at,
        cancelled_at=booking.cancelled_at,
    )


@router.post("/closures", response_model=AmenityClosureResponse, status_code=status.HTTP_201_CREATED)
def add_closure(
    payload: AmenityClosureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = get_user_roles(current_user)
    if "ADMIN" not in roles and "HELPDESK" not in roles and "HELP_DESK" not in roles and "COMMITTEE" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only staff can create amenity closures.")

    closure = create_amenity_closure(db, payload, current_user.id)
    db.commit()
    db.refresh(closure)
    return closure
