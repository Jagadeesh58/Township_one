from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class BankMatchReason(str, Enum):
    REGISTERED_UPI_AND_FLAT_REFERENCE = "REGISTERED_UPI_AND_FLAT_REFERENCE"
    EXACT_INTENT_REFERENCE = "EXACT_INTENT_REFERENCE"
    UPI_ONLY_REVIEW = "UPI_ONLY_REVIEW"
    FLAT_REF_ONLY_REVIEW = "FLAT_REF_ONLY_REVIEW"
    AMOUNT_ONLY_REVIEW = "AMOUNT_ONLY_REVIEW"
    CHEQUE_CLEARANCE_PENDING = "CHEQUE_CLEARANCE_PENDING"
    REVERSAL_BOUNCE_REVIEW = "REVERSAL_BOUNCE_REVIEW"
    DEBIT_ROW_REQUIRES_MANUAL_REVIEW = "DEBIT_ROW_REQUIRES_MANUAL_REVIEW"
    MISSING_UTR = "MISSING_UTR"
    DUPLICATE_UTR_IDENTICAL_EVIDENCE = "DUPLICATE_UTR_IDENTICAL_EVIDENCE"
    UTR_CONFLICT_DIFFERENT_EVIDENCE = "UTR_CONFLICT_DIFFERENT_EVIDENCE"
    FLAT_REF_NOT_FOUND = "FLAT_REF_NOT_FOUND"
    UNKNOWN_PAYER_UPI = "UNKNOWN_PAYER_UPI"
    UPI_REUSED_ACROSS_FLATS_AMBIGUOUS = "UPI_REUSED_ACROSS_FLATS_AMBIGUOUS"
    CONFLICTING_UPI_AND_FLAT_REF = "CONFLICTING_UPI_AND_FLAT_REF"
    OVERPAYMENT_ALL_BILLS_PAID = "OVERPAYMENT_ALL_BILLS_PAID"
    AMBIGUOUS_MULTI_BILL_MATCH = "AMBIGUOUS_MULTI_BILL_MATCH"
    PARTIAL_PAYMENT_REQUIRES_REVIEW = "PARTIAL_PAYMENT_REQUIRES_REVIEW"
    OVERPAYMENT_EXCEEDS_BALANCE = "OVERPAYMENT_EXCEEDS_BALANCE"
    UNRECOGNIZED_BANK_ACCOUNT = "UNRECOGNIZED_BANK_ACCOUNT"
    # Defensive operational reasons
    NO_REFERENCE_FOUND = "NO_REFERENCE_FOUND"
    WRONG_BANK_ACCOUNT = "WRONG_BANK_ACCOUNT"
    BILL_BALANCE_SHIFTED_DURING_COMMIT = "BILL_BALANCE_SHIFTED_DURING_COMMIT"


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
