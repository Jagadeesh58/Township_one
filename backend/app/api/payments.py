"""
Township One - Test payments and receipts endpoints.
API endpoints for:
- Simulated checkout with strict outcome verification (rejecting invalid outcome values)
- Safe idempotent payment execution
- Resident payment status and receipt retrieval with strict cross-resident IDOR protections
"""

from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, verify_flat_access
from backend.app.models.entities import Payment, Receipt, User
from backend.app.services.payments import initiate_simulated_payment
from backend.app.schemas.payments import (
    PaymentInitiateRequest, PaymentResponse, ReceiptResponse
)

router = APIRouter(prefix="/payments", tags=["Payments"])


def to_receipt_response(r: Receipt) -> ReceiptResponse:
    amt_dec = Decimal(str(r.amount))
    return ReceiptResponse(
        id=r.id,
        receipt_number=r.receipt_number,
        flat_number=r.flat_number,
        resident_name=r.resident_name,
        amount=amt_dec,
        amount_inr=f"{amt_dec:.2f}",
        payment_mode=r.payment_mode,
        transaction_reference=r.transaction_reference,
        issued_at=r.issued_at
    )


def to_payment_response(p: Payment, r: Optional[Receipt] = None) -> PaymentResponse:
    amt_dec = Decimal(str(p.amount))
    return PaymentResponse(
        id=p.id,
        flat_id=p.flat_id,
        bill_id=p.bill_id,
        amount=amt_dec,
        amount_inr=f"{amt_dec:.2f}",
        currency=getattr(p, "currency", "INR"),
        status=p.status,
        payment_method=p.payment_method,
        transaction_reference=p.transaction_reference,
        paid_at=p.paid_at,
        receipt_number=p.receipt_number,
        receipt=to_receipt_response(r) if r else (to_receipt_response(p.receipt) if p.receipt else None)
    )


@router.post("/checkout", response_model=PaymentResponse)
def checkout(
    payload: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Server-side authorization: user must have active membership with 'pay' permission for this flat
    verify_flat_access(current_user, payload.flat_id, action="pay")

    payment, receipt = initiate_simulated_payment(
        db=db,
        user=current_user,
        flat_id=payload.flat_id,
        bill_id=payload.bill_id,
        amount=Decimal(str(payload.amount)),
        currency=payload.currency,
        payment_method=payload.payment_method,
        test_outcome=payload.test_outcome,
        idempotency_key=payload.idempotency_key
    )
    return to_payment_response(payment, receipt)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
    verify_flat_access(current_user, payment.flat_id, action="read")
    return to_payment_response(payment)


@router.get("/receipts/{receipt_number}", response_model=ReceiptResponse)
def get_receipt(
    receipt_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(Receipt.receipt_number == receipt_number).first()
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found.")
    payment = receipt.payment
    if payment:
        verify_flat_access(current_user, payment.flat_id, action="read")
    else:
        from backend.app.models.entities import Flat
        flat = db.query(Flat).filter(Flat.flat_number == receipt.flat_number).first()
        if flat:
            verify_flat_access(current_user, flat.id, action="read")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to receipt.")
    return to_receipt_response(receipt)
