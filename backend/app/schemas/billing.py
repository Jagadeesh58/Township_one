from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class BillLineResponse(BaseModel):
    id: str
    line_type: str
    description: str
    amount: float
    amount_inr: str


class BillResponse(BaseModel):
    id: str
    flat_id: str
    period_month: int
    period_year: int
    billing_rule_version: str = "v1.0-demo"
    issue_date: datetime
    due_date: datetime
    area_sqft: float
    rate_per_sqft: float
    principal_amount: float
    principal_amount_inr: str
    late_fee_amount: float
    total_amount: float
    total_amount_inr: str
    paid_amount: float
    paid_amount_inr: str
    balance_amount: float
    balance_amount_inr: str
    status: str
    lines: List[BillLineResponse] = []


class LedgerEntryResponse(BaseModel):
    id: str
    flat_id: str
    entry_type: str
    amount: float
    amount_inr: str
    balance_after: float
    balance_after_inr: str
    description: str
    reference_id: Optional[str] = None
    created_at: datetime


class FlatBillingSummaryResponse(BaseModel):
    flat_id: str
    flat_number: str
    area_sqft: float
    current_due: float
    current_due_inr: str
    total_outstanding_due: float
    total_outstanding_due_inr: str
    overdue_days: int
    estimated_late_fee: float
    estimated_late_fee_inr: str
    late_fee_notice: str
    unpaid_bills: List[BillResponse] = []
    latest_bill: Optional[BillResponse] = None
    recent_ledger: List[LedgerEntryResponse] = []


class GenerateBillRequest(BaseModel):
    flat_id: str
    period_month: int
    period_year: int
