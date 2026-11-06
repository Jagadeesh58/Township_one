from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, verify_flat_access, require_role
from backend.app.models.entities import Flat, Bill, FlatLedgerEntry, User
from backend.app.services.billing import (
    calculate_demo_late_fee, generate_flat_bill, get_flat_ledger
)
from backend.app.schemas.billing import (
    BillResponse, FlatBillingSummaryResponse, LedgerEntryResponse,
    GenerateBillRequest
)

router = APIRouter(prefix="/billing", tags=["Billing & Maintenance"])


def to_bill_response(bill: Bill) -> BillResponse:
    lines = [
        {
            "id": line.id,
            "line_type": line.line_type,
            "description": line.description,
            "amount": float(line.amount)
        }
        for line in bill.lines
    ]
    return BillResponse(
        id=bill.id,
        flat_id=bill.flat_id,
        period_month=bill.period_month,
        period_year=bill.period_year,
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        area_sqft=float(bill.area_sqft),
        rate_per_sqft=float(bill.rate_per_sqft),
        principal_amount=float(bill.principal_amount),
        late_fee_amount=float(bill.late_fee_amount),
        total_amount=float(bill.total_amount),
        paid_amount=float(bill.paid_amount),
        balance_amount=float(bill.balance_amount),
        status=bill.status,
        lines=lines
    )


def to_ledger_response(entry: FlatLedgerEntry) -> LedgerEntryResponse:
    return LedgerEntryResponse(
        id=entry.id,
        flat_id=entry.flat_id,
        entry_type=entry.entry_type,
        amount=float(entry.amount),
        balance_after=float(entry.balance_after),
        description=entry.description,
        reference_id=entry.reference_id,
        created_at=entry.created_at
    )


@router.get("/flats/{flat_id}/summary", response_model=FlatBillingSummaryResponse)
def get_flat_billing_summary(
    flat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Server-side authorization
    verify_flat_access(current_user, flat_id, action="read")

    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flat not found.")

    latest_bill = db.query(Bill).filter(
        Bill.flat_id == flat_id
    ).order_by(Bill.period_year.desc(), Bill.period_month.desc()).first()

    now = datetime.now(timezone.utc)
    overdue_days = 0
    estimated_late_fee = Decimal("0.00")
    current_due = Decimal("0.00")

    if latest_bill:
        current_due = latest_bill.balance_amount
        # Make latest_bill.due_date timezone aware if naive
        bill_due = latest_bill.due_date
        if bill_due.tzinfo is None:
            bill_due = bill_due.replace(tzinfo=timezone.utc)
        
        if current_due > Decimal("0.00") and now > bill_due:
            overdue_days = (now - bill_due).days
            estimated_late_fee = calculate_demo_late_fee(current_due, overdue_days)

    ledger_entries = db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat_id
    ).order_by(FlatLedgerEntry.created_at.desc()).limit(10).all()

    return FlatBillingSummaryResponse(
        flat_id=flat.id,
        flat_number=flat.flat_number,
        area_sqft=float(flat.area_sqft),
        current_due=float(current_due),
        overdue_days=overdue_days,
        estimated_late_fee=float(estimated_late_fee),
        late_fee_notice="Demo Rule (18% p.a. simple interest after due date) - pending society federation approval",
        latest_bill=to_bill_response(latest_bill) if latest_bill else None,
        recent_ledger=[to_ledger_response(e) for e in ledger_entries]
    )


@router.get("/flats/{flat_id}/bills", response_model=List[BillResponse])
def get_bills_for_flat(
    flat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_flat_access(current_user, flat_id, action="read")
    bills = db.query(Bill).filter(Bill.flat_id == flat_id).order_by(Bill.issue_date.desc()).all()
    return [to_bill_response(b) for b in bills]


@router.get("/bills/{bill_id}", response_model=BillResponse)
def get_bill_detail(
    bill_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found.")
    verify_flat_access(current_user, bill.flat_id, action="read")
    return to_bill_response(bill)


@router.get("/flats/{flat_id}/ledger", response_model=List[LedgerEntryResponse])
def get_ledger_for_flat(
    flat_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_flat_access(current_user, flat_id, action="read")
    entries = get_flat_ledger(db, flat_id)
    return [to_ledger_response(e) for e in entries]


@router.post("/generate", response_model=BillResponse)
def generate_bill(
    payload: GenerateBillRequest,
    current_user: User = Depends(require_role(["ACCOUNTS", "ADMIN"])),
    db: Session = Depends(get_db)
):
    bill = generate_flat_bill(
        db=db,
        flat_id=payload.flat_id,
        period_month=payload.period_month,
        period_year=payload.period_year
    )
    return to_bill_response(bill)
