"""
Township One - Resident Security, Billing, and Payment Authorization Tests.

Comprehensive backend verification for:
- Strict cross-flat access denial (summary view and payment checkout)
- Flat membership RBAC: Tenant payment authority vs Family view-only permissions
- Role tampering immunity (header-based role spoofing strictly rejected)
- Bill settlement lifecycle (fully paid bill cannot be repaid)
- Non-success payment outcome idempotency (ledger and balance remain unchanged)
- Cross-flat idempotency key isolation (collision returns 409 without leaking metadata)
- Duplicate monthly bill prevention
- Late fee interest calculation grace period boundaries
- Integer paise financial ledger reconciliation without floating point error
- Illustrative late-fee demo rule compliance
"""

import uuid
import re
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import (
    User, Flat, Bill, FlatLedgerEntry, OTPChallenge, PaymentIdempotencyRecord, BillingRule
)
from backend.app.services.billing import evaluate_bill_overdue_and_interest

client = TestClient(app)


def get_auth_token(phone: str) -> tuple[str, dict]:
    """Helper to authenticate test resident and return (jwt_token, user_dict)."""
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    client.post("/api/v1/auth/otp/request", json={"phone": phone})
    res = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    csrf = res.cookies.get("township_csrf", "")
    client.headers["X-CSRF-Token"] = csrf
    data = res.json()
    return data["access_token"], data["user"]


# ------------------------------------------------------------------------------
# 1. Cross-flat access denial (403)
# ------------------------------------------------------------------------------
def test_cross_flat_access_is_denied():
    swati_token, swati_user = get_auth_token("9876543211")
    neeraj_token, neeraj_user = get_auth_token("9876543210")

    swati_flat_id = swati_user["flats"][0]["flat_id"]
    neeraj_flat_id = neeraj_user["flats"][0]["flat_id"]

    neeraj_summary = client.get(
        f"/api/v1/billing/flats/{neeraj_flat_id}/summary",
        cookies={"township_session": neeraj_token}
    ).json()
    neeraj_bill_id = neeraj_summary["latest_bill"]["id"]

    # 1. Cross-flat summary view attempt -> 403
    resp_view = client.get(
        f"/api/v1/billing/flats/{neeraj_flat_id}/summary",
        cookies={"township_session": swati_token}
    )
    assert resp_view.status_code == 403
    assert "Access denied" in resp_view.json()["error"]["message"]

    # 2. Cross-flat bill payment attempt -> 403
    resp_pay = client.post(
        "/api/v1/payments/checkout",
        cookies={"township_session": swati_token},
        json={
            "flat_id": neeraj_flat_id,
            "bill_id": neeraj_bill_id,
            "amount": 500.0,
            "idempotency_key": str(uuid.uuid4()),
            "test_outcome": "SUCCESS"
        }
    )
    assert resp_pay.status_code == 403
    assert "Access denied" in resp_pay.json()["error"]["message"]


# ------------------------------------------------------------------------------
# 2. Tenant payment authorization vs family view-only permissions
# ------------------------------------------------------------------------------
def test_tenant_and_family_permissions():
    swati_token, swati_user = get_auth_token("9876543211") # Tenant, can_pay_bills=True
    ananya_token, ananya_user = get_auth_token("9876543213") # Family, can_pay_bills=False

    swati_flat_id = swati_user["flats"][0]["flat_id"]
    neeraj_flat_id = ananya_user["flats"][0]["flat_id"]

    # Tenant view -> 200
    resp_swati_view = client.get(
        f"/api/v1/billing/flats/{swati_flat_id}/summary",
        cookies={"township_session": swati_token}
    )
    assert resp_swati_view.status_code == 200

    # Family view -> 200 OK (family member can view flat dues)
    resp_family_view = client.get(
        f"/api/v1/billing/flats/{neeraj_flat_id}/summary",
        cookies={"township_session": ananya_token}
    )
    assert resp_family_view.status_code == 200
    summary = resp_family_view.json()
    bill_id = summary["latest_bill"]["id"]

    # Family payment attempt -> 403 Forbidden (can_pay_bills is False)
    resp_family_pay = client.post(
        "/api/v1/payments/checkout",
        cookies={"township_session": ananya_token},
        json={
            "flat_id": neeraj_flat_id,
            "bill_id": bill_id,
            "amount": 100.0,
            "idempotency_key": str(uuid.uuid4()),
            "test_outcome": "SUCCESS"
        }
    )
    assert resp_family_pay.status_code == 403
    assert "permit bill payment" in resp_family_pay.json()["error"]["message"].lower()


# ------------------------------------------------------------------------------
# 3. Role tampering rejected: authority strictly verified against database
# ------------------------------------------------------------------------------
def test_role_tampering_rejected():
    resident_token, _ = get_auth_token("9876543211")
    resp_tamper = client.get(
        "/api/v1/billing/committee/aggregate",
        headers={
            "X-User-Role": "COMMITTEE",
            "X-Role": "ADMIN",
            "Role": "ADMIN"
        }
    )
    assert resp_tamper.status_code == 403
    assert "Required role" in resp_tamper.json()["error"]["message"]
    assert "RESIDENT" in resp_tamper.json()["error"]["message"]


# ------------------------------------------------------------------------------
# 4. Fully settled bills cannot be repaid (400)
# ------------------------------------------------------------------------------
def test_paid_bill_cannot_be_repaid():
    token, user = get_auth_token("9876543210")
    flat_id = user["flats"][0]["flat_id"]

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary").json()
    bill_id = summary["latest_bill"]["id"]

    resp = client.post(
        "/api/v1/payments/checkout",
        json={
            "flat_id": flat_id,
            "bill_id": bill_id,
            "amount": 100.0,
            "idempotency_key": str(uuid.uuid4()),
            "test_outcome": "SUCCESS"
        }
    )
    assert resp.status_code == 400
    assert "already fully paid" in resp.json()["error"]["message"]


# ------------------------------------------------------------------------------
# 5. Non-success payment outcomes leave balances unchanged
# ------------------------------------------------------------------------------
def test_non_success_payment_leaves_balance_unchanged():
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]

    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary").json()
    bill_id = summary_before["latest_bill"]["id"]
    balance_before = summary_before["latest_bill"]["balance_amount"]
    ledger_count_before = len(summary_before["recent_ledger"])

    for outcome in ["PENDING", "FAILED", "EXPIRED"]:
        resp_outcome = client.post(
            "/api/v1/payments/checkout",
            json={
                "flat_id": flat_id,
                "bill_id": bill_id,
                "amount": 150.0,
                "idempotency_key": str(uuid.uuid4()),
                "test_outcome": outcome
            }
        )
        assert resp_outcome.status_code == 200
        assert resp_outcome.json()["status"] == outcome

    summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary").json()
    assert summary_after["latest_bill"]["balance_amount"] == balance_before
    assert len(summary_after["recent_ledger"]) == ledger_count_before


# ------------------------------------------------------------------------------
# 6. Cross-flat duplicate idempotency rejected (409) without leaking data
# ------------------------------------------------------------------------------
def test_idempotency_key_cannot_cross_flats():
    swati_token, swati_user = get_auth_token("9876543211") # Flat T12-0408 (unpaid)
    swati_flat_id = swati_user["flats"][0]["flat_id"]
    swati_summary = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary").json()
    swati_bill_id = swati_summary["latest_bill"]["id"]

    shared_key = f"IDEM-CROSS-FLAT-{uuid.uuid4()}"

    # Swati successfully checks out with shared_key
    resp_swati = client.post(
        "/api/v1/payments/checkout",
        json={
            "flat_id": swati_flat_id,
            "bill_id": swati_bill_id,
            "amount": 100.0,
            "idempotency_key": shared_key,
            "test_outcome": "SUCCESS"
        }
    )
    assert resp_swati.status_code == 200

    # Aamir attempts checkout using the same idempotency key for his flat
    aamir_token, aamir_user = get_auth_token("9876543212") # Flat T21-1601 (unpaid)
    aamir_flat_id = aamir_user["flats"][0]["flat_id"]
    aamir_summary = client.get(f"/api/v1/billing/flats/{aamir_flat_id}/summary").json()
    aamir_bill_id = aamir_summary["latest_bill"]["id"]

    resp_aamir = client.post(
        "/api/v1/payments/checkout",
        json={
            "flat_id": aamir_flat_id,
            "bill_id": aamir_bill_id,
            "amount": 100.0,
            "idempotency_key": shared_key,
            "test_outcome": "SUCCESS"
        }
    )
    assert resp_aamir.status_code == 409
    body_str = resp_aamir.text
    # Strict information leakage check: does not reveal Swati's flat, name, or transaction
    assert swati_flat_id not in body_str
    assert "Swati" not in body_str
    assert "T12-0408" not in body_str


# ------------------------------------------------------------------------------
# 7. Cannot generate duplicate monthly bill for same flat/month
# ------------------------------------------------------------------------------
def test_monthly_bill_not_duplicated():
    accounts_token, _ = get_auth_token("9876543240") # Anita Deshmukh (ACCOUNTS)
    _, swati_user = get_auth_token("9876543211")
    swati_flat_id = swati_user["flats"][0]["flat_id"]

    # Re-login as Anita to make sure accounts session is active
    get_auth_token("9876543240")

    resp_dup = client.post(
        "/api/v1/billing/generate",
        json={
            "flat_id": swati_flat_id,
            "period_month": 9,
            "period_year": 2026
        }
    )
    assert resp_dup.status_code == 409
    error_msg = resp_dup.json().get("error", {}).get("message") or resp_dup.json().get("detail", "")
    assert "already exists" in error_msg


# ------------------------------------------------------------------------------
# 8. Late fee grace period boundaries tested
# ------------------------------------------------------------------------------
def test_late_fee_grace_boundaries():
    rule = BillingRule(
        name="Test Boundary Rule",
        rate_per_sqft=Decimal("6.50"),
        due_day_of_month=15,
        grace_period_days=5,
        late_fee_percentage_pa=Decimal("18.00")
    )
    due_date = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
    principal = Decimal("6370.00")
    test_bill = Bill(
        flat_id="test-flat",
        billing_rule_version="v1.0",
        period_month=9,
        period_year=2026,
        issue_date=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        due_date=due_date,
        area_sqft=Decimal("980.00"),
        rate_per_sqft=Decimal("6.50"),
        principal_amount=principal,
        late_fee_amount=Decimal("0.00"),
        total_amount=principal,
        paid_amount=Decimal("0.00"),
        balance_amount=principal,
        status="ISSUED"
    )

    # 1. On due date (Sept 15): 0 overdue days, 0 interest
    eval_due = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc))
    assert eval_due.calendar_overdue_days == 0
    assert eval_due.interest_eligible_days == 0
    assert eval_due.late_fee == Decimal("0.00")

    # 2. Inside grace period (Sept 19 = 4 days overdue <= 5): 4 overdue days, 0 interest
    eval_grace = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=datetime(2026, 9, 19, 0, 0, tzinfo=timezone.utc))
    assert eval_grace.calendar_overdue_days == 4
    assert eval_grace.interest_eligible_days == 0
    assert eval_grace.late_fee == Decimal("0.00")

    # 3. Exact grace expiry boundary (Sept 20 = 5 days overdue == 5): 5 overdue days, 0 interest
    eval_boundary = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc))
    assert eval_boundary.calendar_overdue_days == 5
    assert eval_boundary.interest_eligible_days == 0
    assert eval_boundary.late_fee == Decimal("0.00")

    # 4. First day of interest eligibility (Sept 21 = 6 days overdue > 5): 1 interest eligible day
    eval_first_interest = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc))
    assert eval_first_interest.calendar_overdue_days == 6
    assert eval_first_interest.interest_eligible_days == 1
    # 6370 * 0.18 * 1 / 365 = 3.141369... -> 3.14
    assert eval_first_interest.late_fee == Decimal("3.14")

    # 5. As-of reference date (Nov 6 = 52 days overdue > 5): 47 interest eligible days
    eval_demo_date = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc))
    assert eval_demo_date.calendar_overdue_days == 52
    assert eval_demo_date.interest_eligible_days == 47
    # 6370 * 0.18 * 47 / 365 = 147.64438... -> 147.64
    assert eval_demo_date.late_fee == Decimal("147.64")


# ------------------------------------------------------------------------------
# 9. Ledger reconciliation: sum(credits) - sum(debits) matches balance without float drift
# ------------------------------------------------------------------------------
def test_ledger_reconciles_without_float():
    db = SessionLocal()
    try:
        flats = db.query(Flat).all()
        for f in flats:
            entries = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.flat_id == f.id).all()
            if entries:
                debits = sum((e.amount for e in entries if e.entry_type == "DEBIT"), Decimal("0.00"))
                credits = sum((e.amount for e in entries if e.entry_type == "CREDIT"), Decimal("0.00"))
                expected_balance = debits - credits
                latest_entry = sorted(entries, key=lambda e: e.created_at)[-1]
                assert latest_entry.balance_after == expected_balance
    finally:
        db.close()


# ------------------------------------------------------------------------------
# 10. Illustrative demo rule explicitly labeled in backend late fee summary
# ------------------------------------------------------------------------------
def test_demo_rule_label_present():
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary").json()
    assert "Illustrative demo rule" in summary["late_fee_notice"]
    assert "Model Bye-Law No. 67" in summary["late_fee_notice"]
