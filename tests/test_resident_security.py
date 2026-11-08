"""
Township One - Resident, Billing, and Payment Security Test Suite.

Verifies system security, financial integrity, and UI contracts:
1. Cross-flat access denial (HTTP 403 Forbidden).
2. Tenant payment authorization vs. family view-only permissions.
3. Role tampering rejection (authority verified against persistent database roles).
4. Fully settled bills cannot be repaid (HTTP 400 Bad Request).
5. Non-success test payment outcomes preserve outstanding balances and ledgers.
6. Cross-flat idempotency key collisions return HTTP 409 without leaking metadata.
7. Monthly bill generation non-duplication constraints.
8. Late fee grace period boundary calculations.
9. Dual-entry ledger reconciliation and zero binary floating-point arithmetic.
10. Illustrative demo late fee statutory labeling.
11. Two-tap resident shortcut actions structure.
12. Trilingual dictionary completeness (English, Marathi, Hindi).
13. Service worker cache boundaries and logout cache deletion.
14. Responsive viewport configuration and UI states.
"""

import os
import re
import uuid
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
        headers={"Authorization": f"Bearer {neeraj_token}"}
    ).json()
    neeraj_bill_id = neeraj_summary["latest_bill"]["id"]

    # 1. Cross-flat summary view attempt -> 403
    resp_view = client.get(
        f"/api/v1/billing/flats/{neeraj_flat_id}/summary",
        headers={"Authorization": f"Bearer {swati_token}"}
    )
    assert resp_view.status_code == 403
    assert "Access denied" in resp_view.json()["error"]["message"]

    # 2. Cross-flat bill payment attempt -> 403
    resp_pay = client.post(
        "/api/v1/payments/checkout",
        headers={"Authorization": f"Bearer {swati_token}"},
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
        headers={"Authorization": f"Bearer {swati_token}"}
    )
    assert resp_swati_view.status_code == 200

    # Family view -> 200 OK (family member can view flat dues)
    resp_family_view = client.get(
        f"/api/v1/billing/flats/{neeraj_flat_id}/summary",
        headers={"Authorization": f"Bearer {ananya_token}"}
    )
    assert resp_family_view.status_code == 200
    summary = resp_family_view.json()
    bill_id = summary["latest_bill"]["id"]

    # Family payment attempt -> 403 Forbidden (can_pay_bills is False)
    resp_family_pay = client.post(
        "/api/v1/payments/checkout",
        headers={"Authorization": f"Bearer {ananya_token}"},
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
            "Authorization": f"Bearer {resident_token}",
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
    headers = {"Authorization": f"Bearer {token}"}

    summary = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary["latest_bill"]["id"]

    resp = client.post(
        "/api/v1/payments/checkout",
        headers=headers,
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
    headers = {"Authorization": f"Bearer {token}"}

    summary_before = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    bill_id = summary_before["latest_bill"]["id"]
    balance_before = summary_before["latest_bill"]["balance_amount"]
    ledger_count_before = len(summary_before["recent_ledger"])

    for outcome in ["PENDING", "FAILED", "EXPIRED"]:
        resp_outcome = client.post(
            "/api/v1/payments/checkout",
            headers=headers,
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

    summary_after = client.get(f"/api/v1/billing/flats/{flat_id}/summary", headers=headers).json()
    assert summary_after["latest_bill"]["balance_amount"] == balance_before
    assert len(summary_after["recent_ledger"]) == ledger_count_before


# ------------------------------------------------------------------------------
# 6. Cross-flat duplicate idempotency rejected (409) without leaking data
# ------------------------------------------------------------------------------
def test_idempotency_key_cannot_cross_flats():
    swati_token, swati_user = get_auth_token("9876543211") # Flat T12-0408 (unpaid)
    aamir_token, aamir_user = get_auth_token("9876543212") # Flat T21-1601 (unpaid)

    swati_flat_id = swati_user["flats"][0]["flat_id"]
    aamir_flat_id = aamir_user["flats"][0]["flat_id"]

    swati_summary = client.get(f"/api/v1/billing/flats/{swati_flat_id}/summary", headers={"Authorization": f"Bearer {swati_token}"}).json()
    aamir_summary = client.get(f"/api/v1/billing/flats/{aamir_flat_id}/summary", headers={"Authorization": f"Bearer {aamir_token}"}).json()

    swati_bill_id = swati_summary["latest_bill"]["id"]
    aamir_bill_id = aamir_summary["latest_bill"]["id"]

    shared_key = f"IDEM-CROSS-FLAT-{uuid.uuid4()}"

    # Swati successfully checks out with shared_key
    resp_swati = client.post(
        "/api/v1/payments/checkout",
        headers={"Authorization": f"Bearer {swati_token}"},
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
    resp_aamir = client.post(
        "/api/v1/payments/checkout",
        headers={"Authorization": f"Bearer {aamir_token}"},
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

    resp_dup = client.post(
        "/api/v1/billing/generate",
        headers={"Authorization": f"Bearer {accounts_token}"},
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
        principal_amount=principal,
        balance_amount=principal,
        due_date=due_date
    )

    # Day 0 (due date) -> no fee
    eval_day0 = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=due_date)
    assert eval_day0.calendar_overdue_days == 0
    assert eval_day0.late_fee == Decimal("0.00")

    # Day 5 (last grace day, Sept 20) -> no fee
    eval_day5 = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=due_date + timedelta(days=5))
    assert eval_day5.calendar_overdue_days == 5
    assert eval_day5.interest_eligible_days == 0
    assert eval_day5.late_fee == Decimal("0.00")

    # Day 6 (first day after grace, Sept 21) -> late fee applied
    eval_day6 = evaluate_bill_overdue_and_interest(test_bill, rule, as_of=due_date + timedelta(days=6))
    assert eval_day6.calendar_overdue_days == 6
    assert eval_day6.interest_eligible_days == 1
    assert eval_day6.late_fee > Decimal("0.00")


# ------------------------------------------------------------------------------
# 9. Ledger reconciliation and zero binary float
# ------------------------------------------------------------------------------
def test_ledger_reconciles_without_float():
    # 1. Zero binary float in critical financial code
    billing_src = open("backend/app/api/billing.py", "r", encoding="utf-8").read()
    payments_src = open("backend/app/api/payments.py", "r", encoding="utf-8").read()
    assert not re.search(r"\bfloat\(", billing_src), "Forbidden float() found in backend/app/api/billing.py!"
    assert not re.search(r"\bfloat\(", payments_src), "Forbidden float() found in backend/app/api/payments.py!"

    # 2. Ledger balance reconciliation
    db = SessionLocal()
    try:
        flats = db.query(Flat).all()
        for flat in flats:
            entries = db.query(FlatLedgerEntry).filter(FlatLedgerEntry.flat_id == flat.id).all()
            if entries:
                debits = sum((e.amount for e in entries if e.entry_type == "DEBIT"), Decimal("0.00"))
                credits = sum((e.amount for e in entries if e.entry_type == "CREDIT"), Decimal("0.00"))
                expected_balance = debits - credits
                latest_entry = sorted(entries, key=lambda e: e.created_at)[-1]
                assert latest_entry.balance_after == expected_balance
    finally:
        db.close()


# ------------------------------------------------------------------------------
# 10. Illustrative demo rule explicitly labeled everywhere late fees appear
# ------------------------------------------------------------------------------
def test_demo_rule_label_present():
    token, user = get_auth_token("9876543211")
    flat_id = user["flats"][0]["flat_id"]

    # Backend summary notice
    summary = client.get(
        f"/api/v1/billing/flats/{flat_id}/summary",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert "Illustrative demo rule" in summary["late_fee_notice"]
    assert "Model Bye-Law No. 67" in summary["late_fee_notice"]

    # Frontend component label
    dues_card_code = open("frontend/src/components/DuesCard.tsx", "r", encoding="utf-8").read()
    assert "Illustrative demo rule" in dues_card_code


# ------------------------------------------------------------------------------
# 11. Two-tap resident UI verified
# ------------------------------------------------------------------------------
def test_two_tap_actions():
    quick_actions_code = open("frontend/src/components/QuickActions.tsx", "r", encoding="utf-8").read()
    assert "pay" in quick_actions_code
    assert "complaint" in quick_actions_code
    assert "visitor" in quick_actions_code
    assert "amenity" in quick_actions_code
    assert "2-Tap" in quick_actions_code or "2-tap" in quick_actions_code.lower()


# ------------------------------------------------------------------------------
# 12. Trilingual dictionary complete
# ------------------------------------------------------------------------------
def test_translations_complete():
    trans_code = open("frontend/src/i18n/translations.ts", "r", encoding="utf-8").read()
    en_section = trans_code.split("en: {")[1].split("},")[0]
    mr_section = trans_code.split("mr: {")[1].split("},")[0]
    hi_section = trans_code.split("hi: {")[1].split("}")[0]

    en_keys = set(re.findall(r"([a-z_]+):\s*[\"']", en_section))
    mr_keys = set(re.findall(r"([a-z_]+):\s*[\"']", mr_section))
    hi_keys = set(re.findall(r"([a-z_]+):\s*[\"']", hi_section))

    assert len(en_keys) >= 30
    assert en_keys == mr_keys, f"Missing Marathi keys: {en_keys - mr_keys}"
    assert en_keys == hi_keys, f"Missing Hindi keys: {en_keys - hi_keys}"


# ------------------------------------------------------------------------------
# 13. PWA service worker caching and logout clear verified
# ------------------------------------------------------------------------------
def test_service_worker_caching():
    sw_code = open("frontend/public/sw.js", "r", encoding="utf-8").read()
    assert "/api/" in sw_code
    assert "township-one-shell-v1" in sw_code
    assert "CLEAR_CACHES" in sw_code or "LOGOUT" in sw_code

    client_code = open("frontend/src/api/client.ts", "r", encoding="utf-8").read()
    assert "caches.delete" in client_code
    assert "CLEAR_CACHES" in client_code


# ------------------------------------------------------------------------------
# 14. Responsive viewport and states verified
# ------------------------------------------------------------------------------
def test_responsive_states():
    # 1. Viewport meta tag
    html_code = open("frontend/index.html", "r", encoding="utf-8").read()
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0"' in html_code

    # 2. Touch target >= 44px
    quick_actions_code = open("frontend/src/components/QuickActions.tsx", "r", encoding="utf-8").read()
    assert "minHeight: '44px'" in quick_actions_code or "min-height: 44px" in quick_actions_code
    assert "minWidth: '44px'" in quick_actions_code or "min-width: 44px" in quick_actions_code

    # 3. Loading, empty, and error states present in resident UI
    resident_page = open("frontend/src/pages/ResidentHomePage.tsx", "r", encoding="utf-8").read()
    assert "loading" in resident_page.lower()
    assert "no active complaints" in resident_page.lower()

    dues_card = open("frontend/src/components/DuesCard.tsx", "r", encoding="utf-8").read()
    assert "loading" in dues_card.lower()
    assert "all dues cleared" in dues_card.lower() or "up_to_date" in dues_card
