from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import (
    Amenity,
    AmenitySlot,
    BankRow,
    Bill,
    BillLine,
    Flat,
    Notification,
    OTPChallenge,
    User,
)
from backend.app.services.billing import (
    generate_flat_bill,
)


def get_auth_client(phone: str) -> tuple[TestClient, dict]:
    db = SessionLocal()
    try:
        db.query(OTPChallenge).filter(OTPChallenge.phone == phone).delete()
        db.commit()
    finally:
        db.close()
    client = TestClient(app)
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req.status_code == 200
    res = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert res.status_code == 200
    csrf = res.cookies.get("township_csrf")
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    return client, headers


def test_bank_api_lifecycle():
    accounts_client, accounts_headers = get_auth_client("9876543240")  # Anita Deshmukh (ACCOUNTS)

    # 1. List accounts
    acc_res = accounts_client.get("/api/v1/bank/accounts", headers=accounts_headers)
    assert acc_res.status_code == 200
    accounts = acc_res.json()
    assert isinstance(accounts, list)

    # 2. Preview statement CSV
    csv_content = (
        b"account_no,txn_date,value_date,narration,direction,amount,currency,utr,payer_upi,flat_ref\n"
        b"98765432100012,2026-03-05,2026-03-05,NEFT maintenance,CREDIT,10660.00,INR,UTRAPI000001,neeraj@okaxis,T01-0101\n"
        b"98765432100012,2026-03-05,2026-03-05,Unknown deposit,CREDIT,5000.00,INR,UTRAPI000002,unknown@upi,\n"
    )

    preview_res = accounts_client.post(
        "/api/v1/bank/imports/preview",
        files={"file": ("statement_test.csv", csv_content, "text/csv")},
        headers=accounts_headers,
    )
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["total_rows"] == 2
    assert preview_data["accepted_rows"] == 2

    # 3. Commit statement CSV
    commit_res = accounts_client.post(
        "/api/v1/bank/imports/commit",
        files={"file": ("statement_test.csv", csv_content, "text/csv")},
        headers=accounts_headers,
    )
    assert commit_res.status_code == 200
    commit_data = commit_res.json()
    import_id = commit_data["import_file_id"]
    assert import_id is not None

    # 4. List statement imports
    imports_res = accounts_client.get("/api/v1/bank/imports?page=1&page_size=10", headers=accounts_headers)
    assert imports_res.status_code == 200
    imports_list = imports_res.json()
    assert "items" in imports_list
    assert len(imports_list["items"]) >= 1

    # 5. Get import rows
    rows_res = accounts_client.get(f"/api/v1/bank/imports/{import_id}/rows", headers=accounts_headers)
    assert rows_res.status_code == 200
    rows = rows_res.json()
    assert len(rows) == 2

    # 6. Get review queue
    review_res = accounts_client.get("/api/v1/bank/review-queue", headers=accounts_headers)
    assert review_res.status_code == 200
    review_rows = review_res.json()
    assert isinstance(review_rows, list)

    # 7. Apply review action (HOLD or REJECT on a pending row)
    db = SessionLocal()
    pending_row = db.query(BankRow).filter(BankRow.import_file_id == import_id, BankRow.decision == "REVIEW").first()
    db.close()

    if pending_row:
        action_res = accounts_client.post(
            f"/api/v1/bank/rows/{pending_row.id}/action",
            json={"action": "HOLD", "reason": "Awaiting proof from resident"},
            headers=accounts_headers,
        )
        assert action_res.status_code == 200
        assert action_res.json()["review_status"] == "HELD"

    # 8. List bank audit events
    audit_res = accounts_client.get("/api/v1/bank/audit?page=1&page_size=10", headers=accounts_headers)
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert isinstance(events, list)


def test_notifications_api_lifecycle():
    resident_client, resident_headers = get_auth_client("9876543210")  # Neeraj

    db = SessionLocal()
    user = db.query(User).filter(User.phone == "9876543210").first()
    assert user is not None

    # Insert a test unread notification
    notif = Notification(
        user_id=user.id,
        notification_type="SYSTEM",
        title="Maintenance Notice",
        message="Water shutdown scheduled for tomorrow 2 PM to 5 PM.",
        channel="IN_APP",
        is_read=False,
    )
    db.add(notif)
    db.commit()
    notif_id = notif.id
    db.close()

    # 1. Fetch unread count
    cnt_res = resident_client.get("/api/v1/notifications/unread-count", headers=resident_headers)
    assert cnt_res.status_code == 200
    assert cnt_res.json()["unread_count"] >= 1

    # 2. List notifications
    list_res = resident_client.get("/api/v1/notifications?unread_only=true", headers=resident_headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(n["id"] == notif_id for n in items)

    # 3. Mark single notification as read
    read_res = resident_client.post(f"/api/v1/notifications/{notif_id}/read", headers=resident_headers)
    assert read_res.status_code == 200
    assert read_res.json()["status"] == "READ"

    # 4. Mark all as read
    all_read_res = resident_client.post("/api/v1/notifications/read-all", headers=resident_headers)
    assert all_read_res.status_code == 200
    assert all_read_res.json()["status"] == "ALL_READ"


def test_amenities_booking_and_cancellation():
    resident_client, resident_headers = get_auth_client("9876543210")  # Neeraj

    db = SessionLocal()
    amenity = db.query(Amenity).first()
    assert amenity is not None
    slot = db.query(AmenitySlot).filter(AmenitySlot.amenity_id == amenity.id).first()
    assert slot is not None
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    assert flat is not None
    db.close()

    booking_date = (datetime.now(UTC) + timedelta(days=5)).strftime("%Y-%m-%d")

    # 1. Create booking
    book_res = resident_client.post(
        "/api/v1/amenities/bookings",
        json={
            "amenity_id": amenity.id,
            "flat_id": flat.id,
            "slot_id": slot.id,
            "booking_date": booking_date,
            "guest_count": 2,
        },
        headers=resident_headers,
    )
    if book_res.status_code == 201:
        booking_id = book_res.json()["id"]

        # 2. Fetch my bookings
        my_res = resident_client.get("/api/v1/amenities/my-bookings", headers=resident_headers)
        assert my_res.status_code == 200
        my_list = my_res.json()
        assert any(b["id"] == booking_id for b in my_list)

        # 3. Cancel booking
        cancel_res = resident_client.post(
            f"/api/v1/amenities/bookings/{booking_id}/cancel",
            json={"reason": "Change of plans"},
            headers=resident_headers,
        )
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"


def test_billing_service_operations():
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T21-1601").first()
    assert flat is not None

    # Test duplicate bill prevention (month 99, year 2026)
    month = 11
    year = 2028

    # Remove dependent rows before the parent bill (PostgreSQL FK enforcement).
    existing_bill_ids = db.query(Bill.id).filter(
        Bill.flat_id == flat.id,
        Bill.period_month == month,
        Bill.period_year == year,
    )
    db.query(BillLine).filter(BillLine.bill_id.in_(existing_bill_ids)).delete(synchronize_session=False)
    db.query(Bill).filter(Bill.flat_id == flat.id, Bill.period_month == month, Bill.period_year == year).delete()
    db.commit()

    bill = generate_flat_bill(db, flat.id, period_month=month, period_year=year)
    assert bill is not None
    assert bill.principal_amount > 0

    # Generating again should raise HTTPException 409
    with pytest.raises(HTTPException) as exc_info:
        generate_flat_bill(db, flat.id, period_month=month, period_year=year)
    assert exc_info.value.status_code == 409

    # Clean dependent lines before deleting the generated bill.
    db.query(BillLine).filter(BillLine.bill_id == bill.id).delete(synchronize_session=False)
    db.query(Bill).filter(Bill.id == bill.id).delete()
    db.commit()
    db.close()
