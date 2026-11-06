from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PaymentInitiateRequest(BaseModel):
    flat_id: str
    bill_id: str
    amount: float = Field(..., gt=0)
    payment_method: str = "TEST_UPI"
    test_outcome: str = Field("SUCCESS", description="SUCCESS, PENDING, FAILED, EXPIRED")
    idempotency_key: Optional[str] = None


class ReceiptResponse(BaseModel):
    id: str
    receipt_number: str
    flat_number: str
    resident_name: str
    amount: float
    payment_mode: str
    transaction_reference: str
    issued_at: datetime


class PaymentResponse(BaseModel):
    id: str
    flat_id: str
    bill_id: str
    amount: float
    status: str
    payment_method: str
    transaction_reference: str
    paid_at: datetime
    receipt_number: Optional[str] = None
    receipt: Optional[ReceiptResponse] = None
