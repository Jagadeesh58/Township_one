"""
Township One - Maintenance Billing and Ledger Verification Tests.

Test suite verifying:
- Precise area-based principal calculations
- Grace period boundaries (due on 15th, grace ends 20th, interest starts 21st)
- Multi-bill outstanding balance aggregation (unpaid_bills and total_outstanding_due)
- Leap year calculation support (366 vs 365 days)
- IDOR access denial across flats
- Duplicate bill prevention for the same period
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Flat, Bill, FlatLedgerEntry, BillingRule
from backend.app.services.billing import (
    calculate_principal, calculate_demo_late_fee, generate_flat_bill,
    evaluate_bill_overdue_and_interest
)

client = TestClient(app)


def test_principal_calculation_exact():
    assert calculate_principal(Decimal("1150.00")) == Decimal("7475.00")
    assert calculate_principal(Decimal("980.00")) == Decimal("6370.00")
    assert calculate_principal(Decimal("1640.00")) == Decimal("10660.00")


def test_demo_late_fee_boundaries():
    # 0 days overdue -> 0
    assert calculate_demo_late_fee(Decimal("6370.00"), 0) == Decimal("0.00")
    assert calculate_demo_late_fee(Decimal("6370.00"), -5) == Decimal("0.00")
    
    # 47 days overdue on 6370 @ 18% p.a.
    fee = calculate_demo_late_fee(Decimal("6370.00"), 47, Decimal("18.00"))
    assert fee > Decimal("140.00") and fee < Decimal("150.00")


def test_demo_late_fee_leap_year_handling():
    # Leap year (2024, 366 days): 366 days @ 10% on 1,000 = exactly 100.00
    fee_leap = calculate_demo_late_fee(Decimal("1000.00"), 366, Decimal("10.00"), year=2024)
    assert fee_leap == Decimal("100.00")

    # Non-leap year (2025, 365 days): 365 days @ 10% on 1,000 = exactly 100.00
    fee_non_leap = calculate_demo_late_fee(Decimal("1000.00"), 365, Decimal("10.00"), year=2025)
    assert fee_non_leap == Decimal("100.00")


def test_grace_period_enforcement():
    # Due date: Nov 15, Grace Period: 5 days -> Grace period active until Nov 20!
    rule = BillingRule(
        name="Test Rule",
        rate_per_sqft=Decimal("6.50"),
        due_day_of_month=15,
        grace_period_days=5,
        late_fee_percentage_pa=Decimal("18.00")
    )
    bill = Bill(
        principal_amount=Decimal("6370.00"),
        balance_amount=Decimal("6370.00"),
        due_date=datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc)
    )

    # 1. Check on Nov 18 (3 calendar days past due, but within 5-day grace period: 0 interest-eligible days, ₹0 fee)
    as_of_nov18 = datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc)
    res_nov18 = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov18)
    assert res_nov18.calendar_overdue_days == 3
    assert res_nov18.interest_eligible_days == 0
    assert res_nov18.late_fee == Decimal("0.00")

    # 2. Check on Nov 20 (exact grace cutoff: 5 calendar overdue days, 0 interest-eligible days, ₹0 fee)
    as_of_nov20 = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    res_nov20 = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov20)
    assert res_nov20.calendar_overdue_days == 5
    assert res_nov20.interest_eligible_days == 0
    assert res_nov20.late_fee == Decimal("0.00")

    # 3. Check on Nov 22 (past grace period -> interest calculated on 2 interest-eligible days)
    as_of_nov22 = datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)
    res_nov22 = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov22)
    assert res_nov22.calendar_overdue_days == 7
    assert res_nov22.interest_eligible_days == 2  # 7 - 5 = 2 days
    assert res_nov22.late_fee > Decimal("0.00")


def test_overdue_and_grace_period_specification_fixtures():
    """
    Validates exact prompt specification for grace-period and late fee separation:
    - Due date 2026-09-20, as-of 2026-11-06: 47 calendar overdue days, 42 interest-eligible days.
    - Due date 2026-10-19, as-of 2026-11-06: 18 calendar overdue days, 13 interest-eligible days.
    """
    rule = BillingRule(
        name="Standard Rule",
        rate_per_sqft=Decimal("6.50"),
        grace_period_days=5,
        late_fee_percentage_pa=Decimal("18.00")
    )
    as_of = datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc)

    # 1. T12-0408 (Sep 2026 bill, due 2026-09-20, balance ₹6,370)
    bill_sep = Bill(
        principal_amount=Decimal("6370.00"),
        balance_amount=Decimal("6370.00"),
        due_date=datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)
    )
    eval_sep = evaluate_bill_overdue_and_interest(bill_sep, rule, as_of=as_of)
    assert eval_sep.calendar_overdue_days == 47
    assert eval_sep.interest_eligible_days == 42
    assert eval_sep.late_fee == Decimal("131.94")

    # 2. T21-1601 (Oct 2026 bill, due 2026-10-19, balance ₹5,660)
    bill_oct = Bill(
        principal_amount=Decimal("10660.00"),
        balance_amount=Decimal("5660.00"),
        due_date=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
    )
    eval_oct = evaluate_bill_overdue_and_interest(bill_oct, rule, as_of=as_of)
    assert eval_oct.calendar_overdue_days == 18
    assert eval_oct.interest_eligible_days == 13
    assert eval_oct.late_fee == Decimal("36.29")


def test_billing_summary_aggregates_multiple_unpaid_bills():
    # Login as Swati (T12-0408)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    flat_id = login["user"]["flats"][0]["flat_id"]
    
    # Generate a second bill for a previous month (August 2026) for Swati's flat
    db = SessionLocal()
    try:
        bill_aug = Bill(
            flat_id=flat_id,
            billing_rule_version="v1.0-demo",
            period_month=8,
            period_year=2026,
            issue_date=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc),
            area_sqft=Decimal("980.00"),
            rate_per_sqft=Decimal("6.50"),
            principal_amount=Decimal("6370.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("6370.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("6370.00"),
            status="OVERDUE"
        )
        db.add(bill_aug)
        db.commit()
    finally:
        db.close()

    # Now verify summary aggregates BOTH bills: 6370 (Sept) + 6370 (Aug) = 12740.0
    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flat_number"] == "T12-0408"
    assert float(data["total_outstanding_due"]) == 12740.0
    assert len(data["unpaid_bills"]) == 2


def test_billing_cross_flat_idor_denied():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"})

    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    swati_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    swati_flat_id = swati_login["user"]["flats"][0]["flat_id"]

    resp = client.get(
        f"/api/v1/billing/flats/{swati_flat_id}/summary",
        cookies={"township_session": neeraj_token}
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["error"]["message"]


def test_duplicate_bill_generation_rejected():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        with pytest.raises(Exception) as exc_info:
            generate_flat_bill(db, flat.id, period_month=11, period_year=2026)
        assert "already exists" in str(exc_info.value)
    finally:
        db.close()
