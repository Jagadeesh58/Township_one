"""
Township One - Bank Statement Match Engine Verification.

Tests verifying:
- Non-mutating preview functionality with strict format validation
- 385-row deterministic corpus processing
- ZERO false automatic postings (no non-matching rows ever auto-posted)
- Non-empty reasons for every held row
- Replay idempotency (replaying identical file creates no new ledger entries)
- Concurrency safety (concurrent approvals of one row post exactly once)
- Ledger totals reconciliation (ledger credits match sum of approved payments)
- Standalone auto-match coverage percentage metric
"""

import io
import csv
from decimal import Decimal
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.entities import (
    BankAccount, BankImportFile, BankRow, BankPosting, Flat, Bill, BillLine,
    Payment, FlatLedgerEntry, RegisteredUPI, User
)
from backend.app.services.bank_matching import (
    preview_bank_statement, commit_bank_statement, handle_review_action
)
from backend.app.services.billing import round_currency
from tests.bank_corpus.generate_corpus import generate_corpus, write_corpus_csv


def provision_corpus_environment(db: Session, account_no: str = "98765432100012"):
    """
    Provisions open bills and registered UPI mappings required by the 385-row synthetic corpus.
    """
    # 1. Bank Account
    bank_acc = db.query(BankAccount).filter(BankAccount.account_no == account_no).first()
    if not bank_acc:
        bank_acc = BankAccount(
            account_no=account_no,
            bank_name="HDFC Bank - Township One Operations",
            ifsc_code="HDFC0001234",
            is_active=True
        )
        db.add(bank_acc)
        db.flush()

    # 2. Uploader Admin
    admin_user = db.query(User).filter(User.phone == "9876543200").first()
    assert admin_user is not None

    # Cache flats
    flats = {f.flat_number: f for f in db.query(Flat).all()}

    # Clean prior bills & UPIs for test towers T01..T06
    test_towers = ["T01-", "T02-", "T03-", "T04-", "T05-", "T06-"]
    target_flat_ids = [f.id for f_num, f in flats.items() if any(f_num.startswith(tw) for tw in test_towers)]

    db.query(BankPosting).delete(synchronize_session=False)
    db.query(BankRow).delete(synchronize_session=False)
    db.query(BankImportFile).delete(synchronize_session=False)
    db.query(FlatLedgerEntry).filter(FlatLedgerEntry.flat_id.in_(target_flat_ids)).delete(synchronize_session=False)
    db.query(Payment).filter(Payment.flat_id.in_(target_flat_ids)).delete(synchronize_session=False)
    db.query(BillLine).filter(BillLine.bill_id.in_(
        db.query(Bill.id).filter(Bill.flat_id.in_(target_flat_ids))
    )).delete(synchronize_session=False)
    db.query(Bill).filter(Bill.flat_id.in_(target_flat_ids)).delete(synchronize_session=False)
    db.query(RegisteredUPI).filter(RegisteredUPI.flat_id.in_(target_flat_ids)).delete(synchronize_session=False)
    db.commit()

    # Provision Tower 1 (Exact full match flats: T01-0101 to T01-1504)
    for fl in range(1, 16):
        # Unit 1: 10660.00
        f_num1 = f"T01-{fl:02d}01"
        amt1 = Decimal("10660.00")
        f1 = flats[f_num1]
        b1 = Bill(flat_id=f1.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                  issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                  area_sqft=Decimal("1640.00"), rate_per_sqft=Decimal("6.50"), principal_amount=amt1,
                  total_amount=amt1, paid_amount=Decimal("0.00"), balance_amount=amt1, status="ISSUED")
        db.add(b1)
        db.add(RegisteredUPI(flat_id=f1.id, upi_id=f"resident.t01.{fl:02d}01@okhdfcbank", is_verified=True))

        # Unit 2: 9230.00
        f_num2 = f"T01-{fl:02d}02"
        amt2 = Decimal("9230.00")
        f2 = flats[f_num2]
        b2 = Bill(flat_id=f2.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                  issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                  area_sqft=Decimal("1420.00"), rate_per_sqft=Decimal("6.50"), principal_amount=amt2,
                  total_amount=amt2, paid_amount=Decimal("0.00"), balance_amount=amt2, status="ISSUED")
        db.add(b2)
        db.add(RegisteredUPI(flat_id=f2.id, upi_id=f"resident.t01.{fl:02d}02@okaxis", is_verified=True))

        # Unit 3: 7475.00
        f_num3 = f"T01-{fl:02d}03"
        amt3 = Decimal("7475.00")
        f3 = flats[f_num3]
        b3 = Bill(flat_id=f3.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                  issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                  area_sqft=Decimal("1150.00"), rate_per_sqft=Decimal("6.50"), principal_amount=amt3,
                  total_amount=amt3, paid_amount=Decimal("0.00"), balance_amount=amt3, status="ISSUED")
        db.add(b3)
        db.add(RegisteredUPI(flat_id=f3.id, upi_id=f"resident.t01.{fl:02d}03@icici", is_verified=True))

        # Unit 4: 6370.00
        f_num4 = f"T01-{fl:02d}04"
        amt4 = Decimal("6370.00")
        f4 = flats[f_num4]
        b4 = Bill(flat_id=f4.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                  issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                  area_sqft=Decimal("980.00"), rate_per_sqft=Decimal("6.50"), principal_amount=amt4,
                  total_amount=amt4, paid_amount=Decimal("0.00"), balance_amount=amt4, status="ISSUED")
        db.add(b4)
        db.add(RegisteredUPI(flat_id=f4.id, upi_id=f"resident.t01.{fl:02d}04@paytm", is_verified=True))

    # Provision Tower 2 (UPI only and Flat ref only)
    for fl in range(1, 16):
        if fl <= 10:
            f2_1 = flats[f"T02-{fl:02d}01"]
            b2_1 = Bill(flat_id=f2_1.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                        issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                        area_sqft=Decimal("1640.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("10660.00"),
                        total_amount=Decimal("10660.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("10660.00"), status="ISSUED")
            db.add(b2_1)
            db.add(RegisteredUPI(flat_id=f2_1.id, upi_id=f"user.t02.{fl:02d}01@okhdfcbank", is_verified=True))

            f2_2 = flats[f"T02-{fl:02d}02"]
            b2_2 = Bill(flat_id=f2_2.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                        issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                        area_sqft=Decimal("1420.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("9230.00"),
                        total_amount=Decimal("9230.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("9230.00"), status="ISSUED")
            db.add(b2_2)
            db.add(RegisteredUPI(flat_id=f2_2.id, upi_id=f"user.t02.{fl:02d}02@okaxis", is_verified=True))

            f2_3 = flats[f"T02-{fl:02d}03"]
            b2_3 = Bill(flat_id=f2_3.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                        issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                        area_sqft=Decimal("1150.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("7475.00"),
                        total_amount=Decimal("7475.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("7475.00"), status="ISSUED")
            db.add(b2_3)
            db.add(RegisteredUPI(flat_id=f2_3.id, upi_id=f"user.t02.{fl:02d}03@icici", is_verified=True))

        # Flat-ref-only on unit 4
        f2_4 = flats[f"T02-{fl:02d}04"]
        b2_4 = Bill(flat_id=f2_4.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                    issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("980.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("6370.00"),
                    total_amount=Decimal("6370.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("6370.00"), status="ISSUED")
        db.add(b2_4)

        # Tower 3 unit 3 flat-ref-only
        f3_3 = flats[f"T03-{fl:02d}03"]
        b3_3 = Bill(flat_id=f3_3.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                    issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("1150.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("7475.00"),
                    total_amount=Decimal("7475.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("7475.00"), status="ISSUED")
        db.add(b3_3)

    # Reused UPI (Tower 4: T04-0101 and T04-0102 share shared.family@okhdfcbank)
    f4_1 = flats["T04-0101"]
    f4_2 = flats["T04-0102"]
    db.add(RegisteredUPI(flat_id=f4_1.id, upi_id="shared.family@okhdfcbank", is_verified=True))
    db.add(RegisteredUPI(flat_id=f4_2.id, upi_id="shared.family@okhdfcbank", is_verified=True))

    # Tower 5: Partial, overpayment, cheque, bounce flats
    for fl in range(1, 21):
        f5_1 = flats[f"T05-{fl:02d}01"]
        b5_1 = Bill(flat_id=f5_1.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                    issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("1640.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("10660.00"),
                    total_amount=Decimal("10660.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("10660.00"), status="ISSUED")
        db.add(b5_1)
        db.add(RegisteredUPI(flat_id=f5_1.id, upi_id=f"resident.t05.{fl:02d}01@okhdfcbank", is_verified=True))

        f5_2 = flats[f"T05-{fl:02d}02"]
        b5_2 = Bill(flat_id=f5_2.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                    issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("1420.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("9230.00"),
                    total_amount=Decimal("9230.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("9230.00"), status="ISSUED")
        db.add(b5_2)
        db.add(RegisteredUPI(flat_id=f5_2.id, upi_id=f"resident.t05.{fl:02d}02@okaxis", is_verified=True))

    # Tower 6: Ambiguity flats (each flat has TWO active open bills with identical balance)
    for fl in range(1, 21):
        f6 = flats[f"T06-{fl:02d}01"]
        b6_a = Bill(flat_id=f6.id, billing_rule_version="v1.0-demo", period_month=10, period_year=2026,
                    issue_date=datetime(2026, 10, 1, tzinfo=timezone.utc), due_date=datetime(2026, 10, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("1640.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("10660.00"),
                    total_amount=Decimal("10660.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("10660.00"), status="ISSUED")
        b6_b = Bill(flat_id=f6.id, billing_rule_version="v1.0-demo", period_month=11, period_year=2026,
                    issue_date=datetime(2026, 11, 1, tzinfo=timezone.utc), due_date=datetime(2026, 11, 15, tzinfo=timezone.utc),
                    area_sqft=Decimal("1640.00"), rate_per_sqft=Decimal("6.50"), principal_amount=Decimal("10660.00"),
                    total_amount=Decimal("10660.00"), paid_amount=Decimal("0.00"), balance_amount=Decimal("10660.00"), status="ISSUED")
        db.add(b6_a)
        db.add(b6_b)
        db.add(RegisteredUPI(flat_id=f6.id, upi_id=f"resident.t06.{fl:02d}01@okhdfcbank", is_verified=True))

    db.commit()


@pytest.fixture(autouse=True)
def prepare_test_environment():
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
    finally:
        db.close()
    yield


def test_preview_statement_validation():
    """Verify preview is strictly non-mutating and correctly parses DEMO_BANK_CSV_V1."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)

        # Baseline entity counts
        files_count_before = db.query(BankImportFile).count()
        rows_count_before = db.query(BankRow).count()
        payments_count_before = db.query(Payment).count()
        ledger_count_before = db.query(FlatLedgerEntry).count()

        # Load sample demo statement
        sample_csv = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-02 10:15:00,2026-11-02,UPI/TEST/T01-0101,CREDIT,10660.00,INR,UTRPREVIEW001,resident.t01.0101@okhdfcbank,T01-0101\n"
            "98765432100012,2026-11-02 11:00:00,2026-11-02,INVALID AMOUNT ROW,CREDIT,-500.00,INR,UTRPREVIEW002,,\n"
            "98765432100012,2026-11-02 12:00:00,2026-11-02,VENDOR DEBIT,DEBIT,2500.00,INR,UTRPREVIEW003,,\n"
        )

        res = preview_bank_statement(db, sample_csv, "test_preview.csv")

        # Summary structure assertions
        assert res["total_rows"] == 3
        assert res["accepted_rows"] == 2
        assert res["invalid_rows"] == 1
        assert res["duplicate_file"] is False
        assert res["total_credit"] == Decimal("10660.00")
        assert res["total_debit"] == Decimal("2500.00")
        assert len(res["rows"]) == 3

        # Row 1: Valid exact match
        r1 = res["rows"][0]
        assert r1["is_valid"] is True
        assert r1["candidate_decision"] == "AUTO_MATCH"
        assert r1["candidate_action"] == "APPROVE"

        # Row 2: Negative amount invalid
        r2 = res["rows"][1]
        assert r2["is_valid"] is False
        assert r2["candidate_decision"] == "INVALID"
        assert r2["candidate_action"] == "REJECT"

        # Row 3: Debit row accepted but review
        r3 = res["rows"][2]
        assert r3["is_valid"] is True
        assert r3["candidate_decision"] == "REVIEW"
        assert r3["candidate_action"] == "HOLD"

        # ZERO writes to database during preview
        assert db.query(BankImportFile).count() == files_count_before
        assert db.query(BankRow).count() == rows_count_before
        assert db.query(Payment).count() == payments_count_before
        assert db.query(FlatLedgerEntry).count() == ledger_count_before
    finally:
        db.close()


def test_corpus_processing_and_zero_false_automatic_postings():
    """
    Runs the 385-row deterministic corpus through the match engine.
    Asserts:
    1. Zero false automatic postings (no non-AUTO_MATCH row is ever auto-posted).
    2. Every held row has a non-empty reason.
    3. Prints auto-match coverage percentage as a standalone metric.
    """
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        corpus_rows = generate_corpus(seed=42)
        assert len(corpus_rows) >= 300, f"Expected >= 300 rows, got {len(corpus_rows)}"

        csv_buf = io.StringIO()
        fieldnames = [
            "account_no", "txn_date", "value_date", "narration", "direction",
            "amount", "currency", "utr", "payer_upi", "flat_ref"
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in corpus_rows:
            writer.writerow({k: r[k] for k in fieldnames})
        csv_content = csv_buf.getvalue()

        # Commit statement
        result = commit_bank_statement(
            db=db,
            content=csv_content,
            filename="corpus_bank_statement_385.csv",
            uploaded_by_user_id=admin.id
        )

        assert result["status"] == "COMMITTED"
        assert result["total_rows"] == len(corpus_rows)

        committed_rows = db.query(BankRow).filter(
            BankRow.import_file_id == result["import_file_id"]
        ).order_by(BankRow.original_row_number.asc()).all()
        assert len(committed_rows) == len(corpus_rows)

        # Build lookup of corpus expectations
        auto_matched_count = 0
        held_count = 0
        total_rows_evaluated = len(corpus_rows)

        for b_row, expected in zip(committed_rows, corpus_rows):
            exp_decision = expected["expected_decision"]
            actual_decision = b_row.decision

            # ASSERTION A: ZERO FALSE AUTOMATIC POSTINGS & EXACT POSTINGS
            if actual_decision == "AUTO_MATCH" or b_row.review_status == "AUTO_POSTED":
                assert exp_decision == "AUTO_MATCH", (
                    f"CRITICAL SAFETY VIOLATION: Row #{b_row.original_row_number} (category: {expected.get('category')}) "
                    f"was AUTO_MATCHED but expected {exp_decision}!"
                )
                auto_matched_count += 1
                # Must have linked bill, payment, and flat
                assert b_row.matched_flat_id is not None
                assert b_row.matched_bill_id is not None
                assert b_row.matched_payment_id is not None

                # Every AUTO row creates exactly 1 payment and 1 ledger entry
                payment_count = db.query(Payment).filter(Payment.id == b_row.matched_payment_id).count()
                assert payment_count == 1, f"Row #{b_row.original_row_number} expected 1 payment, got {payment_count}"
                ledger_count = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.reference_id == b_row.matched_payment_id).count()
                assert ledger_count == 1, f"Row #{b_row.original_row_number} expected 1 ledger entry, got {ledger_count}"

            # ASSERTION B: EVERY NON-AUTO ROW HAS ZERO POSTINGS & NON-EMPTY REASON
            if actual_decision in ["REVIEW", "DUPLICATE_NO_OP", "INVALID"]:
                held_count += 1
                assert b_row.matched_payment_id is None, f"Non-auto row #{b_row.original_row_number} has matched_payment_id!"
                assert b_row.review_status != "AUTO_POSTED"
                assert b_row.decision_reason is not None and len(b_row.decision_reason.strip()) > 0, (
                    f"Held row #{b_row.original_row_number} has an empty reason!"
                )

        # Coverage Calculation & Reporting
        coverage_pct = round_currency((Decimal(auto_matched_count) / Decimal(total_rows_evaluated)) * Decimal("100.00"))
        print("\n=======================================================")
        print(f"AUTO-MATCH COVERAGE: {coverage_pct:.2f}%")
        print(f"Auto-matched rows: {auto_matched_count} / {total_rows_evaluated}")
        print(f"Held for review rows: {held_count} / {total_rows_evaluated}")
        print("Zero false automatic postings verified: PASS")
        print("=======================================================\n")

        assert auto_matched_count == 60, f"Expected exactly 60 auto-matches, got {auto_matched_count}"
        assert coverage_pct == Decimal("15.58"), f"Expected coverage 15.58%, got {coverage_pct}%"
    finally:
        db.close()


def test_replay_idempotency():
    """Verify that committing the exact same bank file twice is a no-op that creates zero new ledger entries."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # Short test CSV
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-03 10:00:00,2026-11-03,UPI/IDEM/T01-0101,CREDIT,10660.00,INR,UTRIDEM001,resident.t01.0101@okhdfcbank,T01-0101\n"
        )

        res1 = commit_bank_statement(db, csv_payload, "idempotent_test.csv", admin.id)
        assert res1["status"] in ["COMMITTED", "ALREADY_PROCESSED"]

        # Snapshot DB counts
        ledger_count_1 = db.query(FlatLedgerEntry).count()
        payments_count_1 = db.query(Payment).count()
        bank_rows_count_1 = db.query(BankRow).count()
        files_count_1 = db.query(BankImportFile).count()

        # Replay the identical file payload
        res2 = commit_bank_statement(db, csv_payload, "idempotent_test.csv", admin.id)
        assert res2["status"] == "ALREADY_PROCESSED"

        # Database state MUST remain strictly unchanged
        assert db.query(FlatLedgerEntry).count() == ledger_count_1
        assert db.query(Payment).count() == payments_count_1
        assert db.query(BankRow).count() == bank_rows_count_1
        assert db.query(BankImportFile).count() == files_count_1
    finally:
        db.close()


def test_concurrent_approval_safety():
    """
    Verify that concurrent approval attempts on the same bank row execute safely
    and post exactly ONE payment and ONE ledger entry.
    """
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # Insert a row held for review (partial payment)
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-04 10:00:00,2026-11-04,UPI/PARTIAL/T05-0101,CREDIT,4000.00,INR,UTRCONCURR001,resident.t05.0101@okhdfcbank,T05-0101\n"
        )
        res = commit_bank_statement(db, csv_payload, "concurrency_test.csv", admin.id)
        file_id = res["import_file_id"]

        row = db.query(BankRow).filter(BankRow.import_file_id == file_id).first()
        assert row is not None
        assert row.decision == "REVIEW"
        assert row.review_status == "PENDING"
        row_id = row.id

        initial_ledger_count = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.flat_id == row.matched_flat_id).count()
        initial_payments_count = db.query(Payment).filter(Payment.flat_id == row.matched_flat_id).count()

        # Concurrent execution of APPROVE
        def run_approval(idx: int):
            import time
            for attempt in range(5):
                worker_db = SessionLocal()
                try:
                    handle_review_action(
                        db=worker_db,
                        bank_row_id=row_id,
                        action="APPROVE",
                        reviewer_user_id=admin.id,
                        reason=f"Approved by worker {idx}"
                    )
                    return True
                except Exception as e:
                    if "locked" in str(e).lower() and attempt < 4:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    return str(e)
                finally:
                    worker_db.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_approval, i) for i in range(5)]
            results = [f.result() for f in futures]

        db.refresh(row)
        assert row.review_status == "APPROVED"

        final_ledger_count = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.flat_id == row.matched_flat_id).count()
        final_payments_count = db.query(Payment).filter(Payment.flat_id == row.matched_flat_id).count()

        # Exactly ONE payment and ONE ledger entry created across all 5 threads
        assert final_payments_count == initial_payments_count + 1
        assert final_ledger_count == initial_ledger_count + 1
    finally:
        db.close()


def test_ledger_reconciliation():
    """Verify that ledger credits created by bank matching reconcile with the exact sum of approved amounts."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # Two exact match rows
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-05 10:00:00,2026-11-05,UPI/RECON/T01-0201,CREDIT,10660.00,INR,UTRRECON001,resident.t01.0201@okhdfcbank,T01-0201\n"
            "98765432100012,2026-11-05 11:00:00,2026-11-05,UPI/RECON/T01-0202,CREDIT,9230.00,INR,UTRRECON002,resident.t01.0202@okaxis,T01-0202\n"
        )
        res = commit_bank_statement(db, csv_payload, "recon_test.csv", admin.id)
        file_id = res["import_file_id"]

        rows = db.query(BankRow).filter(BankRow.import_file_id == file_id).all()
        expected_total = sum(r.amount for r in rows)
        assert expected_total == Decimal("19890.00")

        # Sum ledger entries linked to these payments
        payment_ids = [r.matched_payment_id for r in rows if r.matched_payment_id]
        assert len(payment_ids) == 2

        ledger_entries = db.query(FlatLedgerEntry).filter(
            FlatLedgerEntry.reference_id.in_(payment_ids),
            FlatLedgerEntry.entry_type == "CREDIT"
        ).all()

        ledger_total = sum(e.amount for e in ledger_entries)
        assert ledger_total == expected_total
        assert round_currency(ledger_total) == round_currency(expected_total)
    finally:
        db.close()


def test_review_action_handlers_full_lifecycle():
    """Verify HOLD, REJECT, CORRECT_MAPPING, and APPROVE review handlers."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-06 10:00:00,2026-11-06,UPI/LIFECYCLE/UNKNOWN,CREDIT,6370.00,INR,UTRLIFECYCLE01,unknown.donor@bank,\n"
        )
        res = commit_bank_statement(db, csv_payload, "lifecycle_test.csv", admin.id)
        row = db.query(BankRow).filter(BankRow.import_file_id == res["import_file_id"]).first()
        assert row is not None
        assert row.decision == "REVIEW"

        # 1. HOLD
        row = handle_review_action(db, row.id, "HOLD", admin.id, reason="Awaiting bank slip")
        assert row.review_status == "HELD"
        assert row.correction_reason == "Awaiting bank slip"

        # 2. CORRECT_MAPPING (map to T01-0104 which has an open bill of 6370.00)
        target_flat = db.query(Flat).filter(Flat.flat_number == "T01-0104").first()
        assert target_flat is not None
        target_bill = db.query(Bill).filter(
            Bill.flat_id == target_flat.id,
            Bill.balance_amount == Decimal("6370.00")
        ).first()

        row = handle_review_action(
            db, row.id, "CORRECT_MAPPING", admin.id,
            target_flat_id=target_flat.id,
            target_bill_id=target_bill.id if target_bill else None,
            reason="Donor confirmed flat is T01-0104"
        )
        assert row.review_status == "CORRECTED"
        assert row.matched_flat_id == target_flat.id

        # 3. APPROVE corrected row
        row = handle_review_action(db, row.id, "APPROVE", admin.id, reason="Correction verified, posting payment")
        assert row.review_status == "APPROVED"
        assert row.matched_payment_id is not None

        # Verify bill is paid
        if target_bill:
            db.refresh(target_bill)
            assert target_bill.status == "PAID"
            assert target_bill.balance_amount == Decimal("0.00")
    finally:
        db.close()


def test_settle_existing_checkout_without_duplicate_payment():
    """Verify that when a statement line settles an existing test checkout, it links without creating a duplicate payment."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # Find flat T01-0103 and its bill
        flat = db.query(Flat).filter(Flat.flat_number == "T01-0103").first()
        assert flat is not None
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None

        # Create an existing PENDING checkout payment
        pending_payment = Payment(
            flat_id=flat.id,
            bill_id=bill.id,
            amount=bill.balance_amount,
            currency="INR",
            payment_method="UPI_PENDING_CHECKOUT",
            status="PENDING",
            transaction_reference="TXN-CHECKOUT-PENDING-001",
            idempotency_key="IDEM-TEST-CHECKOUT-001",
            paid_at=datetime.now(timezone.utc),
            payer_user_id=admin.id
        )
        db.add(pending_payment)
        db.commit()

        initial_payments_count = db.query(Payment).filter(Payment.flat_id == flat.id).count()

        # Submit bank statement matching this bill and reference
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            f"98765432100012,2026-11-07 10:00:00,2026-11-07,UPI/SETTLE CHECKOUT/{flat.flat_number},CREDIT,{bill.balance_amount},INR,TXN-CHECKOUT-PENDING-001,resident.t01.0103@icici,{flat.flat_number}\n"
        )
        res = commit_bank_statement(db, csv_payload, "settle_checkout_test.csv", admin.id)
        assert res["status"] == "COMMITTED"

        row = db.query(BankRow).filter(BankRow.import_file_id == res["import_file_id"]).first()
        assert row is not None
        assert row.decision == "AUTO_MATCH"
        assert row.review_status == "AUTO_POSTED"
        assert row.matched_payment_id == pending_payment.id

        # Verify no duplicate payment was created
        final_payments_count = db.query(Payment).filter(Payment.flat_id == flat.id).count()
        assert final_payments_count == initial_payments_count

        db.refresh(pending_payment)
        assert pending_payment.status == "SUCCESS"
        assert pending_payment.payment_method == "BANK_MATCHED"
    finally:
        db.close()


def test_upi_only_rows_never_auto_post():
    """Verify that rows with registered UPI but missing flat_ref never auto-post, even when amount matches open bill."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # T01-0101 has open balance 10660.00 and registered UPI resident.t01.0101@okhdfcbank
        # Provide valid registered UPI, but empty flat_ref
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-08 10:00:00,2026-11-08,UPI/PAYMENT FROM RESIDENT,CREDIT,10660.00,INR,UTRUPIONLY001,resident.t01.0101@okhdfcbank,\n"
        )
        res = commit_bank_statement(db, csv_payload, "test_upi_only.csv", admin.id)
        row = db.query(BankRow).filter(BankRow.import_file_id == res["import_file_id"]).first()
        assert row is not None

        # Assert row goes to REVIEW with reason UPI_ONLY_REVIEW
        assert row.decision == "REVIEW"
        assert row.decision_reason == "UPI_ONLY_REVIEW"
        assert row.review_status == "PENDING"
        assert row.matched_payment_id is None

        # Suggested flat is populated for accounts staff review
        flat = db.query(Flat).filter(Flat.flat_number == "T01-0101").first()
        assert row.matched_flat_id == flat.id

        # ZERO payments and ZERO ledger entries created
        payments = db.query(Payment).filter(Payment.transaction_reference == "UTRUPIONLY001").all()
        assert len(payments) == 0

        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill.balance_amount == Decimal("10660.00")
        assert bill.status == "ISSUED"
    finally:
        db.close()


def test_flat_ref_only_rows_never_auto_post():
    """Verify that rows with flat_ref (or flat parsed from narration) but missing/unregistered UPI never auto-post."""
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # Test both explicit flat_ref and narration-parsed flat
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-08 11:00:00,2026-11-08,NEFT/DUES/T01-0102,CREDIT,9230.00,INR,UTRFLATREF001,,T01-0102\n"
            "98765432100012,2026-11-08 12:00:00,2026-11-08,IMPS FROM BANK FOR T01-0103 MAINTENANCE,CREDIT,7475.00,INR,UTRNARRREF002,,\n"
        )
        res = commit_bank_statement(db, csv_payload, "test_flat_ref_only.csv", admin.id)
        rows = db.query(BankRow).filter(BankRow.import_file_id == res["import_file_id"]).order_by(BankRow.original_row_number.asc()).all()
        assert len(rows) == 2

        # Row 1: Explicit flat_ref only
        r1 = rows[0]
        assert r1.decision == "REVIEW"
        assert r1.decision_reason == "FLAT_REF_ONLY_REVIEW"
        assert r1.review_status == "PENDING"
        assert r1.matched_payment_id is None

        # Row 2: Narration parsed flat only
        r2 = rows[1]
        assert r2.decision == "REVIEW"
        assert r2.decision_reason == "FLAT_REF_ONLY_REVIEW"
        assert r2.review_status == "PENDING"
        assert r2.matched_payment_id is None

        # ZERO payments created for either row
        assert db.query(Payment).filter(Payment.transaction_reference.in_(["UTRFLATREF001", "UTRNARRREF002"])).count() == 0
    finally:
        db.close()


def test_partial_payment_approval_path_and_overpayment_held():
    """
    Verify accounts approval path for partial payment and overpayment:
    - Partial payment approval posts once, bill becomes PARTIALLY_PAID, ledger credit equals paid amount.
    - Overpayment approval is rejected and remains HELD.
    """
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # T05-0101 has open balance 10660.00
        # Row 1: Partial payment of 4000.00
        # Row 2: Overpayment of 15000.00 (against T05-0102 with balance 9230.00)
        csv_payload = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-08 14:00:00,2026-11-08,UPI/PARTIAL/T05-0101,CREDIT,4000.00,INR,UTRPARTIAL001,resident.t05.0101@okhdfcbank,T05-0101\n"
            "98765432100012,2026-11-08 15:00:00,2026-11-08,UPI/OVERPAY/T05-0102,CREDIT,15000.00,INR,UTROVERPAY002,resident.t05.0102@okaxis,T05-0102\n"
        )
        res = commit_bank_statement(db, csv_payload, "test_partial_overpay.csv", admin.id)
        rows = db.query(BankRow).filter(BankRow.import_file_id == res["import_file_id"]).order_by(BankRow.original_row_number.asc()).all()
        assert len(rows) == 2

        partial_row, overpay_row = rows[0], rows[1]
        assert partial_row.decision == "REVIEW"
        assert partial_row.decision_reason == "PARTIAL_PAYMENT_REQUIRES_REVIEW"
        assert overpay_row.decision == "REVIEW"
        assert overpay_row.decision_reason == "OVERPAYMENT_EXCEEDS_BALANCE"

        # 1. Approve Partial Payment
        flat_partial = db.query(Flat).filter(Flat.flat_number == "T05-0101").first()
        bill_partial = db.query(Bill).filter(Bill.flat_id == flat_partial.id).first()
        assert bill_partial.balance_amount == Decimal("10660.00")

        approved_row = handle_review_action(
            db=db,
            bank_row_id=partial_row.id,
            action="APPROVE",
            reviewer_user_id=admin.id,
            reason="Approved partial payment"
        )
        assert approved_row.review_status == "APPROVED"
        assert approved_row.matched_payment_id is not None

        db.refresh(bill_partial)
        assert bill_partial.paid_amount == Decimal("4000.00")
        assert bill_partial.balance_amount == Decimal("6660.00")
        assert bill_partial.status == "PARTIALLY_PAID"

        ledger_entry = db.query(FlatLedgerEntry).filter(
            FlatLedgerEntry.reference_id == approved_row.matched_payment_id
        ).first()
        assert ledger_entry is not None
        assert ledger_entry.entry_type == "CREDIT"
        assert ledger_entry.amount == Decimal("4000.00")

        # Concurrency safety: Approving again is safe and posts no duplicate
        handle_review_action(
            db=db,
            bank_row_id=partial_row.id,
            action="APPROVE",
            reviewer_user_id=admin.id
        )
        assert db.query(Payment).filter(Payment.transaction_reference == "UTRPARTIAL001").count() == 1
        assert db.query(FlatLedgerEntry).filter(FlatLedgerEntry.reference_id == approved_row.matched_payment_id).count() == 1

        # 2. Attempt Overpayment Approval -> Must fail and remain HELD
        flat_overpay = db.query(Flat).filter(Flat.flat_number == "T05-0102").first()
        bill_overpay = db.query(Bill).filter(Bill.flat_id == flat_overpay.id).first()
        assert bill_overpay.balance_amount == Decimal("9230.00")

        with pytest.raises(ValueError, match="exceeds"):
            handle_review_action(
                db=db,
                bank_row_id=overpay_row.id,
                action="APPROVE",
                reviewer_user_id=admin.id,
                reason="Attempting to approve excess payment"
            )

        db.refresh(overpay_row)
        assert overpay_row.review_status == "HELD"
        assert overpay_row.matched_payment_id is None

        # Bill remains untouched
        db.refresh(bill_overpay)
        assert bill_overpay.paid_amount == Decimal("0.00")
        assert bill_overpay.balance_amount == Decimal("9230.00")
        assert bill_overpay.status == "ISSUED"

        # Zero payments and zero ledger entries created for overpayment
        assert db.query(Payment).filter(Payment.transaction_reference == "UTROVERPAY002").count() == 0
    finally:
        db.close()


def test_concurrent_import_and_approval_duplicate_prevention():
    """
    Concurrency test verifying database-level duplicate protection:
    - Two threads concurrently import the same statement file -> exactly 1 BankPosting and 1 ledger entry.
    - Two threads concurrently approve the same held bank row -> exactly 1 BankPosting and 1 ledger entry.
    """
    import time
    db = SessionLocal()
    try:
        provision_corpus_environment(db)
        admin = db.query(User).filter(User.phone == "9876543200").first()
        assert admin is not None

        # 1. Concurrent import of the exact same statement file
        import_csv = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-08 16:00:00,2026-11-08,UPI/CONCUR/T01-0101,CREDIT,10660.00,INR,UTRCONCURRIMP01,resident.t01.0101@okhdfcbank,T01-0101\n"
        )

        def worker_import(idx: int):
            for attempt in range(5):
                worker_db = SessionLocal()
                try:
                    res = commit_bank_statement(
                        db=worker_db,
                        content=import_csv,
                        filename="concurrent_import.csv",
                        uploaded_by_user_id=admin.id
                    )
                    return res["status"]
                except Exception as e:
                    if "locked" in str(e).lower() and attempt < 4:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    return str(e)
                finally:
                    worker_db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(worker_import, 1)
            f2 = executor.submit(worker_import, 2)
            res1 = f1.result()
            res2 = f2.result()

        # Database state: exactly ONE posting, ONE payment, and ONE ledger entry
        postings = db.query(BankPosting).filter(BankPosting.utr == "UTRCONCURRIMP01").all()
        assert len(postings) == 1, f"Expected 1 BankPosting, got {len(postings)}"

        payments = db.query(Payment).filter(Payment.transaction_reference == "UTRCONCURRIMP01").all()
        assert len(payments) == 1, f"Expected 1 Payment, got {len(payments)}"

        ledgers = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.reference_id == payments[0].id).all()
        assert len(ledgers) == 1, f"Expected 1 FlatLedgerEntry, got {len(ledgers)}"

        # 2. Concurrent approval of the same held bank row
        held_csv = (
            "account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
            "98765432100012,2026-11-08 17:00:00,2026-11-08,UPI/CONCUR_APPR/T01-0102,CREDIT,9230.00,INR,UTRCONCURRAPPR01,resident.t01.0102@okaxis,T01-0102\n"
        )
        res_held = commit_bank_statement(db, held_csv, "held_concur.csv", admin.id)
        held_row = db.query(BankRow).filter(BankRow.import_file_id == res_held["import_file_id"]).first()
        assert held_row is not None
        held_row_id = held_row.id

        def worker_approve(idx: int):
            for attempt in range(5):
                worker_db = SessionLocal()
                try:
                    handle_review_action(
                        db=worker_db,
                        bank_row_id=held_row_id,
                        action="APPROVE",
                        reviewer_user_id=admin.id,
                        reason=f"Approved by concurrent worker {idx}"
                    )
                    return True
                except Exception as e:
                    if "locked" in str(e).lower() and attempt < 4:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    return str(e)
                finally:
                    worker_db.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            fa1 = executor.submit(worker_approve, 1)
            fa2 = executor.submit(worker_approve, 2)
            ra1 = fa1.result()
            ra2 = fa2.result()

        # Database state: exactly ONE posting, ONE payment, and ONE ledger entry
        postings_appr = db.query(BankPosting).filter(BankPosting.utr == "UTRCONCURRAPPR01").all()
        assert len(postings_appr) == 1, f"Expected 1 BankPosting, got {len(postings_appr)}"

        payments_appr = db.query(Payment).filter(Payment.transaction_reference == "UTRCONCURRAPPR01").all()
        assert len(payments_appr) == 1, f"Expected 1 Payment, got {len(payments_appr)}"

        ledgers_appr = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.reference_id == payments_appr[0].id).all()
        assert len(ledgers_appr) == 1, f"Expected 1 FlatLedgerEntry, got {len(ledgers_appr)}"
    finally:
        db.close()


def test_alembic_bank_postings_upgrade_and_downgrade():
    """Verify clean upgrade and downgrade cycle for the bank_postings migration."""
    import subprocess
    import sys

    # Downgrade 1 step
    res_down = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "-1"],
        capture_output=True, text=True
    )
    assert res_down.returncode == 0, f"Alembic downgrade failed: {res_down.stderr}"

    # Upgrade back to head
    res_up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True
    )
    assert res_up.returncode == 0, f"Alembic upgrade failed: {res_up.stderr}"


