"""
Day 1 · D1-S4 — Maintenance billing and ledger
Endpoints for:
- Flat billing summaries with multi-bill unpaid aggregation (total_outstanding_due, unpaid_bills)
- Strict server-side RBAC denying Committee and Security Guard access to individual flat records
- Committee aggregate reports (total billed, collected, outstanding across township)
- Bill retrieval, bill details, and flat ledger entries
"""

from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, verify_flat_access, require_role
from backend.app.models.entities import Flat, Bill, FlatLedgerEntry, BillingRule, User
from backend.app.services.billing import (
    evaluate_bill_overdue_and_interest, generate_flat_bill, get_flat_ledger, get_effective_date, round_currency
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
            "amount": float(line.amount),
            "amount_inr": f"{Decimal(str(line.amount)):.2f}"
        }
        for line in bill.lines
    ]
    p_dec = Decimal(str(bill.principal_amount))
    t_dec = Decimal(str(bill.total_amount))
    pd_dec = Decimal(str(bill.paid_amount))
    b_dec = Decimal(str(bill.balance_amount))
    lf_dec = Decimal(str(bill.late_fee_amount))

    return BillResponse(
        id=bill.id,
        flat_id=bill.flat_id,
        period_month=bill.period_month,
        period_year=bill.period_year,
        billing_rule_version=getattr(bill, "billing_rule_version", "v1.0-demo"),
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        area_sqft=float(bill.area_sqft),
        rate_per_sqft=float(bill.rate_per_sqft),
        principal_amount=float(p_dec),
        principal_amount_inr=f"{p_dec:.2f}",
        late_fee_amount=float(lf_dec),
        total_amount=float(t_dec),
        total_amount_inr=f"{t_dec:.2f}",
        paid_amount=float(pd_dec),
        paid_amount_inr=f"{pd_dec:.2f}",
        balance_amount=float(b_dec),
        balance_amount_inr=f"{b_dec:.2f}",
        status=bill.status,
        lines=lines
    )


def to_ledger_response(entry: FlatLedgerEntry) -> LedgerEntryResponse:
    amt_dec = Decimal(str(entry.amount))
    bal_dec = Decimal(str(entry.balance_after))
    return LedgerEntryResponse(
        id=entry.id,
        flat_id=entry.flat_id,
        entry_type=entry.entry_type,
        amount=float(amt_dec),
        amount_inr=f"{amt_dec:.2f}",
        balance_after=float(bal_dec),
        balance_after_inr=f"{bal_dec:.2f}",
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
    # Strict server-side authorization: Blocks Committee, Guard, and unauthorized residents
    verify_flat_access(current_user, flat_id, action="read")

    flat = db.query(Flat).filter(Flat.id == flat_id).first()
    if not flat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flat not found.")

    rule = db.query(BillingRule).filter(BillingRule.is_active == True).first()
    effective_now = get_effective_date()

    # Aggregate ALL bills for this flat
    all_bills = db.query(Bill).filter(
        Bill.flat_id == flat_id
    ).order_by(Bill.period_year.desc(), Bill.period_month.desc()).all()

    latest_bill = all_bills[0] if all_bills else None

    # Aggregate all eligible unpaid bills (balance > 0)
    unpaid_bills = [b for b in all_bills if Decimal(str(b.balance_amount)) > Decimal("0.00")]

    total_outstanding = Decimal("0.00")
    total_estimated_late_fee = Decimal("0.00")
    max_overdue_days = 0

    for b in unpaid_bills:
        b_bal = Decimal(str(b.balance_amount))
        total_outstanding += b_bal
        days_ovd, l_fee = evaluate_bill_overdue_and_interest(b, rule, as_of=effective_now)
        total_estimated_late_fee += l_fee
        if days_ovd > max_overdue_days:
            max_overdue_days = days_ovd

    total_outstanding = round_currency(total_outstanding)
    total_estimated_late_fee = round_currency(total_estimated_late_fee)

    ledger_entries = db.query(FlatLedgerEntry).filter(
        FlatLedgerEntry.flat_id == flat_id
    ).order_by(FlatLedgerEntry.created_at.desc()).limit(15).all()

    return FlatBillingSummaryResponse(
        flat_id=flat.id,
        flat_number=flat.flat_number,
        area_sqft=float(flat.area_sqft),
        current_due=float(total_outstanding),
        current_due_inr=f"{total_outstanding:.2f}",
        total_outstanding_due=float(total_outstanding),
        total_outstanding_due_inr=f"{total_outstanding:.2f}",
        overdue_days=max_overdue_days,
        estimated_late_fee=float(total_estimated_late_fee),
        estimated_late_fee_inr=f"{total_estimated_late_fee:.2f}",
        late_fee_notice="Demo Rule (18% p.a. simple interest after 5-day grace period) - pending society federation approval",
        unpaid_bills=[to_bill_response(b) for b in unpaid_bills],
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


# Authorized Committee Aggregate Endpoint (Security Fix C)
@router.get("/committee/aggregate")
def get_committee_aggregate(
    current_user: User = Depends(require_role(["COMMITTEE", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Aggregate financial overview authorized for Committee members (zero individual flat PII)."""
    total_billed = db.query(func.coalesce(func.sum(Bill.total_amount), 0)).scalar()
    total_collected = db.query(func.coalesce(func.sum(Bill.paid_amount), 0)).scalar()
    total_outstanding = db.query(func.coalesce(func.sum(Bill.balance_amount), 0)).scalar()
    total_flats = db.query(Flat).count()

    dec_billed = Decimal(str(total_billed))
    dec_collected = Decimal(str(total_collected))
    eff_pct = round(float(dec_collected / dec_billed * 100), 2) if dec_billed > 0 else 0.0

    return {
        "status": "authorized",
        "scope": "TOWNSHIP_AGGREGATE",
        "total_flats": total_flats,
        "total_billed_inr": f"{dec_billed:.2f}",
        "total_collected_inr": f"{dec_collected:.2f}",
        "total_outstanding_inr": f"{Decimal(str(total_outstanding)):.2f}",
        "collection_efficiency_pct": eff_pct,
        "as_of_date": get_effective_date().isoformat()
    }
