"""
Township One - Test payments and receipts service.
Service implementation for:
- Simulated checkout with strict outcome validation (SUCCESS, PENDING, FAILED, EXPIRED only)
- Cryptographic request fingerprinting & idempotency locking (per principal, flat, bill, amount, currency, method, outcome)
- Cross-flat replay protection & information leakage prevention (generic 409 without leaking metadata)
- Dialect-aware concurrency row-locking
- Dual-entry atomic ledger posting (CREDIT on payment SUCCESS) and receipt generation
"""

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.entities import (
    Flat, Bill, Payment, PaymentIdempotencyRecord, FlatLedgerEntry, Receipt, User
)
from backend.app.schemas.payments import PaymentOutcomeEnum
from backend.app.services.billing import round_currency


def initiate_simulated_payment(
    db: Session,
    user: User,
    flat_id: str,
    bill_id: str,
    amount: Decimal,
    currency: str = "INR",
    payment_method: str = "TEST_UPI",
    test_outcome: PaymentOutcomeEnum = PaymentOutcomeEnum.SUCCESS,
    idempotency_key: str = ""
) -> Tuple[Payment, Optional[Receipt]]:
    """
    Simulated test payment processor with robust cryptographic idempotency,
    cross-flat boundary protection, and strict outcome validation:
    - Dedicated PaymentIdempotencyRecord tracking with request fingerprinting.
    - Replaying identical payload returns original payment and receipt.
    - Replaying same key with different payload returns 409 Conflict.
    - Replaying another resident's key returns generic 409 without data leakage.
    - Strict outcome validation: ONLY SUCCESS, PENDING, FAILED, EXPIRED permitted.
    - Atomicity: on SUCCESS, updates Bill balance, adds FlatLedgerEntry credit, generates Receipt.
    """
    # 0. Production guard: Simulated payments are blocked in production
    if getattr(settings, "APP_ENV", "development") == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulated test payment processor is disabled in production."
        )

    # 1. Mandatory Idempotency Key Validation
    if not idempotency_key or len(idempotency_key.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency key is required and must be at least 8 characters long."
        )
    idempotency_key = idempotency_key.strip()

    # 2. Strict Outcome Validation (Security Fix B)
    valid_outcomes = {o.value for o in PaymentOutcomeEnum}
    outcome_str = test_outcome.value if isinstance(test_outcome, PaymentOutcomeEnum) else str(test_outcome)
    if outcome_str not in valid_outcomes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payment outcome '{outcome_str}'. Allowed values: {sorted(list(valid_outcomes))}"
        )

    amount = round_currency(amount)
    if amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero."
        )

    # 3. Cryptographic Request Fingerprint for Idempotency Binding (Security Fix A)
    # Bind authenticated principal (user_id), flat, bill, amount, currency, payment_method, and outcome
    fingerprint_raw = f"{user.id}:{flat_id}:{bill_id}:{amount:.2f}:{currency}:{payment_method}:{outcome_str}"
    request_hash = hashlib.sha256(fingerprint_raw.encode("utf-8")).hexdigest()

    idempotency_record: Optional[PaymentIdempotencyRecord] = None

    # Query for existing idempotency record
    existing_rec = db.query(PaymentIdempotencyRecord).filter(
        PaymentIdempotencyRecord.idempotency_key == idempotency_key
    ).first()

    if existing_rec:
        # Check 1: User ownership - Cross-flat replay prevention without information disclosure!
        if existing_rec.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key conflict or invalid request."
            )

        # Check 2: Payload mismatch - Reused key with different bill, flat, amount, or outcome
        if existing_rec.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key has already been used with different request parameters."
            )

        # Check 3: Already completed payment
        if existing_rec.status == "COMPLETED" and existing_rec.payment_id:
            existing_payment = db.query(Payment).filter(
                Payment.id == existing_rec.payment_id
            ).first()
            if existing_payment:
                receipt = db.query(Receipt).filter(
                    Receipt.payment_id == existing_payment.id
                ).first()
                return existing_payment, receipt

        if existing_rec.status == "IN_PROGRESS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A transaction with this idempotency key is currently being processed. Please retry."
            )

    # 4. Acquire row-level lock on Bill BEFORE inserting child records (prevents PostgreSQL FK KeyShare lock inversion & deadlocks)
    bill_query = db.query(Bill).filter(Bill.id == bill_id, Bill.flat_id == flat_id)
    if db.bind and db.bind.dialect.name != "sqlite":
        bill_query = bill_query.with_for_update()
    bill = bill_query.first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found for this flat.")

    if bill.balance_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bill {bill.id} is already fully paid. Duplicate payment is not permitted."
        )

    if amount > bill.balance_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount (₹{amount}) cannot exceed current outstanding balance (₹{bill.balance_amount})."
        )

    if not existing_rec:
        # Create in-progress record to secure lock
        try:
            idempotency_record = PaymentIdempotencyRecord(
                idempotency_key=idempotency_key,
                user_id=user.id,
                flat_id=flat_id,
                bill_id=bill_id,
                amount=amount,
                currency=currency,
                request_hash=request_hash,
                status="IN_PROGRESS"
            )
            db.add(idempotency_record)
            db.flush()
        except IntegrityError:
            db.rollback()
            # Concurrent race condition: another thread inserted the same key
            conflict_rec = db.query(PaymentIdempotencyRecord).filter(
                PaymentIdempotencyRecord.idempotency_key == idempotency_key
            ).first()
            if conflict_rec and conflict_rec.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key conflict or invalid request."
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent request detected for this idempotency key. Please retry."
            )

    # 4. Generate unique payment transaction reference (distinct from idempotency key!)
    now_dt = datetime.now(timezone.utc)
    txn_ref = f"TXN-SIM-{now_dt.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # 5. Non-SUCCESS outcomes (PENDING, FAILED, EXPIRED)
    if outcome_str != "SUCCESS":
        payment = Payment(
            flat_id=flat_id,
            bill_id=bill_id,
            amount=amount,
            currency=currency,
            status=outcome_str,
            payment_method=payment_method,
            transaction_reference=txn_ref,
            idempotency_key=idempotency_key,
            paid_at=now_dt,
            payer_user_id=user.id
        )
        db.add(payment)
        db.flush()

        if idempotency_record:
            idempotency_record.payment_id = payment.id
            idempotency_record.status = "COMPLETED"

        db.commit()
        db.refresh(payment)
        return payment, None

    # 6. SUCCESS outcome: Atomic posting & Ledger credit
    receipt_no = f"REC-{now_dt.strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}"

    payment = Payment(
        flat_id=flat_id,
        bill_id=bill_id,
        amount=amount,
        currency=currency,
        status="SUCCESS",
        payment_method=payment_method,
        transaction_reference=txn_ref,
        idempotency_key=idempotency_key,
        paid_at=now_dt,
        receipt_number=receipt_no,
        payer_user_id=user.id
    )
    db.add(payment)
    db.flush()

    # Update Bill
    bill.paid_amount = round_currency(bill.paid_amount + amount)
    bill.balance_amount = round_currency(bill.total_amount - bill.paid_amount)
    if bill.balance_amount == Decimal("0.00"):
        bill.status = "PAID"
    else:
        bill.status = "PARTIALLY_PAID"

    # Update Flat Ledger (Debit was posted when bill was created; now post Credit)
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

    if idempotency_record:
        idempotency_record.payment_id = payment.id
        idempotency_record.status = "COMPLETED"

    db.commit()
    db.refresh(payment)
    db.refresh(receipt)
    return payment, receipt
