from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_full_day1_resident_billing_and_payment_journey():
    # -------------------------------------------------------------
    # Step 1: Resident OTP Login (Swati Joshi, Tenant in T12-0408)
    # -------------------------------------------------------------
    otp_req = client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    assert otp_req.status_code == 200

    login_resp = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"})
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    token = login_data["access_token"]
    user = login_data["user"]
    assert user["name"] == "Swati Joshi"
    assert len(user["flats"]) == 1
    flat_id = user["flats"][0]["flat_id"]
    assert user["flats"][0]["flat_number"] == "T12-0408"
    assert user["flats"][0]["member_type"] == "TENANT"

    headers = {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------
    # Step 2: View Outstanding Bill Summary
    # -------------------------------------------------------------
    summary_resp = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["flat_number"] == "T12-0408"
    assert summary["area_sqft"] == 980.0
    assert summary["current_due"] == 6370.0  # 980 * 6.50
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
            "test_outcome": "FAILED"
        }
    )
    assert failed_pay.status_code == 200
    assert failed_pay.json()["status"] == "FAILED"
    assert failed_pay.json()["receipt"] is None

    # Check dues still intact
    summary_check1 = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_check1["current_due"] == 6370.0

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
    assert pay_data["amount"] == 6370.0
    assert pay_data["receipt"] is not None
    receipt_no = pay_data["receipt"]["receipt_number"]
    assert receipt_no.startswith("REC-")
    assert pay_data["receipt"]["flat_number"] == "T12-0408"
    assert pay_data["receipt"]["resident_name"] == "Swati Joshi"

    # Dues must now be exactly 0
    summary_check2 = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_check2["current_due"] == 0.0

    # -------------------------------------------------------------
    # Step 5: Check Running Flat Ledger Reconciliation
    # -------------------------------------------------------------
    ledger_resp = client.get(f"/api/v1/billing/flats/{flat_id}/ledger", headers=headers)
    assert ledger_resp.status_code == 200
    ledger_entries = ledger_resp.json()
    assert len(ledger_entries) >= 2
    # First entry debit (Bill 6370), Second entry credit (Payment 6370 -> Balance 0)
    latest_entry = ledger_entries[-1]
    assert latest_entry["entry_type"] == "CREDIT"
    assert latest_entry["amount"] == 6370.0
    assert latest_entry["balance_after"] == 0.0

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
            "test_outcome": "SUCCESS"
        }
    )
    assert duplicate_pay.status_code == 400
    assert "already fully paid" in duplicate_pay.json()["error"]["message"]

    # -------------------------------------------------------------
    # Step 7: Verify Neeraj Kulkarni (T07-1203) - Already Paid
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    neeraj_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"}).json()
    neeraj_headers = {"Authorization": f"Bearer {neeraj_login['access_token']}"}
    neeraj_flat_id = neeraj_login["user"]["flats"][0]["flat_id"]

    neeraj_summary = client.get(f"/api/v1/billing/flats/{neeraj_flat_id}/summary", headers=neeraj_headers).json()
    assert neeraj_summary["flat_number"] == "T07-1203"
    assert neeraj_summary["area_sqft"] == 1150.0
    assert neeraj_summary["current_due"] == 0.0
    assert neeraj_summary["latest_bill"]["principal_amount"] == 7475.0
    assert neeraj_summary["latest_bill"]["paid_amount"] == 7475.0
    assert neeraj_summary["latest_bill"]["status"] == "PAID"

    # -------------------------------------------------------------
    # Step 8: Verify Aamir Shaikh (T21-1601) - Partially Paid
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543212"})
    aamir_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543212", "otp": "123456"}).json()
    aamir_headers = {"Authorization": f"Bearer {aamir_login['access_token']}"}
    aamir_flat_id = aamir_login["user"]["flats"][0]["flat_id"]

    aamir_summary = client.get(f"/api/v1/billing/flats/{aamir_flat_id}/summary", headers=aamir_headers).json()
    assert aamir_summary["flat_number"] == "T21-1601"
    assert aamir_summary["area_sqft"] == 1640.0
    assert aamir_summary["latest_bill"]["principal_amount"] == 10660.0
    assert aamir_summary["latest_bill"]["paid_amount"] == 5000.0
    assert aamir_summary["current_due"] == 5660.0
    assert aamir_summary["overdue_days"] >= 15
    assert aamir_summary["latest_bill"]["status"] == "PARTIALLY_PAID"

    # -------------------------------------------------------------
    # Step 9: Committee Role Strict Scoping Verification
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543250"})
    comm_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543250", "otp": "123456"}).json()
    comm_headers = {"Authorization": f"Bearer {comm_login['access_token']}"}

    # Committee can view aggregate billing metrics
    comm_agg = client.get("/api/v1/billing/committee/aggregate", headers=comm_headers)
    assert comm_agg.status_code == 200
    agg_data = comm_agg.json()
    assert "total_billed_inr" in agg_data
    assert "total_collected_inr" in agg_data
    assert "collection_efficiency_pct" in agg_data

    # Committee is strictly blocked (403) from individual flat billing summaries
    comm_flat_drilldown = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=comm_headers)
    assert comm_flat_drilldown.status_code == 403

    # -------------------------------------------------------------
    # Step 10: Family Member Permission Scoping
    # -------------------------------------------------------------
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543213"})
    ananya_login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543213", "otp": "123456"}).json()
    ananya_headers = {"Authorization": f"Bearer {ananya_login['access_token']}"}
    ananya_flat_id = ananya_login["user"]["flats"][0]["flat_id"]

    # Ananya can view billing summary for T07-1203
    ananya_summary = client.get(f"/api/v1/billing/flats/{ananya_flat_id}/summary", headers=ananya_headers)
    assert ananya_summary.status_code == 200

    # But Ananya cannot pay bills (can_pay_bills=False)
    ananya_pay = client.post(
        "/api/v1/payments/checkout",
        headers=ananya_headers,
        json={
            "flat_id": ananya_flat_id,
            "bill_id": neeraj_summary["latest_bill"]["id"],
            "amount": 100.0,
            "test_outcome": "SUCCESS"
        }
    )
    assert ananya_pay.status_code == 403
    assert "does not permit bill payment" in ananya_pay.json()["error"]["message"].lower()
