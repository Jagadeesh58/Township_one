"""
Day 1 · D1-S4 — Maintenance billing and ledger
Test suite verifying:
- Precise area-based principal calculations
- Grace period boundaries (due on 15th, grace ends 20th, interest starts 21st)
- Multi-bill outstanding balance aggregation (unpaid_bills and total_outstanding_due)
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
    # 6370 * 0.18 * (47 / 365) = 147.67
    fee = calculate_demo_late_fee(Decimal("6370.00"), 47, Decimal("18.00"))
    assert fee > Decimal("140.00") and fee < Decimal("150.00")


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

    # 1. Check on Nov 18 (3 days past due, but within 5-day grace period)
    as_of_nov18 = datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc)
    overdue_days, fee = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov18)
    assert overdue_days == 0
    assert fee == Decimal("0.00")

    # 2. Check on Nov 20 (exact grace cutoff)
    as_of_nov20 = datetime(2026, 11, 20, 0, 0, tzinfo=timezone.utc)
    overdue_days, fee = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov20)
    assert overdue_days == 0
    assert fee == Decimal("0.00")

    # 3. Check on Nov 22 (past grace period -> interest calculated from Nov 15)
    as_of_nov22 = datetime(2026, 11, 22, 0, 0, tzinfo=timezone.utc)
    overdue_days, fee = evaluate_bill_overdue_and_interest(bill, rule, as_of=as_of_nov22)
    assert overdue_days == 7  # 7 days from due date Nov 15
    assert fee > Decimal("0.00")


def test_billing_summary_aggregates_multiple_unpaid_bills():
    # Login as Swati (T12-0408)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    token = login["access_token"]
    flat_id = login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    
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
    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["flat_number"] == "T12-0408"
    assert data["total_outstanding_due"] == 12740.0
    assert len(data["unpaid_bills"]) == 2


def test_billing_cross_flat_idor_denied():
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    neeraj_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"}).json()
    token = neeraj_login["access_token"]

    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    swati_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    swati_flat_id = swati_login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary", headers=headers)
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
