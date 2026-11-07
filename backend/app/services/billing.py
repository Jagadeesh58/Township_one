"""
Day 1 · D1-S4 — Maintenance billing and ledger
Service functions for:
- Deterministic 2-decimal currency rounding using Decimal (half up)
- Flat maintenance calculation (area_sqft * rate_per_sqft)
- Grace period boundaries (due on 15th, 5-day grace until 20th, interest starts 21st)
- Illustrative demo late fee calculation (18% p.a. simple interest pending federation approval)
- Bill generation, line items, and dual-entry ledger bookkeeping (DEBIT on bill issue)
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.entities import (
    Flat, Bill, BillLine, FlatLedgerEntry, BillingRule
)


def round_currency(val: Decimal) -> Decimal:
    """Enforces exact 2-decimal currency rounding (half up). Never uses binary float."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_effective_date() -> datetime:
    """Returns the snapshot reference date for date consistency across UI, API, seed, and tests."""
    try:
        dt = datetime.fromisoformat(settings.DEMO_AS_OF_DATE.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


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
    if days_overdue <= 0 or principal <= Decimal("0.00"):
        return Decimal("0.00")
    
    daily_rate = (annual_rate_pct / Decimal("100")) / Decimal("365")
    interest = principal * daily_rate * Decimal(days_overdue)
    return round_currency(interest)


def evaluate_bill_overdue_and_interest(
    bill: Bill,
    rule: Optional[BillingRule] = None,
    as_of: Optional[datetime] = None
) -> Tuple[int, Decimal]:
    """
    Calculates overdue days and applicable late fee with strict grace period adherence:
    - If as_of <= due_date + grace_period_days: grace period active -> 0 overdue days, 0 late fee.
    - If as_of > due_date + grace_period_days: grace period expired -> interest accrued from due date.
    """
    if bill.balance_amount <= Decimal("0.00"):
        return 0, Decimal("0.00")

    if not as_of:
        as_of = get_effective_date()

    bill_due = bill.due_date
    if bill_due.tzinfo is None:
        bill_due = bill_due.replace(tzinfo=timezone.utc)

    grace_days = rule.grace_period_days if rule else settings.DEFAULT_GRACE_PERIOD_DAYS
    rate_pa = rule.late_fee_percentage_pa if rule else Decimal(str(settings.DEMO_LATE_FEE_PERCENTAGE_PA))

    grace_cutoff = bill_due + timedelta(days=grace_days)

    if as_of <= grace_cutoff:
        # Grace period active
        return 0, Decimal("0.00")

    # Past grace period: interest calculated from original due date
    overdue_days = (as_of - bill_due).days
    late_fee = calculate_demo_late_fee(bill.balance_amount, overdue_days, rate_pa)
    return overdue_days, late_fee


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
    rule_version = rule.version if rule else "v1.0-demo"

    principal = calculate_principal(flat.area_sqft, rate)

    now = get_effective_date()
    if not issue_date:
        issue_date = now
    if not due_date:
        due_day = rule.due_day_of_month if rule else 15
        # Compute due date based on rule
        try:
            due_date = datetime(period_year, period_month, due_day, 0, 0, tzinfo=timezone.utc)
        except ValueError:
            due_date = issue_date + timedelta(days=15)

    bill = Bill(
        flat_id=flat.id,
        billing_rule_id=rule.id if rule else None,
        billing_rule_version=rule_version,
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
    last_ledger = db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat.id
    ).order_by(FlatLedgerEntry.created_at.desc()).first()
    prev_balance = last_ledger.balance_after if last_ledger else Decimal("0.00")
    new_balance = round_currency(prev_balance + principal)

    ledger_entry = FlatLedgerEntry(
        flat_id=flat.id,
        entry_type="DEBIT",
        amount=principal,
        balance_after=new_balance,
        description=f"Maintenance Bill - {period_month:02d}/{period_year}",
        reference_id=bill.id,
        created_at=issue_date
    )
    db.add(ledger_entry)
    db.commit()
    db.refresh(bill)
    return bill


def get_flat_ledger(db: Session, flat_id: str) -> List[FlatLedgerEntry]:
    return db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat_id
    ).order_by(FlatLedgerEntry.created_at.asc()).all()
