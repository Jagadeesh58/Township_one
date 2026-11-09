from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class AmenityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    hourly_fee: Decimal
    capacity: int
    rules: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AmenitySlotResponse(BaseModel):
    id: str
    amenity_id: str
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    booked_count: int
    available_spots: int
    is_closed: bool = False
    closure_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AmenityRuleResponse(BaseModel):
    id: str
    amenity_id: str
    booking_window_days: int
    max_daily_slots_per_flat: int
    cancellation_cutoff_hours: int

    model_config = ConfigDict(from_attributes=True)


class AmenityClosureCreate(BaseModel):
    amenity_id: str
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=3, max_length=500)


class AmenityClosureResponse(BaseModel):
    id: str
    amenity_id: str
    start_date: date
    end_date: date
    reason: str
    created_by_user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AmenityBookingCreate(BaseModel):
    flat_id: str
    slot_id: str
    idempotency_key: str = Field(..., min_length=8, max_length=64)


class AmenityBookingResponse(BaseModel):
    id: str
    flat_id: str
    slot_id: str
    user_id: str
    amenity_name: Optional[str] = None
    slot_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: str
    fee: Decimal
    fee_status: str
    idempotency_key: str
    version: int
    created_at: datetime
    cancelled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
