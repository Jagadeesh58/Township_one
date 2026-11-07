from typing import Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PaymentOutcomeEnum(str, Enum):
    SUCCESS = "SUCCESS"
    PENDING = "PENDING"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PaymentInitiateRequest(BaseModel):
    flat_id: str
    bill_id: str
    amount: Decimal = Field(..., gt=0, description="Payment amount must be greater than zero")
    currency: str = Field("INR", max_length=10)
    payment_method: str = "TEST_UPI"
    test_outcome: PaymentOutcomeEnum = Field(
        PaymentOutcomeEnum.SUCCESS,
        description="Explicit test outcome: SUCCESS, PENDING, FAILED, EXPIRED. Invalid values rejected."
    )
    idempotency_key: Optional[str] = Field(None, max_length=100)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 8:
                raise ValueError("Idempotency key must be at least 8 characters long.")
        return v


class ReceiptResponse(BaseModel):
    id: str
    receipt_number: str
    flat_number: str
    resident_name: str
    amount: float
    amount_inr: str
    payment_mode: str
    transaction_reference: str
    issued_at: datetime


class PaymentResponse(BaseModel):
    id: str
    flat_id: str
    bill_id: str
    amount: float
    amount_inr: str
    currency: str = "INR"
    status: str
    payment_method: str
    transaction_reference: str
    paid_at: datetime
    receipt_number: Optional[str] = None
    receipt: Optional[ReceiptResponse] = None
