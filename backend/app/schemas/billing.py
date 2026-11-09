from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BillLineResponse(BaseModel):
    id: str
    line_type: str
    description: str
    amount: Decimal
    amount_inr: str


class BillResponse(BaseModel):
    id: str
    flat_id: str
    period_month: int
    period_year: int
    billing_rule_version: str = "v1.0-demo"
    issue_date: datetime
    due_date: datetime
    area_sqft: Decimal
    rate_per_sqft: Decimal
    principal_amount: Decimal
    principal_amount_inr: str
    late_fee_amount: Decimal
    total_amount: Decimal
    total_amount_inr: str
    paid_amount: Decimal
    paid_amount_inr: str
    balance_amount: Decimal
    balance_amount_inr: str
    status: str
    lines: list[BillLineResponse] = []


class LedgerEntryResponse(BaseModel):
    id: str
    flat_id: str
    entry_type: str
    amount: Decimal
    amount_inr: str
    balance_after: Decimal
    balance_after_inr: str
    description: str
    reference_id: str | None = None
    created_at: datetime


class FlatBillingSummaryResponse(BaseModel):
    flat_id: str
    flat_number: str
    area_sqft: Decimal
    current_due: Decimal
    current_due_inr: str
    total_outstanding_due: Decimal
    total_outstanding_due_inr: str
    overdue_days: int
    interest_eligible_days: int = 0
    estimated_late_fee: Decimal
    estimated_late_fee_inr: str
    late_fee_notice: str
    unpaid_bills: list[BillResponse] = []
    latest_bill: BillResponse | None = None
    recent_ledger: list[LedgerEntryResponse] = []


class GenerateBillRequest(BaseModel):
    flat_id: str
    period_month: int
    period_year: int
