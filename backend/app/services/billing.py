from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import (
    Flat, Bill, BillLine, FlatLedgerEntry, BillingRule
)


def round_currency(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_principal(area_sqft: Decimal, rate_per_sqft: Decimal = Decimal("6.50")) -> Decimal:
    """Calculates maintenance principal amount: area (sq ft) * rate (INR/sq ft)."""
    return round_currency(area_sqft * rate_per_sqft)


def calculate_demo_late_fee(
    principal: Decimal,
    days_overdue: int,
    annual_rate_pct: Decimal = Decimal("18.00")
) -> Decimal:
    """
    Illustrative Demo Late Fee Formula:
    Simple interest: Principal * (Rate / 100) * (Days / 365)
    Labelled as: 'Demo assumption pending society federation approval'
    """
    if days_overdue <= 0:
        return Decimal("0.00")
    
    daily_rate = (annual_rate_pct / Decimal("100")) / Decimal("365")
    interest = principal * daily_rate * Decimal(days_overdue)
    return round_currency(interest)


def generate_flat_bill(
    db: Session,
    flat_id: str,
    period_month: int,
    period_year: int,
    issue_date: Optional[datetime] = None,
    due_date: Optional[datetime] = None
) -> Bill:
    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flat not found.")

    # Check for duplicate bill in this period
    existing = db.query(Bill).filter(
        Bill.flat_id == flat_id,
        Bill.period_month == period_month,
        Bill.period_year == period_year
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bill for flat {flat.flat_number} for period {period_month}/{period_year} already exists (Bill ID: {existing.id})."
        )

    # Active billing rule
    rule = db.query(BillingRule).filter(BillingRule.is_active == True).first()
    rate = rule.rate_per_sqft if rule else Decimal("6.50")

    principal = calculate_principal(flat.area_sqft, rate)

    now = datetime.now(timezone.utc)
    if not issue_date:
        issue_date = now
    if not due_date:
        due_date = issue_date + timedelta(days=15)

    bill = Bill(
        flat_id=flat.id,
        billing_rule_id=rule.id if rule else None,
        period_month=period_month,
        period_year=period_year,
        issue_date=issue_date,
        due_date=due_date,
        area_sqft=flat.area_sqft,
        rate_per_sqft=rate,
        principal_amount=principal,
        late_fee_amount=Decimal("0.00"),
        total_amount=principal,
        paid_amount=Decimal("0.00"),
        balance_amount=principal,
        status="ISSUED"
    )
    db.add(bill)
    db.flush()

    # Add principal line item
    line = BillLine(
        bill_id=bill.id,
        line_type="PRINCIPAL",
        description=f"Monthly Maintenance ({flat.area_sqft} sq ft @ ₹{rate}/sq ft)",
        amount=principal
    )
    db.add(line)

    # Record in Flat Ledger
    # Get last balance
    last_ledger = db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat.id
    ).order_by(FlatLedgerEntry.created_at.desc()).first()
    prev_balance = last_ledger.balance_after if last_ledger else Decimal("0.00")
    new_balance = prev_balance + principal

    ledger_entry = FlatLedgerEntry(
        flat_id=flat.id,
        entry_type="DEBIT",
        amount=principal,
        balance_after=new_balance,
        description=f"Maintenance Bill - {period_month:02d}/{period_year}",
        reference_id=bill.id
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(bill)
    return bill


def get_flat_ledger(db: Session, flat_id: str) -> List[FlatLedgerEntry]:
    return db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat_id
    ).order_by(FlatLedgerEntry.created_at.asc()).all()
