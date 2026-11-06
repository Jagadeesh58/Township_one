from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class BillLineResponse(BaseModel):
    id: str
    line_type: str
    description: str
    amount: float


class BillResponse(BaseModel):
    id: str
    flat_id: str
    period_month: int
    period_year: int
    issue_date: datetime
    due_date: datetime
    area_sqft: float
    rate_per_sqft: float
    principal_amount: float
    late_fee_amount: float
    total_amount: float
    paid_amount: float
    balance_amount: float
    status: str
    lines: List[BillLineResponse] = []


class LedgerEntryResponse(BaseModel):
    id: str
    flat_id: str
    entry_type: str
    amount: float
    balance_after: float
    description: str
    reference_id: Optional[str] = None
    created_at: datetime


class FlatBillingSummaryResponse(BaseModel):
    flat_id: str
    flat_number: str
    area_sqft: float
    current_due: float
    overdue_days: int
    estimated_late_fee: float
    late_fee_notice: str
    latest_bill: Optional[BillResponse] = None
    recent_ledger: List[LedgerEntryResponse] = []


class GenerateBillRequest(BaseModel):
    flat_id: str
    period_month: int
    period_year: int
