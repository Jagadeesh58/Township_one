"""
Township One - Synthetic Bank Statement Corpus Generator.

Generates a deterministic dataset (>= 300 labelled rows) covering all real-world banking edge cases:
- Exact matches (both registered UPI and flat_ref present, amount equals open bill balance)
- UPI-only matches (registered UPI present, flat_ref blank)
- Flat-ref-only matches (flat_ref present, UPI blank)
- Duplicate UTR with identical evidence
- UTR conflict (duplicate UTR with different amount or flat)
- Amount-only matches without identifier
- Unknown / unregistered UPI
- Reused UPI across multiple flats
- Conflicting reference and UPI
- Debit rows (vendor charges, utility debits)
- Wrong bank account number
- Partial payments (amount less than open bill balance)
- Overpayments (amount greater than open bill balance)
- Missing reference / unidentifiable narration
- Cheque pending clearance
- Reversals and bounce records
- Multi-match ambiguity (multiple open bills without disambiguation)
"""

import os
import csv
import random
from decimal import Decimal
from datetime import datetime, timedelta

DEFAULT_ACCOUNT_NO = "98765432100012"
WRONG_ACCOUNT_NO = "99998888777766"


def generate_corpus(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    base_dt = datetime(2026, 11, 1, 9, 0, 0)

    rows: list[dict] = []
    utr_counter = 10000

    def next_utr() -> str:
        nonlocal utr_counter
        utr_counter += 1
        return f"UTR202611{utr_counter:06d}"

    def dt_str(offset_hours: int) -> tuple[str, str]:
        t = base_dt + timedelta(hours=offset_hours)
        return t.strftime("%Y-%m-%d %H:%M:%S"), t.strftime("%Y-%m-%d")

    hour_idx = 0

    # Pool of flats and standard monthly maintenance amounts
    # T01 has 86 flats; unit 1: 10660.00, unit 2: 9230.00, unit 3: 7475.00, unit 4: 6370.00
    exact_flats = [
        (f"T01-{fl:02d}01", "10660.00", f"resident.t01.{fl:02d}01@okhdfcbank") for fl in range(1, 16)
    ] + [
        (f"T01-{fl:02d}02", "9230.00", f"resident.t01.{fl:02d}02@okaxis") for fl in range(1, 16)
    ] + [
        (f"T01-{fl:02d}03", "7475.00", f"resident.t01.{fl:02d}03@icici") for fl in range(1, 16)
    ] + [
        (f"T01-{fl:02d}04", "6370.00", f"resident.t01.{fl:02d}04@paytm") for fl in range(1, 16)
    ]
    # Total exact_flats = 60 flats

    # 1. Exact Matches (Full - Both UPI and Flat Ref) - 60 rows
    for flat_num, amount, upi in exact_flats:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/{flat_num}/MAINTENANCE BILL",
            "direction": "CREDIT",
            "amount": amount,
            "currency": "INR",
            "utr": utr,
            "payer_upi": upi,
            "flat_ref": flat_num,
            "expected_decision": "AUTO_MATCH",
            "expected_reason": "REGISTERED_UPI_AND_FLAT_REFERENCE",
            "category": "EXACT_MATCH_FULL"
        })

    # 2. UPI-Only Valid Matches (Flat Ref empty, registered UPI present) - 30 rows
    upi_only_flats = [
        (f"T02-{fl:02d}01", "10660.00", f"user.t02.{fl:02d}01@okhdfcbank") for fl in range(1, 11)
    ] + [
        (f"T02-{fl:02d}02", "9230.00", f"user.t02.{fl:02d}02@okaxis") for fl in range(1, 11)
    ] + [
        (f"T02-{fl:02d}03", "7475.00", f"user.t02.{fl:02d}03@icici") for fl in range(1, 11)
    ]
    for flat_num, amount, upi in upi_only_flats:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/TRANSFER FROM {upi}",
            "direction": "CREDIT",
            "amount": amount,
            "currency": "INR",
            "utr": utr,
            "payer_upi": upi,
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "UPI_ONLY_REVIEW",
            "category": "UPI_ONLY_MATCH"
        })

    # 3. Flat-Ref-Only Valid Matches (UPI empty, flat_ref present) - 30 rows
    flat_ref_only_flats = [
        (f"T02-{fl:02d}04", "6370.00") for fl in range(1, 16)
    ] + [
        (f"T03-{fl:02d}03", "7475.00") for fl in range(1, 16)
    ]
    for flat_num, amount in flat_ref_only_flats:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"NEFT/SOCIETY DUES/{flat_num}",
            "direction": "CREDIT",
            "amount": amount,
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": flat_num,
            "expected_decision": "REVIEW",
            "expected_reason": "FLAT_REF_ONLY_REVIEW",
            "category": "FLAT_REF_ONLY_MATCH"
        })

    # Pick 20 existing rows from exact_flats to use for duplicate tests
    saved_exact_rows = [dict(r) for r in rows[:20]]

    # 4. Duplicate UTR with Same Evidence - 20 rows
    for orig in saved_exact_rows:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        dup = dict(orig)
        dup["txn_date"] = txn_d
        dup["value_date"] = val_d
        dup["expected_decision"] = "DUPLICATE_NO_OP"
        dup["expected_reason"] = "DUPLICATE_UTR_IDENTICAL_EVIDENCE"
        dup["category"] = "DUPLICATE_UTR_SAME_EVIDENCE"
        rows.append(dup)

    # 5. UTR Conflict (Same UTR, conflicting amount or flat) - 20 rows
    for idx_u, orig in enumerate(saved_exact_rows):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        conflict_row = dict(orig)
        conflict_row["txn_date"] = txn_d
        conflict_row["value_date"] = val_d
        # Alter amount or flat to trigger conflict
        if idx_u % 2 == 0:
            conflict_row["amount"] = str(Decimal(conflict_row["amount"]) + Decimal("150.00"))
        else:
            conflict_row["flat_ref"] = "T08-0101"
            conflict_row["narration"] = "UPI/CONFLICTING EVIDENCE"
        conflict_row["expected_decision"] = "REVIEW"
        conflict_row["expected_reason"] = "UTR_CONFLICT_DIFFERENT_EVIDENCE"
        conflict_row["category"] = "UTR_CONFLICT"
        rows.append(conflict_row)

    # 6. Amount-Only (No UPI and no flat_ref, amount matches open bill) - 20 rows
    amount_only_amounts = ["10660.00", "9230.00", "7475.00", "6370.00"] * 5
    for amt in amount_only_amounts:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": "IMPS/ANONYMOUS PAYMENT RECEIVED",
            "direction": "CREDIT",
            "amount": amt,
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "AMOUNT_ONLY_REVIEW",
            "category": "AMOUNT_ONLY"
        })

    # 7. Unknown / Unregistered UPI - 20 rows
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        fake_upi = f"unknown.stranger.{k:03d}@unknownbank"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/FROM {fake_upi}/UNREGISTERED",
            "direction": "CREDIT",
            "amount": "7475.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": fake_upi,
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "UNKNOWN_PAYER_UPI",
            "category": "UNKNOWN_UPI"
        })

    # 8. UPI Reused Across Multiple Flats - 20 rows
    # In test setup, shared.family@okhdfcbank is mapped to both T04-0101 and T04-0102
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/SHARED UPI PAYMENT {k}",
            "direction": "CREDIT",
            "amount": "10660.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "shared.family@okhdfcbank",
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "UPI_REUSED_ACROSS_FLATS_AMBIGUOUS",
            "category": "UPI_REUSED_ACROSS_FLATS"
        })

    # 9. Conflicting Reference / UPI - 20 rows
    # UPI belongs to T01-0101, but flat_ref points to T01-0102
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/MISMATCHED SENDER FOR FLAT T01-02{k:02d}",
            "direction": "CREDIT",
            "amount": "10660.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "resident.t01.0101@okhdfcbank",
            "flat_ref": f"T01-02{k:02d}",
            "expected_decision": "REVIEW",
            "expected_reason": "CONFLICTING_UPI_AND_FLAT_REF",
            "category": "CONFLICTING_REF_AND_UPI"
        })

    # 10. Debit Rows - 20 rows
    debit_descriptions = [
        ("MSEB ELECTRICITY HT SUBSTATION", "35000.00"),
        ("ELEVATOR AMC OTIS CHARGES", "18500.00"),
        ("WATER TANKER SUPPLY INVOICE", "12000.00"),
        ("SECURITY GUARD AGENCY SALARY", "48000.00"),
    ] * 5
    for desc, amt in debit_descriptions:
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": desc,
            "direction": "DEBIT",
            "amount": amt,
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "DEBIT_ROW_REQUIRES_MANUAL_REVIEW",
            "category": "DEBIT_ROW"
        })

    # 11. Wrong Bank Account Number - 15 rows
    for k in range(1, 16):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": WRONG_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"NEFT/INCORRECT TARGET ACC/{k}",
            "direction": "CREDIT",
            "amount": "7475.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": f"T01-03{k:02d}",
            "expected_decision": "REVIEW",
            "expected_reason": "UNRECOGNIZED_BANK_ACCOUNT",
            "category": "WRONG_ACCOUNT"
        })

    # 12. Partial Payments (amount < open balance) - 20 rows
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        target_flat = f"T05-{k:02d}01"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/PARTIAL PAYMENT FOR {target_flat}",
            "direction": "CREDIT",
            "amount": "4000.00",  # Full bill is 10660.00
            "currency": "INR",
            "utr": utr,
            "payer_upi": f"resident.t05.{k:02d}01@okhdfcbank",
            "flat_ref": target_flat,
            "expected_decision": "REVIEW",
            "expected_reason": "PARTIAL_PAYMENT_REQUIRES_REVIEW",
            "category": "PARTIAL_PAYMENT"
        })

    # 13. Overpayments (amount > open balance) - 20 rows
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        target_flat = f"T05-{k:02d}02"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/EXCESS PAYMENT FOR {target_flat}",
            "direction": "CREDIT",
            "amount": "15000.00",  # Full bill is 9230.00
            "currency": "INR",
            "utr": utr,
            "payer_upi": f"resident.t05.{k:02d}02@okaxis",
            "flat_ref": target_flat,
            "expected_decision": "REVIEW",
            "expected_reason": "OVERPAYMENT_EXCEEDS_BALANCE",
            "category": "OVERPAYMENT"
        })

    # 14. Missing Reference / Unidentifiable Narration - 20 rows
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"NEFT CR-CITI0000004-MISC DUES {k}",
            "direction": "CREDIT",
            "amount": "6370.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": "",
            "expected_decision": "REVIEW",
            "expected_reason": "AMOUNT_ONLY_REVIEW",
            "category": "NO_REFERENCE"
        })

    # 15. Cheque Pending Clearance - 15 rows
    for k in range(1, 16):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        target_flat = f"T05-{k:02d}03"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"CHQ CLG PENDING T05-{k:02d}03 CHQ 5588{k:02d}",
            "direction": "CREDIT",
            "amount": "7475.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": target_flat,
            "expected_decision": "REVIEW",
            "expected_reason": "CHEQUE_CLEARANCE_PENDING",
            "category": "CHEQUE_PENDING"
        })

    # 16. Reversal / Bounce Records - 15 rows
    for k in range(1, 16):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        target_flat = f"T05-{k:02d}04"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"REV RTN CHQ 7722{k:02d} BOUNCE INSUFF FUNDS",
            "direction": "DEBIT",
            "amount": "6370.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": "",
            "flat_ref": target_flat,
            "expected_decision": "REVIEW",
            "expected_reason": "REVERSAL_BOUNCE_REVIEW",
            "category": "REVERSAL_BOUNCE"
        })

    # 17. Multi-Match Ambiguity (Multiple open bills for flat or ambiguous candidates) - 20 rows
    # In test setup, flats T06-0101 .. T06-2001 have two active open bills each
    for k in range(1, 21):
        hour_idx += 1
        txn_d, val_d = dt_str(hour_idx)
        utr = next_utr()
        target_flat = f"T06-{k:02d}01"
        rows.append({
            "account_no": DEFAULT_ACCOUNT_NO,
            "txn_date": txn_d,
            "value_date": val_d,
            "narration": f"UPI/MULTI BILL AMBIGUITY/{target_flat}",
            "direction": "CREDIT",
            "amount": "10660.00",
            "currency": "INR",
            "utr": utr,
            "payer_upi": f"resident.t06.{k:02d}01@okhdfcbank",
            "flat_ref": target_flat,
            "expected_decision": "REVIEW",
            "expected_reason": "AMBIGUOUS_MULTI_BILL_MATCH",
            "category": "MULTI_MATCH_AMBIGUITY"
        })

    return rows


def write_corpus_csv(filepath: str, rows: list[dict]) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fieldnames = [
        "account_no", "txn_date", "value_date", "narration", "direction",
        "amount", "currency", "utr", "payer_upi", "flat_ref",
        "expected_decision", "expected_reason", "category"
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return filepath


if __name__ == "__main__":
    generated_rows = generate_corpus(seed=42)
    out_path = os.path.join(os.path.dirname(__file__), "corpus_300.csv")
    write_corpus_csv(out_path, generated_rows)
    print(f"Generated {len(generated_rows)} labelled bank statement corpus rows into {out_path}.")
