"""
Township One - Bank Statement Matching Engine.

Deterministic match engine for bank statements conforming to DEMO_BANK_CSV_V1 specification.
Provides:
- Non-mutating CSV preview with strict schema and format validation
- Idempotent commit keyed by (account_no, file_sha256)
- Deterministic auto-match rule evaluation (zero AI in financial decisions)
- Atomic payment and ledger posting with row-level locks
- Comprehensive reviewer action handlers (APPROVE, REJECT, HOLD, CORRECT_MAPPING)
"""

import csv
import io
import re
import uuid
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.entities import (
    BankAccount, BankImportFile, BankRow, Flat, Bill, Payment,
    FlatLedgerEntry, Receipt, RegisteredUPI, AuditEvent, User
)
from backend.app.services.billing import round_currency


EXPECTED_HEADERS = [
    "account_no", "txn_date", "value_date", "narration",
    "direction", "amount", "currency", "utr", "payer_upi", "flat_ref"
]

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d"
]


def parse_statement_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str or not date_str.strip():
        return None
    cleaned = date_str.strip()
    try:
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def calculate_content_sha256(content: Union[str, bytes]) -> tuple[bytes, str]:
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    return content_bytes, hashlib.sha256(content_bytes).hexdigest()


def preview_bank_statement(
    db: Session,
    content: Union[str, bytes],
    filename: str,
    bank_account_no: Optional[str] = None
) -> Dict[str, Any]:
    """
    Non-mutating preview function.
    Validates CSV headers, date, amount, direction, currency, known account, and required fields.
    Computes candidate deterministic match decisions without writing to the database.
    """
    content_bytes, file_sha256 = calculate_content_sha256(content)
    text_content = content_bytes.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise ValueError("Bank statement file is empty or missing headers.")

    cleaned_headers = [h.strip() for h in reader.fieldnames]
    missing_headers = [h for h in EXPECTED_HEADERS if h not in cleaned_headers]
    if missing_headers:
        raise ValueError(f"Missing required CSV headers: {', '.join(missing_headers)}")

    # Check for duplicate file SHA256 in DB
    existing_file = db.query(BankImportFile).filter(
        BankImportFile.file_sha256 == file_sha256
    ).first()
    is_duplicate_file = existing_file is not None

    # Load active bank accounts for quick validation
    active_accounts = {
        acc.account_no: acc for acc in db.query(BankAccount).filter(BankAccount.is_active == True).all()
    }

    # Pre-fetch lookup caches for candidate evaluation
    all_registered_upis = db.query(RegisteredUPI).filter(RegisteredUPI.is_verified == True).all()
    upi_map: Dict[str, List[str]] = {}
    for r in all_registered_upis:
        k = r.upi_id.strip().lower()
        upi_map.setdefault(k, []).append(r.flat_id)

    all_flats = {f.flat_number.upper(): f.id for f in db.query(Flat).all()}

    total_rows = 0
    accepted_rows = 0
    invalid_rows = 0
    total_credit = Decimal("0.00")
    total_debit = Decimal("0.00")
    processed_rows: List[Dict[str, Any]] = []

    seen_utrs: Dict[str, Dict[str, Any]] = {}

    for row_idx, raw in enumerate(reader, start=1):
        total_rows += 1
        errors: List[str] = []

        acc_no = (raw.get("account_no") or "").strip()
        txn_date_str = (raw.get("txn_date") or "").strip()
        value_date_str = (raw.get("value_date") or "").strip()
        narration = (raw.get("narration") or "").strip()
        direction_str = (raw.get("direction") or "").strip().upper()
        amount_str = (raw.get("amount") or "").strip()
        currency_str = (raw.get("currency") or "INR").strip().upper()
        utr_str = (raw.get("utr") or "").strip()
        payer_upi_str = (raw.get("payer_upi") or "").strip()
        flat_ref_str = (raw.get("flat_ref") or "").strip()

        # Account validation
        if not acc_no:
            errors.append("account_no is required")
        elif acc_no not in active_accounts:
            errors.append(f"account_no '{acc_no}' is not a recognized active township bank account")

        # Date validation
        parsed_txn_date = parse_statement_date(txn_date_str)
        if not parsed_txn_date:
            errors.append(f"Invalid txn_date '{txn_date_str}'")

        parsed_val_date = parse_statement_date(value_date_str) if value_date_str else parsed_txn_date

        # Amount validation
        amount_decimal: Optional[Decimal] = None
        if not amount_str:
            errors.append("amount is required")
        else:
            try:
                amt = Decimal(amount_str)
                if amt <= Decimal("0.00"):
                    errors.append(f"Amount must be strictly positive (> 0), got '{amt}'")
                else:
                    amount_decimal = round_currency(amt)
            except (InvalidOperation, ValueError):
                errors.append(f"Invalid numeric amount '{amount_str}'")

        # Direction validation
        if direction_str not in ["CREDIT", "DEBIT"]:
            errors.append(f"Direction must be CREDIT or DEBIT, got '{direction_str}'")

        # Currency validation
        if currency_str != "INR":
            errors.append(f"Unsupported currency '{currency_str}', must be INR")

        is_valid = len(errors) == 0

        # Deterministic Candidate Decision
        candidate_decision: str
        candidate_reason: str
        candidate_action: str

        if not is_valid:
            invalid_rows += 1
            candidate_decision = "INVALID"
            candidate_reason = "; ".join(errors)
            candidate_action = "REJECT"
        else:
            accepted_rows += 1
            assert amount_decimal is not None
            if direction_str == "CREDIT":
                total_credit = round_currency(total_credit + amount_decimal)
            else:
                total_debit = round_currency(total_debit + amount_decimal)

            candidate_decision, candidate_reason, candidate_action = evaluate_candidate_decision(
                db=db,
                acc_no=acc_no,
                direction=direction_str,
                amount=amount_decimal,
                currency=currency_str,
                utr=utr_str,
                payer_upi=payer_upi_str,
                flat_ref=flat_ref_str,
                narration=narration,
                seen_utrs=seen_utrs,
                upi_map=upi_map,
                all_flats=all_flats
            )

        processed_rows.append({
            "row_number": row_idx,
            "raw_row": raw,
            "account_no": acc_no,
            "txn_date": parsed_txn_date.isoformat() if parsed_txn_date else None,
            "value_date": parsed_val_date.isoformat() if parsed_val_date else None,
            "narration": narration,
            "direction": direction_str,
            "amount": str(amount_decimal) if amount_decimal else amount_str,
            "currency": currency_str,
            "utr": utr_str,
            "payer_upi": payer_upi_str,
            "flat_ref": flat_ref_str,
            "is_valid": is_valid,
            "errors": errors,
            "candidate_decision": candidate_decision,
            "candidate_reason": candidate_reason,
            "candidate_action": candidate_action
        })

    return {
        "filename": filename,
        "file_sha256": file_sha256,
        "duplicate_file": is_duplicate_file,
        "total_rows": total_rows,
        "accepted_rows": accepted_rows,
        "invalid_rows": invalid_rows,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "rows": processed_rows
    }


def evaluate_candidate_decision(
    db: Session,
    acc_no: str,
    direction: str,
    amount: Decimal,
    currency: str,
    utr: str,
    payer_upi: str,
    flat_ref: str,
    narration: str,
    seen_utrs: Dict[str, Dict[str, Any]],
    upi_map: Dict[str, List[str]],
    all_flats: Dict[str, str]
) -> tuple[str, str, str]:
    """
    Evaluates row level deterministic matching logic:
    Returns (decision, reason, next_action).
    """
    narration_upper = narration.upper()

    # 1. Cheque pending check
    if "CHQ CLG PENDING" in narration_upper or "CHEQUE PENDING" in narration_upper:
        return "REVIEW", "CHEQUE_CLEARANCE_PENDING", "HOLD"

    # 2. Reversal / Bounce check
    if any(k in narration_upper for k in ["BOUNCE", "REVERSAL", "RTN CHQ", "RETURN CHQ"]):
        return "REVIEW", "REVERSAL_BOUNCE_REVIEW", "HOLD"

    # 3. Direction check (DEBIT rows)
    if direction == "DEBIT":
        return "REVIEW", "DEBIT_ROW_REQUIRES_MANUAL_REVIEW", "HOLD"

    # 4. UTR presence check
    if not utr:
        return "REVIEW", "MISSING_UTR", "HOLD"

    # 5. UTR uniqueness and collision check (in batch and in DB)
    evidence_signature = f"{amount:.2f}:{direction}:{flat_ref.upper()}:{payer_upi.lower()}"
    if utr in seen_utrs:
        prev_sig = seen_utrs[utr]["signature"]
        if prev_sig == evidence_signature:
            return "DUPLICATE_NO_OP", "DUPLICATE_UTR_IDENTICAL_EVIDENCE", "NO_ACTION"
        else:
            return "REVIEW", "UTR_CONFLICT_DIFFERENT_EVIDENCE", "HOLD"

    existing_db_row = db.query(BankRow).filter(BankRow.utr == utr).first()
    if existing_db_row:
        prev_flat = existing_db_row.flat_ref.upper() if existing_db_row.flat_ref else ""
        prev_upi = existing_db_row.payer_upi.lower() if existing_db_row.payer_upi else ""
        prev_amt = f"{existing_db_row.amount:.2f}" if existing_db_row.amount else "0.00"
        db_sig = f"{prev_amt}:{existing_db_row.direction}:{prev_flat}:{prev_upi}"
        if db_sig == evidence_signature:
            seen_utrs[utr] = {"signature": evidence_signature, "decision": "DUPLICATE_NO_OP"}
            return "DUPLICATE_NO_OP", "DUPLICATE_UTR_IDENTICAL_EVIDENCE", "NO_ACTION"
        else:
            seen_utrs[utr] = {"signature": evidence_signature, "decision": "REVIEW"}
            return "REVIEW", "UTR_CONFLICT_DIFFERENT_EVIDENCE", "HOLD"

    seen_utrs[utr] = {"signature": evidence_signature, "decision": "PENDING"}

    # 6. Flat Identification (by flat_ref, payer_upi, or narration)
    matched_flat_id: Optional[str] = None
    flat_ref_upper = flat_ref.strip().upper()
    upi_clean = payer_upi.strip().lower()

    # Case A: Both flat_ref and payer_upi provided
    if flat_ref_upper and upi_clean:
        ref_flat_id = all_flats.get(flat_ref_upper)
        if not ref_flat_id:
            return "REVIEW", "FLAT_REF_NOT_FOUND", "CORRECT_MAPPING"

        upi_flats = upi_map.get(upi_clean, [])
        if not upi_flats:
            return "REVIEW", "UNKNOWN_PAYER_UPI", "CORRECT_MAPPING"
        if ref_flat_id not in upi_flats:
            return "REVIEW", "CONFLICTING_UPI_AND_FLAT_REF", "HOLD"

        matched_flat_id = ref_flat_id

    # Case B: Only payer_upi provided
    elif upi_clean and not flat_ref_upper:
        upi_flats = upi_map.get(upi_clean, [])
        if not upi_flats:
            return "REVIEW", "UNKNOWN_PAYER_UPI", "CORRECT_MAPPING"
        if len(upi_flats) > 1:
            return "REVIEW", "UPI_REUSED_ACROSS_FLATS_AMBIGUOUS", "HOLD"
        matched_flat_id = upi_flats[0]

    # Case C: Only flat_ref provided
    elif flat_ref_upper and not upi_clean:
        ref_flat_id = all_flats.get(flat_ref_upper)
        if not ref_flat_id:
            return "REVIEW", "FLAT_REF_NOT_FOUND", "CORRECT_MAPPING"
        matched_flat_id = ref_flat_id

    # Case D: Neither provided - attempt narration fallback
    else:
        narration_match = re.search(r"\b(T\d{2}-\d{4})\b", narration_upper)
        if narration_match:
            candidate_num = narration_match.group(1)
            ref_flat_id = all_flats.get(candidate_num)
            if ref_flat_id:
                matched_flat_id = ref_flat_id
            else:
                return "REVIEW", "FLAT_REF_NOT_FOUND", "CORRECT_MAPPING"
        else:
            return "REVIEW", "AMOUNT_ONLY_NO_IDENTIFIER", "HOLD"

    if not matched_flat_id:
        return "REVIEW", "NO_REFERENCE_FOUND", "HOLD"

    # 7. Bill Balance Matching
    open_bills = db.query(Bill).filter(
        Bill.flat_id == matched_flat_id,
        Bill.balance_amount > Decimal("0.00")
    ).order_by(Bill.due_date.asc()).all()

    if not open_bills:
        return "REVIEW", "OVERPAYMENT_ALL_BILLS_PAID", "HOLD"

    # Ambiguity check: multiple open bills with exact same balance matching amount
    matching_bills = [b for b in open_bills if b.balance_amount == amount]
    if len(matching_bills) > 1:
        return "REVIEW", "AMBIGUOUS_MULTI_BILL_MATCH", "HOLD"

    target_bill = open_bills[0]

    if amount == target_bill.balance_amount:
        if flat_ref_upper and upi_clean:
            return "AUTO_MATCH", "EXACT_BALANCE_MATCH", "APPROVE"
        elif upi_clean:
            return "AUTO_MATCH", "EXACT_BALANCE_MATCH_UPI", "APPROVE"
        else:
            return "AUTO_MATCH", "EXACT_BALANCE_MATCH_FLAT_REF", "APPROVE"
    elif amount < target_bill.balance_amount:
        return "REVIEW", "PARTIAL_PAYMENT_REQUIRES_REVIEW", "HOLD"
    else:
        return "REVIEW", "OVERPAYMENT_EXCEEDS_BALANCE", "HOLD"


def commit_bank_statement(
    db: Session,
    content: Union[str, bytes],
    filename: str,
    uploaded_by_user_id: str,
    bank_account_no: Optional[str] = None
) -> Dict[str, Any]:
    """
    Idempotent commit matching service keyed by (account_no, file_sha256).
    Preserves invalid rows with reasons.
    Auto-posts payments for strictly verified rows.
    """
    content_bytes, file_sha256 = calculate_content_sha256(content)
    text_content = content_bytes.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise ValueError("Bank statement file is empty or missing headers.")

    cleaned_headers = [h.strip() for h in reader.fieldnames]
    missing_headers = [h for h in EXPECTED_HEADERS if h not in cleaned_headers]
    if missing_headers:
        raise ValueError(f"Missing required CSV headers: {', '.join(missing_headers)}")

    # 1. Determine Township Bank Account
    target_bank_account: Optional[BankAccount] = None
    if bank_account_no:
        target_bank_account = db.query(BankAccount).filter(
            BankAccount.account_no == bank_account_no,
            BankAccount.is_active == True
        ).first()

    first_row_acc: Optional[str] = None
    rows_data = list(reader)
    if rows_data:
        first_row_acc = (rows_data[0].get("account_no") or "").strip()

    if not target_bank_account and first_row_acc:
        target_bank_account = db.query(BankAccount).filter(
            BankAccount.account_no == first_row_acc,
            BankAccount.is_active == True
        ).first()

    if not target_bank_account:
        raise ValueError("No recognized active bank account found for statement import.")

    # 2. File-Level Idempotency check: (account_no, file_sha256)
    existing_import = db.query(BankImportFile).filter(
        BankImportFile.bank_account_id == target_bank_account.id,
        BankImportFile.file_sha256 == file_sha256
    ).first()

    if existing_import:
        existing_rows = db.query(BankRow).filter(
            BankRow.import_file_id == existing_import.id
        ).order_by(BankRow.original_row_number.asc()).all()

        return {
            "status": "ALREADY_PROCESSED",
            "import_file_id": existing_import.id,
            "filename": existing_import.filename,
            "file_sha256": existing_import.file_sha256,
            "total_rows": existing_import.total_rows,
            "accepted_rows": existing_import.accepted_rows,
            "invalid_rows": existing_import.invalid_rows,
            "rows": [
                {
                    "row_number": r.original_row_number,
                    "direction": r.direction,
                    "amount": str(r.amount) if r.amount else None,
                    "utr": r.utr,
                    "decision": r.decision,
                    "decision_reason": r.decision_reason,
                    "review_status": r.review_status,
                    "matched_payment_id": r.matched_payment_id,
                    "matched_bill_id": r.matched_bill_id
                }
                for r in existing_rows
            ]
        }

    # 3. Create BankImportFile record
    import_file = BankImportFile(
        bank_account_id=target_bank_account.id,
        filename=filename,
        file_sha256=file_sha256,
        uploaded_by_user_id=uploaded_by_user_id,
        uploaded_at=datetime.now(timezone.utc),
        total_rows=0,
        accepted_rows=0,
        invalid_rows=0
    )
    db.add(import_file)
    db.flush()

    # Pre-fetch lookup caches
    active_accounts = {
        acc.account_no: acc for acc in db.query(BankAccount).filter(BankAccount.is_active == True).all()
    }
    all_registered_upis = db.query(RegisteredUPI).filter(RegisteredUPI.is_verified == True).all()
    upi_map: Dict[str, List[str]] = {}
    for r in all_registered_upis:
        k = r.upi_id.strip().lower()
        upi_map.setdefault(k, []).append(r.flat_id)

    all_flats = {f.flat_number.upper(): f.id for f in db.query(Flat).all()}

    total_rows = 0
    accepted_rows = 0
    invalid_rows = 0
    seen_utrs: Dict[str, Dict[str, Any]] = {}
    committed_rows: List[BankRow] = []

    for row_idx, raw in enumerate(rows_data, start=1):
        total_rows += 1
        errors: List[str] = []

        acc_no = (raw.get("account_no") or "").strip()
        txn_date_str = (raw.get("txn_date") or "").strip()
        value_date_str = (raw.get("value_date") or "").strip()
        narration = (raw.get("narration") or "").strip()
        direction_str = (raw.get("direction") or "").strip().upper()
        amount_str = (raw.get("amount") or "").strip()
        currency_str = (raw.get("currency") or "INR").strip().upper()
        utr_str = (raw.get("utr") or "").strip()
        payer_upi_str = (raw.get("payer_upi") or "").strip()
        flat_ref_str = (raw.get("flat_ref") or "").strip()

        # Validations
        if not acc_no:
            errors.append("account_no is required")
        elif acc_no not in active_accounts:
            errors.append(f"account_no '{acc_no}' is not a recognized active township bank account")

        parsed_txn_date = parse_statement_date(txn_date_str)
        if not parsed_txn_date:
            errors.append(f"Invalid txn_date '{txn_date_str}'")

        parsed_val_date = parse_statement_date(value_date_str) if value_date_str else parsed_txn_date

        amount_decimal: Optional[Decimal] = None
        if not amount_str:
            errors.append("amount is required")
        else:
            try:
                amt = Decimal(amount_str)
                if amt <= Decimal("0.00"):
                    errors.append(f"Amount must be strictly positive (> 0), got '{amt}'")
                else:
                    amount_decimal = round_currency(amt)
            except (InvalidOperation, ValueError):
                errors.append(f"Invalid numeric amount '{amount_str}'")

        if direction_str not in ["CREDIT", "DEBIT"]:
            errors.append(f"Direction must be CREDIT or DEBIT, got '{direction_str}'")

        if currency_str != "INR":
            errors.append(f"Unsupported currency '{currency_str}', must be INR")

        is_valid = len(errors) == 0

        bank_row = BankRow(
            id=str(uuid.uuid4()),
            import_file_id=import_file.id,
            bank_account_id=target_bank_account.id,
            original_row_number=row_idx,
            raw_row=raw,
            txn_date=parsed_txn_date,
            value_date=parsed_val_date,
            narration=narration,
            direction=direction_str if direction_str in ["CREDIT", "DEBIT"] else None,
            amount=amount_decimal,
            currency=currency_str,
            utr=utr_str or None,
            payer_upi=payer_upi_str or None,
            flat_ref=flat_ref_str or None,
            parse_status="ACCEPTED" if is_valid else "INVALID",
            parse_errors=errors if errors else None,
            review_status="PENDING",
            audit_trail=[{
                "action": "IMPORTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": uploaded_by_user_id
            }]
        )

        if not is_valid:
            invalid_rows += 1
            bank_row.decision = "INVALID"
            bank_row.decision_reason = "; ".join(errors)
            bank_row.next_action = "REJECT"
        else:
            accepted_rows += 1
            assert amount_decimal is not None

            decision, reason, action = evaluate_candidate_decision(
                db=db,
                acc_no=acc_no,
                direction=direction_str,
                amount=amount_decimal,
                currency=currency_str,
                utr=utr_str,
                payer_upi=payer_upi_str,
                flat_ref=flat_ref_str,
                narration=narration,
                seen_utrs=seen_utrs,
                upi_map=upi_map,
                all_flats=all_flats
            )

            bank_row.decision = decision
            bank_row.decision_reason = reason
            bank_row.next_action = action

            # Flat linking
            resolved_flat_id: Optional[str] = None
            if flat_ref_str.strip().upper() in all_flats:
                resolved_flat_id = all_flats[flat_ref_str.strip().upper()]
            elif payer_upi_str.strip().lower() in upi_map:
                fl_list = upi_map[payer_upi_str.strip().lower()]
                if len(fl_list) == 1:
                    resolved_flat_id = fl_list[0]
            bank_row.matched_flat_id = resolved_flat_id

            # If AUTO_MATCH: execute post payment logic immediately in this transaction
            if decision == "AUTO_MATCH" and resolved_flat_id:
                open_bill = db.query(Bill).filter(
                    Bill.flat_id == resolved_flat_id,
                    Bill.balance_amount == amount_decimal
                ).order_by(Bill.due_date.asc()).first()

                if open_bill:
                    db.add(bank_row)
                    db.flush()
                    post_bank_payment(
                        db=db,
                        bank_row=bank_row,
                        bill=open_bill,
                        user_id=uploaded_by_user_id,
                        actor_role="SYSTEM"
                    )
                    bank_row.review_status = "AUTO_POSTED"
                    bank_row.next_action = "APPROVE"
                else:
                    # Defensive fallback: if bill balance shifted, hold for review
                    bank_row.decision = "REVIEW"
                    bank_row.decision_reason = "BILL_BALANCE_SHIFTED_DURING_COMMIT"
                    bank_row.next_action = "HOLD"

        if bank_row not in db:
            db.add(bank_row)
        committed_rows.append(bank_row)

    # 4. Finalize Import Record
    import_file.total_rows = total_rows
    import_file.accepted_rows = accepted_rows
    import_file.invalid_rows = invalid_rows

    db.commit()

    return {
        "status": "COMMITTED",
        "import_file_id": import_file.id,
        "filename": filename,
        "file_sha256": file_sha256,
        "total_rows": total_rows,
        "accepted_rows": accepted_rows,
        "invalid_rows": invalid_rows,
        "rows": [
            {
                "row_number": r.original_row_number,
                "direction": r.direction,
                "amount": str(r.amount) if r.amount else None,
                "utr": r.utr,
                "decision": r.decision,
                "decision_reason": r.decision_reason,
                "review_status": r.review_status,
                "matched_payment_id": r.matched_payment_id,
                "matched_bill_id": r.matched_bill_id
            }
            for r in committed_rows
        ]
    }


def post_bank_payment(
    db: Session,
    bank_row: BankRow,
    bill: Bill,
    user_id: Optional[str] = None,
    actor_role: str = "SYSTEM"
) -> Payment:
    """
    Executes post-payment logic in active DB transaction with row lock on Bill.
    Updates Bill, creates Payment & FlatLedgerEntry, records AuditEvent.
    If settling an existing test checkout, links without duplicate payment.
    """
    # 1. Acquire row lock on Bill (dialect aware)
    bill_query = db.query(Bill).filter(Bill.id == bill.id)
    if db.bind and db.bind.dialect.name != "sqlite":
        bill_query = bill_query.with_for_update()
    locked_bill = bill_query.first()
    if not locked_bill:
        raise ValueError(f"Bill {bill.id} not found.")

    payment_amount = round_currency(bank_row.amount) if bank_row.amount else Decimal("0.00")
    if payment_amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be greater than zero.")

    # 2. Check if settling an existing checkout
    existing_payment: Optional[Payment] = None
    if bank_row.utr:
        existing_payment = db.query(Payment).filter(
            Payment.bill_id == locked_bill.id,
            Payment.transaction_reference == bank_row.utr
        ).first()

    if not existing_payment:
        # Check if there is an existing PENDING payment on this bill with identical amount
        existing_payment = db.query(Payment).filter(
            Payment.bill_id == locked_bill.id,
            Payment.amount == payment_amount,
            Payment.status == "PENDING"
        ).first()

    now_dt = datetime.now(timezone.utc)
    txn_time = bank_row.txn_date or now_dt

    already_settled = False
    if existing_payment:
        if existing_payment.status == "SUCCESS":
            already_settled = True
        existing_payment.status = "SUCCESS"
        existing_payment.payment_method = "BANK_MATCHED"
        existing_payment.paid_at = txn_time
        payment = existing_payment

        existing_ledger = db.query(FlatLedgerEntry).filter(
            FlatLedgerEntry.reference_id == payment.id
        ).first()
        if existing_ledger:
            already_settled = True
    else:
        # Create fresh Payment record
        utr_ref = bank_row.utr or f"BANK-TXN-{uuid.uuid4().hex[:12].upper()}"
        receipt_no = f"REC-BNK-{txn_time.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        payment = Payment(
            flat_id=locked_bill.flat_id,
            bill_id=locked_bill.id,
            amount=payment_amount,
            currency="INR",
            payment_method="BANK_TRANSFER",
            status="SUCCESS",
            transaction_reference=utr_ref,
            idempotency_key=f"BANK-UTR-{utr_ref}",
            paid_at=txn_time,
            receipt_number=receipt_no,
            payer_user_id=user_id,
            created_at=now_dt
        )
        db.add(payment)
        db.flush()

        # Create Receipt record
        flat = db.query(Flat).filter(Flat.id == locked_bill.flat_id).first()
        flat_str = flat.flat_number if flat else "Unknown"
        resident_name = "Society Resident"
        if user_id:
            u = db.query(User).filter(User.id == user_id).first()
            if u:
                resident_name = u.name

        receipt = Receipt(
            payment_id=payment.id,
            receipt_number=receipt_no,
            flat_number=flat_str,
            resident_name=resident_name,
            amount=payment_amount,
            payment_mode="BANK_TRANSFER",
            transaction_reference=utr_ref,
            issued_at=txn_time
        )
        db.add(receipt)

    if not already_settled:
        # 3. Update Bill balances
        locked_bill.paid_amount = round_currency(locked_bill.paid_amount + payment_amount)
        locked_bill.balance_amount = round_currency(locked_bill.total_amount - locked_bill.paid_amount)
        if locked_bill.balance_amount == Decimal("0.00"):
            locked_bill.status = "PAID"
        else:
            locked_bill.status = "PARTIALLY_PAID"

        # 4. Post Dual-Entry Credit to Flat Ledger
        last_ledger = db.query(FlatLedgerEntry).filter(
            FlatLedgerEntry.flat_id == locked_bill.flat_id
        ).order_by(FlatLedgerEntry.created_at.desc(), FlatLedgerEntry.id.desc()).first()

        prev_balance = last_ledger.balance_after if last_ledger else Decimal("0.00")
        new_balance = round_currency(prev_balance - payment_amount)

        ledger_entry = FlatLedgerEntry(
            flat_id=locked_bill.flat_id,
            entry_type="CREDIT",
            amount=payment_amount,
            balance_after=new_balance,
            description=f"Bank Statement Credit - UTR {bank_row.utr or 'N/A'}",
            reference_id=payment.id,
            created_at=txn_time
        )
        db.add(ledger_entry)

    # 5. Link BankRow
    bank_row.matched_payment_id = payment.id
    bank_row.matched_bill_id = locked_bill.id
    bank_row.matched_flat_id = locked_bill.flat_id

    # 6. Audit Trail & AuditEvent
    audit = AuditEvent(
        entity_type="BANK_ROW",
        entity_id=bank_row.id,
        action="AUTO_MATCH_POSTED",
        actor_user_id=user_id,
        actor_role=actor_role,
        old_state=None,
        new_state={
            "bill_id": locked_bill.id,
            "payment_id": payment.id,
            "amount": str(payment_amount),
            "new_balance": str(locked_bill.balance_amount),
            "status": locked_bill.status
        },
        reason=f"Auto-match verified: UTR {bank_row.utr} posted to Bill {locked_bill.id}",
        created_at=now_dt
    )
    db.add(audit)
    db.flush()

    return payment


def handle_review_action(
    db: Session,
    bank_row_id: str,
    action: str,
    reviewer_user_id: str,
    target_flat_id: Optional[str] = None,
    target_bill_id: Optional[str] = None,
    reason: Optional[str] = None
) -> BankRow:
    """
    Review action handler for human-in-the-loop accounts workflow:
    - APPROVE: Posts payment to open bill & ledger atomically
    - REJECT: Marks row as rejected with required reason
    - HOLD: Puts row on hold for clarification
    - CORRECT_MAPPING: Remaps flat and optional bill
    Guarantees concurrency safety (concurrent approvals of one row post exactly once).
    """
    valid_actions = {"APPROVE", "REJECT", "HOLD", "CORRECT_MAPPING"}
    if action not in valid_actions:
        raise ValueError(f"Invalid action '{action}'. Allowed: {sorted(list(valid_actions))}")

    # Row-level lock on BankRow
    row_query = db.query(BankRow).filter(BankRow.id == bank_row_id)
    if db.bind and db.bind.dialect.name != "sqlite":
        row_query = row_query.with_for_update()
    bank_row = row_query.first()
    if not bank_row:
        raise ValueError(f"BankRow with ID '{bank_row_id}' not found.")

    # Concurrency guard: if already finalized, return safely without duplicate posting
    if bank_row.review_status in ["APPROVED", "AUTO_POSTED"]:
        return bank_row

    now_dt = datetime.now(timezone.utc)
    old_state = {
        "review_status": bank_row.review_status,
        "matched_flat_id": bank_row.matched_flat_id,
        "matched_bill_id": bank_row.matched_bill_id,
        "matched_payment_id": bank_row.matched_payment_id
    }

    if action == "APPROVE":
        if bank_row.direction == "DEBIT":
            raise ValueError("Cannot approve DEBIT transaction as resident maintenance payment.")

        # Determine target flat
        chosen_flat_id = target_flat_id or bank_row.matched_flat_id
        if not chosen_flat_id:
            raise ValueError("Cannot approve row without an assigned flat.")

        # Determine target bill
        target_bill: Optional[Bill] = None
        if target_bill_id:
            target_bill = db.query(Bill).filter(
                Bill.id == target_bill_id,
                Bill.flat_id == chosen_flat_id
            ).first()
        elif bank_row.matched_bill_id:
            target_bill = db.query(Bill).filter(
                Bill.id == bank_row.matched_bill_id,
                Bill.flat_id == chosen_flat_id
            ).first()
        else:
            target_bill = db.query(Bill).filter(
                Bill.flat_id == chosen_flat_id,
                Bill.balance_amount > Decimal("0.00")
            ).order_by(Bill.due_date.asc()).first()

        if not target_bill:
            raise ValueError("No open bill found to allocate approved payment.")

        # Execute posting logic
        post_bank_payment(
            db=db,
            bank_row=bank_row,
            bill=target_bill,
            user_id=reviewer_user_id,
            actor_role="ACCOUNTS"
        )
        bank_row.review_status = "APPROVED"
        bank_row.reviewed_by_user_id = reviewer_user_id
        bank_row.reviewed_at = now_dt
        bank_row.correction_reason = reason or "Manually approved by accounts staff"

    elif action == "REJECT":
        bank_row.review_status = "REJECTED"
        bank_row.reviewed_by_user_id = reviewer_user_id
        bank_row.reviewed_at = now_dt
        bank_row.correction_reason = reason or "Rejected during accounts review"

    elif action == "HOLD":
        bank_row.review_status = "HELD"
        bank_row.reviewed_by_user_id = reviewer_user_id
        bank_row.reviewed_at = now_dt
        bank_row.correction_reason = reason or "Held for investigation"

    elif action == "CORRECT_MAPPING":
        if not target_flat_id:
            raise ValueError("Target flat ID is required to correct mapping.")
        bank_row.matched_flat_id = target_flat_id
        if target_bill_id:
            bank_row.matched_bill_id = target_bill_id
        bank_row.review_status = "CORRECTED"
        bank_row.reviewed_by_user_id = reviewer_user_id
        bank_row.reviewed_at = now_dt
        bank_row.correction_reason = reason or f"Mapping corrected to flat {target_flat_id}"

    # Audit log
    audit = AuditEvent(
        entity_type="BANK_ROW",
        entity_id=bank_row.id,
        action=f"REVIEW_{action}",
        actor_user_id=reviewer_user_id,
        actor_role="ACCOUNTS",
        old_state=old_state,
        new_state={
            "review_status": bank_row.review_status,
            "matched_flat_id": bank_row.matched_flat_id,
            "matched_bill_id": bank_row.matched_bill_id,
            "matched_payment_id": bank_row.matched_payment_id
        },
        reason=bank_row.correction_reason,
        created_at=now_dt
    )
    db.add(audit)
    db.commit()
    db.refresh(bank_row)
    return bank_row
