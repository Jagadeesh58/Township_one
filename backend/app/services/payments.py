from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import (
    Flat, Bill, Payment, FlatLedgerEntry, Receipt, User
)
from backend.app.services.billing import round_currency


def initiate_simulated_payment(
    db: Session,
    user: User,
    flat_id: str,
    bill_id: str,
    amount: Decimal,
    payment_method: str = "TEST_UPI",
    test_outcome: str = "SUCCESS",
    idempotency_key: Optional[str] = None
) -> Tuple[Payment, Optional[Receipt]]:
    """
    Simulated test payment processor with deterministic outcomes:
    - SUCCESS: Atomically creates Payment, updates Bill balance, adds FlatLedgerEntry credit, generates Receipt.
    - PENDING / FAILED / EXPIRED: Records Payment attempt without updating Bill or Ledger or generating Receipt.
    """
    # 1. Fetch and validate bill
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.flat_id == flat_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found for this flat.")

    # 2. Check for idempotency replay first
    if idempotency_key:
        existing_payment = db.query(Payment).filter(
            Payment.transaction_reference == idempotency_key
        ).first()
        if existing_payment:
            receipt = db.query(Receipt).filter(Receipt.payment_id == existing_payment.id).first()
            return existing_payment, receipt

    # 3. Check if bill is already paid
    if bill.balance_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill {bill.id} is already fully paid. Duplicate payment is not permitted."
        )

    # 4. Validate amount
    amount = round_currency(amount)
    if amount <= Decimal("0.00"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero.")
    if amount > bill.balance_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount (₹{amount}) cannot exceed current outstanding balance (₹{bill.balance_amount})."
        )

    # Generate unique transaction reference
    txn_ref = idempotency_key if idempotency_key else f"TXN-SIM-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # Handle outcomes
    test_outcome = test_outcome.upper()
    if test_outcome not in ["SUCCESS", "PENDING", "FAILED", "EXPIRED"]:
        test_outcome = "SUCCESS"

    if test_outcome != "SUCCESS":
        # Record non-successful payment attempt
        payment = Payment(
            flat_id=flat_id,
            bill_id=bill_id,
            amount=amount,
            status=test_outcome,
            payment_method=payment_method,
            transaction_reference=txn_ref,
            paid_at=datetime.now(timezone.utc),
            payer_user_id=user.id
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment, None

    # SUCCESS: Atomic posting
    now_dt = datetime.now(timezone.utc)
    receipt_no = f"REC-{now_dt.strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"

    payment = Payment(
        flat_id=flat_id,
        bill_id=bill_id,
        amount=amount,
        status="SUCCESS",
        payment_method=payment_method,
        transaction_reference=txn_ref,
        paid_at=now_dt,
        receipt_number=receipt_no,
        payer_user_id=user.id
    )
    db.add(payment)
    db.flush()

    # Update Bill balance and status
    bill.paid_amount = round_currency(bill.paid_amount + amount)
    bill.balance_amount = round_currency(bill.total_amount - bill.paid_amount)
    if bill.balance_amount == Decimal("0.00"):
        bill.status = "PAID"
    else:
        bill.status = "PARTIALLY_PAID"

    # Update Flat Ledger
    last_ledger = db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat_id
    ).order_by(FlatLedgerEntry.created_at.desc()).first()
    prev_balance = last_ledger.balance_after if last_ledger else Decimal("0.00")
    new_balance = round_currency(prev_balance - amount)

    ledger_entry = FlatLedgerEntry(
        flat_id=flat_id,
        entry_type="CREDIT",
        amount=amount,
        balance_after=new_balance,
        description=f"Payment received via {payment_method} - {receipt_no}",
        reference_id=payment.id,
        created_at=now_dt
    )
    db.add(ledger_entry)

    # Generate Receipt
    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    receipt = Receipt(
        payment_id=payment.id,
        receipt_number=receipt_no,
        flat_number=flat.flat_number if flat else "Unknown",
        resident_name=user.name,
        amount=amount,
        payment_mode=payment_method,
        transaction_reference=txn_ref,
        issued_at=now_dt
    )
    db.add(receipt)

    db.commit()
    db.refresh(payment)
    db.refresh(receipt)
    return payment, receipt
