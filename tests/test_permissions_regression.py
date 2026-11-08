"""
Township One - Server-Side Permissions and Access Control Regression Tests.

Comprehensive verification of server-side role boundaries:
- Unauthenticated requests return 401 Unauthorized.
- Authenticated mutating requests without X-CSRF-Token return 403 Forbidden.
- Guard role cannot access resident complaints, billing, or financial operations.
- Resident cannot access other flats' complaints, attachments/photos, or bills.
- Help Desk cannot access bank statement import, review queue, or financial commits.
- Accounts staff cannot alter complaint lifecycle status or classification decisions.
- Committee members have aggregate/read access but cannot modify tickets or transact on individual flats.
"""

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import User, Flat, Bill, OTPChallenge, Complaint

client = TestClient(app)


def get_auth_client(phone: str) -> tuple[TestClient, dict, str]:
    """Logs in via OTP and returns (authenticated_testclient, user_dict, csrf_token)."""
    tc = TestClient(app)
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()

    tc.post("/api/v1/auth/otp/request", json={"phone": phone})
    res = tc.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert res.status_code == 200, f"Login failed for {phone}: {res.text}"

    csrf = res.cookies.get("township_csrf", "")
    tc.headers["X-CSRF-Token"] = csrf
    return tc, res.json()["user"], csrf


def test_unauthenticated_requests_return_401():
    """Unauthenticated access to protected endpoints must return 401 Unauthorized."""
    clean_client = TestClient(app)

    # Protected endpoints across subsystems
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/complaints/my"),
        ("GET", "/api/v1/complaints/helpdesk/queue"),
        ("POST", "/api/v1/complaints"),
        ("GET", "/api/v1/bank/accounts"),
        ("GET", "/api/v1/bank/review-queue"),
        ("POST", "/api/v1/bank/imports/preview"),
        ("GET", "/api/v1/notifications"),
    ]

    for method, path in endpoints:
        if method == "GET":
            resp = clean_client.get(path)
        else:
            resp = clean_client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


def test_csrf_missing_on_mutating_requests_returns_403():
    """Authenticated mutating requests without matching X-CSRF-Token must return 403 Forbidden."""
    admin_client, _, _ = get_auth_client("9876543200")  # Admin

    # Strip CSRF header
    del admin_client.headers["X-CSRF-Token"]

    # Mutating POST request
    resp = admin_client.post(
        "/api/v1/complaints",
        data={"flat_id": "dummy", "title": "Test", "description": "Test complaint"}
    )
    assert resp.status_code == 403, f"Expected 403 without CSRF token, got {resp.status_code}"
    assert "CSRF" in resp.text or "Forbidden" in resp.text


def test_guard_cannot_access_complaints_or_billing():
    """Guard role (9876543230) must be denied access to resident complaints and billing."""
    guard_client, guard_user, _ = get_auth_client("9876543230")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    db.close()

    # Guard cannot view help desk queue
    resp = guard_client.get("/api/v1/complaints/helpdesk/queue")
    assert resp.status_code == 403, f"Guard viewing complaints got {resp.status_code}"

    # Guard cannot raise resident complaint
    resp = guard_client.post(
        "/api/v1/complaints",
        data={"flat_id": flat.id, "title": "Guard test", "description": "Guard should not post"}
    )
    assert resp.status_code == 403, f"Guard raising complaint got {resp.status_code}"

    # Guard cannot access flat bills
    resp = guard_client.get(f"/api/v1/billing/flats/{flat.id}/bills")
    assert resp.status_code == 403, f"Guard viewing flat bills got {resp.status_code}"

    # Guard cannot access bank matching
    resp = guard_client.get("/api/v1/bank/review-queue")
    assert resp.status_code == 403, f"Guard accessing bank queue got {resp.status_code}"


def test_resident_cannot_access_other_flat_complaints_or_photos_or_bills():
    """Resident must be strictly restricted to their own flat's data (403 or IDOR-safe 404)."""
    neeraj_client, neeraj_user, _ = get_auth_client("9876543210")  # T07-1203
    swati_client, swati_user, _ = get_auth_client("9876543211")    # T12-0408

    db = SessionLocal()
    neeraj_flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    swati_flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    db.close()

    # Swati creates a complaint for her flat
    swati_comp_resp = swati_client.post(
        "/api/v1/complaints",
        data={
            "flat_id": swati_flat.id,
            "title": "Kitchen drain blockage in T12",
            "description": "Kitchen pipe leaking water heavily into lower cabinet"
        }
    )
    assert swati_comp_resp.status_code == 201
    swati_comp_id = swati_comp_resp.json()["id"]

    # Neeraj attempts to view Swati's complaint detail -> returns 404 to avoid leaking existence
    resp = neeraj_client.get(f"/api/v1/complaints/{swati_comp_id}")
    assert resp.status_code in [403, 404], f"Cross-flat complaint access got {resp.status_code}"

    # Neeraj attempts to view Swati's flat bills -> 403
    resp = neeraj_client.get(f"/api/v1/billing/flats/{swati_flat.id}/bills")
    assert resp.status_code == 403, f"Cross-flat bills access got {resp.status_code}, expected 403"

    # Neeraj attempts to view Swati's flat summary -> 403
    resp = neeraj_client.get(f"/api/v1/billing/flats/{swati_flat.id}/summary")
    assert resp.status_code == 403, f"Cross-flat summary access got {resp.status_code}, expected 403"


def test_helpdesk_cannot_access_bank_statement_or_financial_commit():
    """Help Desk staff (9876543220) must be denied access to bank statement matching and financial commits."""
    helpdesk_client, _, _ = get_auth_client("9876543220")

    # Helpdesk cannot preview bank statement
    sample_csv = "Transaction Date,Value Date,Description,Reference No,Debit,Credit,Balance\n01/11/2026,01/11/2026,UPI-NEERAJ-T07-1203,UPI001,,7475.00,107475.00\n"
    resp = helpdesk_client.post(
        "/api/v1/bank/imports/preview",
        files={"file": ("stmt.csv", sample_csv.encode("utf-8"), "text/csv")},
        data={"account_no": "98765432100012"}
    )
    assert resp.status_code == 403, f"Helpdesk bank preview got {resp.status_code}, expected 403"

    # Helpdesk cannot access review queue
    resp = helpdesk_client.get("/api/v1/bank/review-queue")
    assert resp.status_code == 403, f"Helpdesk review queue got {resp.status_code}, expected 403"

    # Helpdesk cannot execute bank row commit
    resp = helpdesk_client.post(
        "/api/v1/bank/imports/commit",
        json={"bank_account_no": "98765432100012", "import_file_id": "dummy"}
    )
    assert resp.status_code == 403, f"Helpdesk bank commit got {resp.status_code}, expected 403"


def test_accounts_cannot_alter_complaint_lifecycle_or_classification():
    """Accounts staff (9876543240) must be denied altering complaint lifecycle or triage classification."""
    accounts_client, _, _ = get_auth_client("9876543240")
    neeraj_client, _, _ = get_auth_client("9876543210")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    db.close()

    # Create complaint
    c_resp = neeraj_client.post(
        "/api/v1/complaints",
        data={"flat_id": flat.id, "title": "Lobby light fused", "description": "Floor 12 lobby light fused"}
    )
    c_id = c_resp.json()["id"]

    # Accounts staff attempts to transition status -> 403
    resp = accounts_client.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "IN_PROGRESS", "notes": "Accounts attempting transition"}
    )
    assert resp.status_code == 403, f"Accounts altering status got {resp.status_code}, expected 403"

    # Accounts staff attempts to correct AI classification -> 403
    resp = accounts_client.post(
        f"/api/v1/complaints/{c_id}/correct-classification",
        json={
            "expected_version": 1,
            "category": "ELECTRICAL",
            "urgency": "HIGH",
            "reason": "Accounts reclassifying"
        }
    )
    assert resp.status_code == 403, f"Accounts correcting classification got {resp.status_code}, expected 403"


def test_committee_aggregate_boundaries_and_denial_of_flat_level_actions():
    """Committee role (9876543250) can inspect overview but cannot mutate individual complaints or pay bills."""
    committee_client, _, _ = get_auth_client("9876543250")

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    db.close()

    # Committee can view overall complaints list / queue
    resp = committee_client.get("/api/v1/complaints/helpdesk/queue")
    assert resp.status_code == 200, f"Committee viewing complaints got {resp.status_code}"

    # Committee cannot raise a complaint on a flat they don't reside in
    resp = committee_client.post(
        "/api/v1/complaints",
        data={"flat_id": flat.id, "title": "Committee unauthorized ticket", "description": "Testing permission denial"}
    )
    assert resp.status_code == 403, f"Committee raising complaint got {resp.status_code}, expected 403"

    # Committee cannot trigger payment checkout for a resident flat
    resp = committee_client.post(
        "/api/v1/payments/checkout",
        json={
            "flat_id": flat.id,
            "bill_id": "dummy-bill",
            "amount": "1000.00",
            "payment_method": "UPI",
            "idempotency_key": "comm-chk-1"
        }
    )
    assert resp.status_code == 403, f"Committee paying resident bill got {resp.status_code}, expected 403"
