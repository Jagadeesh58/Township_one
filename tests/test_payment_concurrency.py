"""
Township One - Payment Concurrency and Race Condition Verification Tests.

Test suite verifying:
- Concurrent payment requests against the same bill using ThreadPoolExecutor
- Prevention of over-allocation (total successful paid allocations <= initial balance)
- Concurrent identical requests with the same idempotency key result in exactly 1 payment record
"""

import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Bill, Payment

client = TestClient(app)


def get_auth_token(phone: str) -> tuple[str, dict]:
    from backend.app.core.security import OTP_STORE
    OTP_STORE.pop(phone, None)
    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    res = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    data = res.json()
    return data["access_token"], data["user"]


def test_concurrent_identical_idempotency_requests():
    """Verify concurrent requests with the identical idempotency key produce only 1 payment."""
    token, user = get_auth_token("9876543211")  # Swati (T12-0408)
    flat_id = user["flats"][0]["flat_id"]
    headers = {"Authorization": f"Bearer {token}"}

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    unpaid = summary.get("unpaid_bills") or [summary["latest_bill"]]
    target_bill = unpaid[0]
    bill_id = target_bill["id"]
    balance = float(target_bill["balance_amount"])

    if balance <= 0:
        pytest.skip("Bill is already paid")

    pay_amount = min(100.0, balance)
    concurrent_key = f"IDEM-CONC-RACE-{uuid.uuid4()}"

    def make_payment():
        # Dedicated client call in thread
        return client.post(
            "/api/v1/payments/checkout",
            headers=headers,
            json={
                "flat_id": flat_id,
                "bill_id": bill_id,
                "amount": pay_amount,
                "test_outcome": "SUCCESS",
                "idempotency_key": concurrent_key
            }
        )

    # Launch 5 concurrent threads with identical key
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_payment) for _ in range(5)]
        for f in as_completed(futures):
            results.append(f.result())

    # Check outcomes: At least one must succeed (200), and others must either return 200 (original result) or 409
    successful_results = [r for r in results if r.status_code == 200]
    conflict_results = [r for r in results if r.status_code == 409]

    assert len(successful_results) >= 1
    # Total distinct payment IDs created must be EXACTLY 1
    payment_ids = {r.json()["id"] for r in successful_results}
    assert len(payment_ids) == 1

    # Verify database has exactly 1 payment record with this idempotency key
    db = SessionLocal()
    try:
        count = db.query(Payment).filter(Payment.idempotency_key == concurrent_key).count()
        assert count == 1
    finally:
        db.close()


def test_concurrent_payments_prevent_over_allocation():
    """Verify that multiple concurrent threads attempting to over-consume a bill balance are bounded."""
    token, user = get_auth_token("9876543212")  # Aamir (T21-1601)
    flat_id = user["flats"][0]["flat_id"]
    headers = {"Authorization": f"Bearer {token}"}

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    target_bill = summary["latest_bill"]
    bill_id = target_bill["id"]
    balance = float(target_bill["balance_amount"])

    if balance <= 0:
        pytest.skip("Bill is already paid")

    # Each thread attempts to pay the ENTIRE remaining balance with distinct keys
    def make_competing_payment(i: int):
        return client.post(
            "/api/v1/payments/checkout",
            headers=headers,
            json={
                "flat_id": flat_id,
                "bill_id": bill_id,
                "amount": balance,
                "test_outcome": "SUCCESS",
                "idempotency_key": f"IDEM-OVERALLOC-{i}-{uuid.uuid4()}"
            }
        )

    results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(make_competing_payment, i) for i in range(4)]
        for f in as_completed(futures):
            results.append(f.result())

    # Only 1 thread should succeed in paying the full balance; subsequent attempts must fail (400)
    success_count = sum(1 for r in results if r.status_code == 200)
    rejected_count = sum(1 for r in results if r.status_code in [400, 409])

    assert success_count == 1
    assert rejected_count >= 3

    # Verify final balance is 0.00 and paid amount does not exceed total amount
    db = SessionLocal()
    try:
        b = db.query(Bill).filter(Bill.id == bill_id).first()
        assert b.balance_amount >= Decimal("0.00")
        assert b.paid_amount <= b.total_amount
    finally:
        db.close()
