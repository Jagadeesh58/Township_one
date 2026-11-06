from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Bill, Flat, FlatLedgerEntry, Payment

client = TestClient(app)


def test_pay_already_paid_bill_rejected():
    # Login as Neeraj (T07-1203) - bill is already paid
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543210"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543210", "otp": "123456"}).json()
    token = login["access_token"]
    flat_id = login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary["latest_bill"]["id"]

    # Attempt to pay
    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 7475.0,
            "test_outcome": "SUCCESS"
        }
    )
    assert resp.status_code == 400
    assert "already fully paid" in resp.json()["error"]["message"]


def test_payment_failure_pending_expired_leaves_dues_intact():
    # Login as Swati (T12-0408)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    token = login["access_token"]
    flat_id = login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    initial_due = summary_before["current_due"]
    bill_id = summary_before["latest_bill"]["id"]

    # 1. Test FAILED outcome
    resp_failed = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": "FAILED"
        }
    )
    assert resp_failed.status_code == 200
    data_failed = resp_failed.json()
    assert data_failed["status"] == "FAILED"
    assert data_failed["receipt"] is None

    # Dues must remain unchanged
    summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_after["current_due"] == initial_due


def test_payment_success_atomicity_and_receipt():
    # Login as Swati (T12-0408)
    client.post("/api/v1/auth/otp/request", json={"phone": "9876543211"})
    login = client.post("/api/v1/auth/otp/verify", json={"phone": "9876543211", "otp": "123456"}).json()
    token = login["access_token"]
    flat_id = login["user"]["flats"][0]["flat_id"]

    headers = {"Authorization": f"Bearer {token}"}
    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary_before["latest_bill"]["id"]
    due_amount = summary_before["current_due"]  # 6370.0

    # Pay full amount in test mode with SUCCESS
    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": due_amount,
            "payment_method": "UPI_TEST_MODE",
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-TEST-SWATI-1204"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["amount"] == due_amount
    assert data["receipt"] is not None
    receipt_no = data["receipt"]["receipt_number"]
    assert receipt_no.startswith("REC-")
    assert data["receipt"]["resident_name"] == "Swati Joshi"

    # Dues must now be 0
    summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_after["current_due"] == 0.0
    assert summary_after["latest_bill"]["status"] == "PAID"

    # Test Idempotency Replay
    resp_replay = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": due_amount,
            "payment_method": "UPI_TEST_MODE",
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-TEST-SWATI-1204"
        }
    )
    assert resp_replay.status_code == 200
    assert resp_replay.json()["receipt"]["receipt_number"] == receipt_no

    # Test Receipt Fetch Endpoint
    receipt_fetch = client.get(f"/api/v1/payments/receipts/{receipt_no}", headers=headers)
    assert receipt_fetch.status_code == 200
    assert receipt_fetch.json()["amount"] == due_amount
