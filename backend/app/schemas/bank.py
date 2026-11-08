from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class BankRowPreviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_row_number: int
    txn_date: Optional[str] = None
    value_date: Optional[str] = None
    narration: Optional[str] = None
    direction: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "INR"
    utr: Optional[str] = None
    payer_upi: Optional[str] = None
    flat_ref: Optional[str] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    parse_status: str = "ACCEPTED"
    parse_errors: Optional[List[str]] = None
    matched_flat_number: Optional[str] = None
    matched_bill_id: Optional[str] = None


class BankImportPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_sha256: str
    duplicate_file: bool
    total_rows: int
    accepted_rows: int
    invalid_rows: int
    total_credit_amount: Decimal
    total_debit_amount: Decimal
    auto_match_count: int
    review_count: int
    duplicate_count: int
    rows: List[BankRowPreviewItem]


class BankImportCommitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_file_id: str
    filename: str
    file_sha256: str
    total_rows: int
    accepted_rows: int
    invalid_rows: int
    auto_matched_count: int
    review_count: int
    duplicate_count: int
    is_duplicate: bool = False


class BankRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    import_file_id: str
    original_row_number: int
    txn_date: Optional[datetime] = None
    value_date: Optional[datetime] = None
    narration: Optional[str] = None
    direction: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "INR"
    utr: Optional[str] = None
    payer_upi: Optional[str] = None
    flat_ref: Optional[str] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    review_status: str
    matched_flat_id: Optional[str] = None
    matched_flat_number: Optional[str] = None
    matched_bill_id: Optional[str] = None
    matched_payment_id: Optional[str] = None
    correction_reason: Optional[str] = None
    raw_row: Optional[Dict[str, Any]] = None
    audit_trail: Optional[List[Any]] = None


class ReviewActionRequest(BaseModel):
    action: str  # APPROVE, REJECT, HOLD, CORRECT_MAPPING
    target_flat_id: Optional[str] = None
    target_bill_id: Optional[str] = None
    reason: Optional[str] = None


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_no: str
    bank_name: str
    ifsc_code: str
    is_active: bool
