"""
Township One - Full Integration Verification Test Suite.

End-to-end integration test suite verifying the complete resident journey:
- Resident OTP authentication and profile retrieval
- Billing summary retrieval with area/rate calculations and overdue tracking
- Simulated payment checkout (FAILED outcome preserves dues, SUCCESS outcome reduces dues and creates receipt)
- Dual-entry flat ledger reconciliation
- Prevention of duplicate payments on already-paid bills
- Seed data verification across sample flats:
    * Neeraj Kulkarni (T07-1203, 1150 sq ft, fully paid)
    * Aamir Shaikh (T21-1601, 1640 sq ft, partially paid)
    * Swati Joshi (T12-0408, 980 sq ft, tenant)
- Committee aggregate reports allowed, individual flat drilldown strictly forbidden (403)
- Family member role permissions (read permitted, pay denied)
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import OTPChallenge

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_otp_challenges():
    db = SessionLocal()
    try:
        db.query(OTPChallenge).delete()
        db.commit()
    finally:
        db.close()


def test_full_resident_billing_and_payment_journey():
    # -------------------------------------------------------------
    # Step 1: Resident OTP Login (Swati Joshi, Tenant in T12-0408)
    # -------------------------------------------------------------
    otp_req = client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    assert otp_req.status_code == 200

    login_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"})
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" not in login_data
    user = login_data["user"]
    assert user["name"] == "Swati Joshi"
    assert len(user["flats"]) == 1
    flat_id = user["flats"][0]["flat_id"]
    assert user["flats"][0]["flat_number"] == "T12-0408"
    assert user["flats"][0]["member_type"] == "TENANT"

    csrf_token = login_resp.cookies.get("township_csrf", "")
    client.headers["X-CSRF-Token"] = csrf_token
    headers = {"X-CSRF-Token": csrf_token}

    # -------------------------------------------------------------
    # Step 2: View Outstanding Bill Summary
    # -------------------------------------------------------------
    summary_resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["flat_number"] == "T12-0408"
    assert float(summary["area_sqft"]) == 980.0
    assert float(summary["current_due"]) == 6370.0  # 980 * 6.50
    assert summary["overdue_days"] >= 40
    bill_id = summary["latest_bill"]["id"]

    # -------------------------------------------------------------
    # Step 3: Test Payment - FAILED state preserves dues
    # -------------------------------------------------------------
    failed_pay = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 6370.0,
            "test_outcome": "FAILED",
            "idempotency_key": "IDEM-E2E-FAILED-001"
        }
    )
    assert failed_pay.status_code == 200
    assert failed_pay.json()["status"] == "FAILED"
    assert failed_pay.json()["receipt"] is None

    # Check dues still intact
    summary_check1 = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert float(summary_check1["current_due"]) == 6370.0

    # -------------------------------------------------------------
    # Step 4: Test Payment - SUCCESS state reduces dues & issues receipt
    # -------------------------------------------------------------
    success_pay = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 6370.0,
            "payment_method": "UPI_SIMULATED",
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-E2E-SWATI-001"
        }
    )
    assert success_pay.status_code == 200
    pay_data = success_pay.json()
    assert pay_data["status"] == "SUCCESS"
    assert float(pay_data["amount"]) == 6370.0
    assert pay_data["receipt"] is not None
    receipt_no = pay_data["receipt"]["receipt_number"]
    assert receipt_no.startswith("REC-")
    assert pay_data["receipt"]["flat_number"] == "T12-0408"
    assert pay_data["receipt"]["resident_name"] == "Swati Joshi"

    # Dues must now be exactly 0
    summary_check2 = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert float(summary_check2["current_due"]) == 0.0

    # -------------------------------------------------------------
    # Step 5: Check Running Flat Ledger Reconciliation
    # -------------------------------------------------------------
    ledger_resp = client.get(f"/api/v1/billing/flats/{flat_id}/ledger", headers=headers)
    assert ledger_resp.status_code == 200
    ledger_entries = ledger_resp.json()
    assert len(ledger_entries) >= 2
    latest_entry = ledger_entries[-1]
    assert latest_entry["entry_type"] == "CREDIT"
    assert float(latest_entry["amount"]) == 6370.0
    assert float(latest_entry["balance_after"]) == 0.0

    # -------------------------------------------------------------
    # Step 6: Paying already-paid bill is blocked
    # -------------------------------------------------------------
    duplicate_pay = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-E2E-DUP-BLOCKED"
        }
    )
    assert duplicate_pay.status_code == 400
    assert "already fully paid" in duplicate_pay.json()["error"]["message"]

    # -------------------------------------------------------------
    # Step 7: Verify Neeraj Kulkarni (T07-1203) - Already Paid
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    neeraj_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"}).json()
    neeraj_csrf = client.cookies.get("township_csrf", "")
    neeraj_headers = {"X-CSRF-Token": neeraj_csrf}
    neeraj_flat_id = neeraj_login["user"]["flats"][0]["flat_id"]

    neeraj_summary = client.get(f"/api/v1/billing/flats/{neeraj_flat_id}/summary", headers=neeraj_headers).json()
    assert neeraj_summary["flat_number"] == "T07-1203"
    assert float(neeraj_summary["area_sqft"]) == 1150.0
    assert float(neeraj_summary["current_due"]) == 0.0
    assert float(neeraj_summary["latest_bill"]["principal_amount"]) == 7475.0
    assert float(neeraj_summary["latest_bill"]["paid_amount"]) == 7475.0
    assert neeraj_summary["latest_bill"]["status"] == "PAID"

    # -------------------------------------------------------------
    # Step 8: Verify Aamir Shaikh (T21-1601) - Partially Paid
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543212"})
    aamir_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "123456"}).json()
    aamir_csrf = client.cookies.get("township_csrf", "")
    aamir_headers = {"X-CSRF-Token": aamir_csrf}
    aamir_flat_id = aamir_login["user"]["flats"][0]["flat_id"]

    aamir_summary = client.get(f"/api/v1/billing/flats/{aamir_flat_id}/summary", headers=aamir_headers).json()
    assert aamir_summary["flat_number"] == "T21-1601"
    assert float(aamir_summary["area_sqft"]) == 1640.0
    assert float(aamir_summary["latest_bill"]["principal_amount"]) == 10660.0
    assert float(aamir_summary["latest_bill"]["paid_amount"]) == 5000.0
    assert float(aamir_summary["current_due"]) == 5660.0
    assert aamir_summary["overdue_days"] >= 15
    assert aamir_summary["latest_bill"]["status"] == "PARTIALLY_PAID"

    # -------------------------------------------------------------
    # Step 9: Committee Role Strict Scoping Verification
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543250"})
    comm_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543250", "otp": "123456"}).json()
    comm_csrf = client.cookies.get("township_csrf", "")
    comm_headers = {"X-CSRF-Token": comm_csrf}

    comm_agg = client.get("/api/v1/billing/committee/aggregate", headers=comm_headers)
    assert comm_agg.status_code == 200
    agg_data = comm_agg.json()
    assert "total_billed_inr" in agg_data
    assert "total_collected_inr" in agg_data
    assert "collection_efficiency_pct" in agg_data

    comm_flat_drilldown = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=comm_headers)
    assert comm_flat_drilldown.status_code == 403

    # -------------------------------------------------------------
    # Step 10: Family Member Permission Scoping
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543213"})
    ananya_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543213", "otp": "123456"}).json()
    ananya_csrf = client.cookies.get("township_csrf", "")
    ananya_headers = {"X-CSRF-Token": ananya_csrf}
    ananya_flat_id = ananya_login["user"]["flats"][0]["flat_id"]

    ananya_summary = client.get(f"/api/v1/billing/flats/{ananya_flat_id}/summary", headers=ananya_headers)
    assert ananya_summary.status_code == 200

    ananya_pay = client.post(
        "/api/v1/payments/checkout",
        headers=ananya_headers,
        json={
            "flat_id": ananya_flat_id,
            "bill_id": neeraj_summary["latest_bill"]["id"],
            "amount": 100.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-E2E-FAMILY-BLOCK"
        }
    )
    assert ananya_pay.status_code == 403
    assert "does not permit bill payment" in ananya_pay.json()["error"]["message"].lower()
