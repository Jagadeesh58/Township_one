from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Flat, Bill, FlatLedgerEntry
from backend.app.services.billing import (
    calculate_principal, calculate_demo_late_fee, generate_flat_bill
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


def test_billing_summary_endpoint():
    # Login as Swati (T12-0408)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    token = login["access_token"]
    flat_id = login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["flat_number"] == "T12-0408"
    assert data["area_sqft"] == 980.0
    assert data["current_due"] == 6370.0
    assert "pending society federation approval" in data["late_fee_notice"]
    assert len(data["recent_ledger"]) > 0


def test_billing_cross_flat_idor_denied():
    # Login as Neeraj (T07-1203)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    neeraj_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"}).json()
    token = neeraj_login["access_token"]

    # Login as Swati to get Swati's flat ID
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    swati_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    swati_flat_id = swati_login["user"]["flats"][0]["flat_id"]

    # Neeraj attempts to view Swati's billing summary
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary", headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["error"]["message"]


def test_duplicate_bill_generation_rejected():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        # Bill for 11/2026 already seeded for T07-1203
        with pytest.raises(Exception) as exc_info:
            generate_flat_bill(db, flat.id, period_month=11, period_year=2026)
        assert "already exists" in str(exc_info.value)
    finally:
        db.close()
