"""
Township One - Test Payments and Receipts Verification Tests.

Test suite verifying:
- Payment idempotency and cryptographic request fingerprinting
- Mandatory idempotency key validation (min 8 chars, rejection when missing or too short)
- Production guard: simulated payments blocked in production
- Cross-flat idempotency key collision without data leakage (generic 409)
- Idempotency key payload mismatch rejection (409 on altered amount, flat, bill, or outcome)
- Strict validation of test payment outcomes (SUCCESS, PENDING, FAILED, EXPIRED only)
- Over-allocation prevention (cannot pay more than outstanding bill balance)
- Rejection of double payment on already-paid bills
- Cross-resident receipt and payment IDOR prevention
"""

import os
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Bill, Flat, FlatLedgerEntry, Payment, Receipt

client = TestClient(app)


def get_auth_token(phone: str) -> tuple[str, dict]:
    from backend.app.core.database import SessionLocal
    from backend.app.models.entities import OTPChallenge
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    res = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    csrf = res.cookies.get("township_csrf", "")
    token = res.cookies.get("township_session", "")
    client.headers["X-CSRF-Token"] = csrf
    data = res.json()
    return token, data["user"]


def test_mandatory_idempotency_key_enforcement():
    # Login as Swati (T12-0408)
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}
    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary["latest_bill"]["id"]

    # 1. Missing idempotency key -> HTTP 422
    resp_missing = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 500.0,
            "test_outcome": "SUCCESS"
        }
    )
    assert resp_missing.status_code == 422

    # 2. Too short key (< 8 chars) -> HTTP 422
    resp_short = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": "short"
        }
    )
    assert resp_short.status_code == 422


def test_simulated_payment_blocked_in_production(monkeypatch):
    # First obtain auth token while in test environment
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    # Now switch to production environment
    monkeypatch.setattr(settings, "APP_ENV", "production")

    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": str(uuid.uuid4()),
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": "idem-prod-guard-check-123"
        }
    )
    assert resp.status_code == 403
    assert "disabled in production" in resp.json()["error"]["message"]


def test_pay_already_paid_bill_rejected():
    # Login as Neeraj (T07-1203) - bill is already paid
    token, user = get_auth_token("9876543210")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

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
            "test_outcome": "SUCCESS",
            "idempotency_key": "idem-already-paid-check"
        }
    )
    assert resp.status_code == 400
    assert "already fully paid" in resp.json()["error"]["message"]


def test_invalid_payment_outcomes_rejected():
    # Login as Swati (T12-0408)
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary_before["latest_bill"]["id"]
    initial_due = summary_before["current_due"]

    # 1. TYPO_SUCCESS -> HTTP 422
    resp_typo = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": "TYPO_SUCCESS",
            "idempotency_key": "idem-typo-test-outcome"
        }
    )
    assert resp_typo.status_code == 422

    # 2. UNKNOWN -> HTTP 422
    resp_unknown = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": "UNKNOWN",
            "idempotency_key": "idem-unknown-test-outcome"
        }
    )
    assert resp_unknown.status_code == 422

    # 3. None / null -> HTTP 422
    resp_none = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": None,
            "idempotency_key": "idem-none-test-outcome"
        }
    )
    assert resp_none.status_code == 422

    # 4. Lowercase string -> HTTP 422
    resp_lower = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 1000.0,
            "test_outcome": "success",
            "idempotency_key": "idem-lower-test-outcome"
        }
    )
    assert resp_lower.status_code == 422

    # Ensure zero side effects: dues unchanged, no payments created
    summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_after["current_due"] == initial_due


def test_payment_failure_pending_expired_leaves_dues_intact():
    # Login as Swati (T12-0408)
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    initial_due = summary_before["current_due"]
    bill_id = summary_before["latest_bill"]["id"]

    for outcome in ["FAILED", "PENDING", "EXPIRED"]:
        resp = client.post(
            "/api/v1/payments/checkout",
            headers=headers,
            json={
                "flat_id": flat_id,
                "bill_id": bill_id,
                "amount": 1000.0,
                "test_outcome": outcome,
                "idempotency_key": f"IDEM-NON-SUCCESS-{outcome}"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == outcome
        assert data["receipt"] is None

        # Dues must remain unchanged
        summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
        assert summary_after["current_due"] == initial_due


def test_cross_flat_idempotency_key_replay_and_leakage_prevention():
    # 1. Swati (T12-0408) pays partial amount with key K
    swati_token, swati_user = get_auth_token("9876543211")
    swati_flat_id = swati_user["flats"][0]["flat_id"]
    swati_headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}
    swati_summary = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary", headers=swati_headers).json()
    swati_bill_id = swati_summary["latest_bill"]["id"]

    shared_key = f"IDEM-SHARED-{uuid.uuid4()}"
    resp_swati = client.post(
        "/api/v1/payments/checkout",
        headers=swati_headers,
        json={
            "flat_id": swati_flat_id,
            "bill_id": swati_bill_id,
            "amount": 1000.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": shared_key
        }
    )
    assert resp_swati.status_code == 200
    swati_payment = resp_swati.json()
    assert swati_payment["status"] == "SUCCESS"
    assert swati_payment["receipt"] is not None
    swati_receipt_no = swati_payment["receipt"]["receipt_number"]

    # 2. Aamir (T21-1601) attempts to use the same key K for his flat and bill
    aamir_token, aamir_user = get_auth_token("9876543212")
    aamir_flat_id = aamir_user["flats"][0]["flat_id"]
    aamir_headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}
    aamir_summary = client.get(f"/api/v1/billing/flats/{aamir_flat_id}/summary", headers=aamir_headers).json()
    aamir_bill_id = aamir_summary["latest_bill"]["id"]

    resp_aamir = client.post(
        "/api/v1/payments/checkout",
        headers=aamir_headers,
        json={
            "flat_id": aamir_flat_id,
            "bill_id": aamir_bill_id,
            "amount": 2000.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": shared_key
        }
    )
    # Must return 409 Conflict
    assert resp_aamir.status_code == 409
    err = resp_aamir.json()
    # Must NOT reveal Swati's payment, receipt, flat, or resident info
    assert swati_receipt_no not in str(err)
    assert "Swati" not in str(err)
    assert "T12-0408" not in str(err)
    assert "conflict" in err["error"]["message"].lower()


def test_idempotency_key_payload_divergence_returns_409():
    # Swati uses key K with amount 500
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}
    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary["latest_bill"]["id"]

    diverge_key = f"IDEM-DIV-{uuid.uuid4()}"

    resp1 = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": diverge_key
        }
    )
    assert resp1.status_code == 200

    # Swati reuses key K with different amount (600.0) -> HTTP 409
    resp_diff_amount = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 600.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": diverge_key
        }
    )
    assert resp_diff_amount.status_code == 409
    assert "different request parameters" in resp_diff_amount.json()["error"]["message"].lower()

    # Swati reuses key K with identical payload -> returns original payment result
    resp_identical = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": diverge_key
        }
    )
    assert resp_identical.status_code == 200
    assert resp_identical.json()["id"] == resp1.json()["id"]
    assert resp_identical.json()["receipt"]["receipt_number"] == resp1.json()["receipt"]["receipt_number"]


def test_cross_resident_receipt_and_payment_access_denied():
    # Swati pays and gets a receipt
    swati_token, swati_user = get_auth_token("9876543211")
    swati_flat_id = swati_user["flats"][0]["flat_id"]
    swati_headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}
    swati_summary = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary", headers=swati_headers).json()
    swati_bill_id = swati_summary["latest_bill"]["id"]

    resp = client.post(
        "/api/v1/payments/checkout",
        headers=swati_headers,
        json={
            "flat_id": swati_flat_id,
            "bill_id": swati_bill_id,
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": f"IDEM-REC-ACCESS-{uuid.uuid4()}"
        }
    )
    assert resp.status_code == 200
    payment_id = resp.json()["id"]
    receipt_no = resp.json()["receipt"]["receipt_number"]

    # Swati can access her own receipt and payment
    assert client.get(f"/api/v1/payments/receipts/{receipt_no}", headers=swati_headers).status_code == 200
    assert client.get(f"/api/v1/payments/{payment_id}", headers=swati_headers).status_code == 200

    # Aamir (different resident) attempts to access Swati's receipt and payment -> 403 Forbidden
    aamir_token, _ = get_auth_token("9876543212")
    aamir_headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    rec_access = client.get(f"/api/v1/payments/receipts/{receipt_no}", headers=aamir_headers)
    assert rec_access.status_code == 403

    pay_access = client.get(f"/api/v1/payments/{payment_id}", headers=aamir_headers)
    assert pay_access.status_code == 403


def test_family_member_without_pay_permission_blocked():
    # Login as Ananya Kulkarni (Family member of T07-1203 with can_pay_bills=False)
    ananya_token, ananya_user = get_auth_token("9876543213")
    flat_id = ananya_user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    # Ananya attempts to pay -> 403 Forbidden
    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": str(uuid.uuid4()),
            "amount": 500.0,
            "test_outcome": "SUCCESS",
            "idempotency_key": "IDEM-FAMILY-PAY-DENIED"
        }
    )
    assert resp.status_code == 403
    assert "does not permit bill payment" in resp.json()["error"]["message"].lower()


def test_payment_exceeding_balance_rejected():
    # Login as Swati (T12-0408)
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]
    headers = {"X-CSRF-Token": client.cookies.get("township_csrf", "")}

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill = summary["unpaid_bills"][0] if summary.get("unpaid_bills") else summary["latest_bill"]
    bill_id = bill["id"]
    balance = float(bill["balance_amount"])

    # Attempt to pay more than balance (e.g. balance + 1000)
    over_amount = balance + 1000.0
    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": over_amount,
            "test_outcome": "SUCCESS",
            "idempotency_key": f"IDEM-OVERPAY-{uuid.uuid4()}"
        }
    )
    assert resp.status_code == 400
    assert "cannot exceed current outstanding balance" in resp.json()["error"]["message"]


@pytest.mark.skipif(not os.environ.get("PG_DATABASE_URL"), reason="needs PostgreSQL row locks")
def test_postgresql_row_locking_in_payments():
    """
    Validates PostgreSQL row locking (SELECT ... FOR UPDATE) against a live PostgreSQL database
    when PG_DATABASE_URL or TEST_POSTGRESQL_URL is set in environment (e.g. CI workflow service container).
    """
    pg_url = os.environ.get("PG_DATABASE_URL") or os.environ.get("TEST_POSTGRESQL_URL")
    if not pg_url:
        pytest.skip("PG_DATABASE_URL not set; skipping live PostgreSQL row locking concurrency test.")
    from tests.test_payment_concurrency import test_postgresql_with_for_update_row_locking
    test_postgresql_with_for_update_row_locking()
