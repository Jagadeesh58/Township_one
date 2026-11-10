import uuid
from datetime import time, timedelta

from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import (
    Amenity,
    AmenityBooking,
    AmenitySlot,
    Flat,
    OTPChallenge,
)
from backend.app.services.amenity_service import get_effective_now


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


def test_list_amenities_and_daily_slots():
    client, headers = get_auth_client("9876543210")  # Neeraj

    # 1. List amenities
    res = client.get("/api/v1/amenities", headers=headers)
    assert res.status_code == 200
    amenities = res.json()
    assert len(amenities) >= 6
    names = [a["name"] for a in amenities]
    assert "Clubhouse Banquet Hall" in names
    assert "Tennis Court" in names

    # 2. Get slots for Clubhouse Banquet Hall
    hall = next(a for a in amenities if a["name"] == "Clubhouse Banquet Hall")
    eff_date = get_effective_now().date()
    slots_res = client.get(f"/api/v1/amenities/{hall['id']}/slots?target_date={eff_date.isoformat()}", headers=headers)
    assert slots_res.status_code == 200
    slots = slots_res.json()
    assert len(slots) >= 12  # 08:00 to 20:00 (1-hour slots)
    for slot in slots:
        assert slot["capacity"] == hall["capacity"]
        assert slot["available_spots"] >= 0


def test_book_amenity_slot_success_and_idempotency():
    client, headers = get_auth_client("9876543210")  # Neeraj (T07-1203)

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    hall = db.query(Amenity).filter(Amenity.name == "Clubhouse Banquet Hall").first()
    eff_date = get_effective_now().date()
    slot = (
        db.query(AmenitySlot)
        .filter(
            AmenitySlot.amenity_id == hall.id,
            AmenitySlot.slot_date == eff_date,
            AmenitySlot.start_time == time(10, 0),
        )
        .first()
    )
    slot_id = slot.id
    flat_id = flat.id
    db.close()

    idempotency_key = f"amenity_idem_{uuid.uuid4().hex}"

    # 1. First booking request -> 201 Created
    b_res = client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert b_res.status_code == 201
    b_data = b_res.json()
    booking_id = b_data["id"]
    assert b_data["status"] == "CONFIRMED"
    assert b_data["fee"] == "1200.00"
    assert b_data["fee_status"] == "PAID_TEST"

    # 2. Duplicate booking request with identical idempotency key -> returns existing booking
    dup_res = client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": idempotency_key,
        },
        headers=headers,
    )
    assert dup_res.status_code in (200, 201)
    dup_data = dup_res.json()
    assert dup_data["id"] == booking_id
    assert dup_data["idempotency_key"] == idempotency_key


def test_capacity_limit_and_slot_exhaustion():
    db = SessionLocal()
    hall = db.query(Amenity).filter(Amenity.name == "Clubhouse Banquet Hall").first()
    eff_date = get_effective_now().date() + timedelta(days=2)

    # Create dedicated slot with capacity 1 for strict exhaustion test
    tight_slot = AmenitySlot(
        amenity_id=hall.id,
        slot_date=eff_date,
        start_time=time(14, 0),
        end_time=time(15, 0),
        capacity=1,
        booked_count=1,  # Already full
    )
    db.add(tight_slot)
    db.commit()
    slot_id = tight_slot.id

    flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    flat_id = flat_swati.id
    db.close()

    swati_client, swati_headers = get_auth_client("9876543211")  # Swati

    # Attempt to book fully booked slot -> 409 Conflict
    res = swati_client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": f"idem_full_{uuid.uuid4().hex}",
        },
        headers=swati_headers,
    )
    assert res.status_code == 409
    err_msg = (res.json().get("error", {}).get("message") or res.json().get("detail", "")).lower()
    assert "fully booked" in err_msg


def test_flat_daily_booking_limit_enforced():
    client, headers = get_auth_client("9876543210")  # Neeraj (T07-1203)

    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    court = db.query(Amenity).filter(Amenity.name == "Tennis Court").first()
    eff_date = get_effective_now().date() + timedelta(days=1)

    slots = (
        db.query(AmenitySlot)
        .filter(
            AmenitySlot.amenity_id == court.id,
            AmenitySlot.slot_date == eff_date,
        )
        .order_by(AmenitySlot.start_time.asc())
        .limit(2)
        .all()
    )
    slot1_id = slots[0].id
    slot2_id = slots[1].id
    flat_id = flat.id
    db.close()

    # Book slot 1 -> succeeds
    res1 = client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot1_id,
            "idempotency_key": f"idem_limit_1_{uuid.uuid4().hex}",
        },
        headers=headers,
    )
    assert res1.status_code == 201

    # Book slot 2 on same day for same flat -> 409 Conflict (daily limit reached)
    res2 = client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot2_id,
            "idempotency_key": f"idem_limit_2_{uuid.uuid4().hex}",
        },
        headers=headers,
    )
    assert res2.status_code == 409
    err_msg = (res2.json().get("error", {}).get("message") or res2.json().get("detail", "")).lower()
    assert "flat limit reached" in err_msg


def test_cancellation_workflow_and_unauthorized_cancellation_blocked():
    neeraj_client, neeraj_headers = get_auth_client("9876543210")  # Neeraj
    swati_client, swati_headers = get_auth_client("9876543211")  # Swati

    db = SessionLocal()
    flat_neeraj = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    court = db.query(Amenity).filter(Amenity.name == "Tennis Court").first()
    eff_date = get_effective_now().date() + timedelta(days=3)

    slot = (
        db.query(AmenitySlot)
        .filter(
            AmenitySlot.amenity_id == court.id,
            AmenitySlot.slot_date == eff_date,
            AmenitySlot.start_time == time(16, 0),
        )
        .first()
    )
    slot_id = slot.id
    flat_id = flat_neeraj.id
    db.close()

    # 1. Neeraj books slot
    book_res = neeraj_client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": f"idem_cancel_{uuid.uuid4().hex}",
        },
        headers=neeraj_headers,
    )
    assert book_res.status_code == 201
    booking_id = book_res.json()["id"]

    # 2. Swati attempts to cancel Neeraj's booking -> 403 Forbidden
    unauth_cancel = swati_client.post(
        f"/api/v1/amenities/bookings/{booking_id}/cancel",
        headers=swati_headers,
    )
    assert unauth_cancel.status_code == 403

    # 3. Neeraj cancels his own booking -> succeeds
    cancel_res = neeraj_client.post(
        f"/api/v1/amenities/bookings/{booking_id}/cancel",
        headers=neeraj_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
    assert cancel_res.json()["fee_status"] == "CANCELLED"


def test_amenity_closure_workflow_blocks_new_bookings_and_cancels_conflicts():
    helpdesk_client, helpdesk_headers = get_auth_client("9876543220")  # Help Desk (Ramesh)
    neeraj_client, neeraj_headers = get_auth_client("9876543210")  # Neeraj

    db = SessionLocal()
    court = db.query(Amenity).filter(Amenity.name == "Tennis Court").first()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    closure_date = get_effective_now().date() + timedelta(days=4)

    slot = (
        db.query(AmenitySlot)
        .filter(
            AmenitySlot.amenity_id == court.id,
            AmenitySlot.slot_date == closure_date,
            AmenitySlot.start_time == time(18, 0),
        )
        .first()
    )
    slot_id = slot.id
    flat_id = flat.id
    court_id = court.id
    db.close()

    # 1. Resident books slot on closure_date
    book_res = neeraj_client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": f"idem_closure_pre_{uuid.uuid4().hex}",
        },
        headers=neeraj_headers,
    )
    assert book_res.status_code == 201
    booking_id = book_res.json()["id"]

    # 2. Resident cannot create amenity closure -> 403 Forbidden
    res_closure_fail = neeraj_client.post(
        "/api/v1/amenities/closures",
        json={
            "amenity_id": court_id,
            "start_date": closure_date.isoformat(),
            "end_date": closure_date.isoformat(),
            "reason": "Unauthorized resident attempt",
        },
        headers=neeraj_headers,
    )
    assert res_closure_fail.status_code == 403

    # 3. Help Desk creates closure -> 201 Created and cancels conflicting booking
    closure_res = helpdesk_client.post(
        "/api/v1/amenities/closures",
        json={
            "amenity_id": court_id,
            "start_date": closure_date.isoformat(),
            "end_date": closure_date.isoformat(),
            "reason": "Court resurfacing and line painting",
        },
        headers=helpdesk_headers,
    )
    assert closure_res.status_code == 201

    # Verify existing booking was cancelled
    db = SessionLocal()
    b_check = db.query(AmenityBooking).filter(AmenityBooking.id == booking_id).first()
    assert b_check.status == "CANCELLED"
    db.close()

    # 4. Attempting to book any slot on that court during closure -> 409 Conflict
    blocked_book = neeraj_client.post(
        "/api/v1/amenities/bookings",
        json={
            "flat_id": flat_id,
            "slot_id": slot_id,
            "idempotency_key": f"idem_during_closure_{uuid.uuid4().hex}",
        },
        headers=neeraj_headers,
    )
    assert blocked_book.status_code == 409
    err_msg = (blocked_book.json().get("error", {}).get("message") or blocked_book.json().get("detail", "")).lower()
    assert "closed" in err_msg


def test_rules_booking_lists_and_closed_slot_visibility():
    resident_client, resident_headers = get_auth_client("9876543210")
    guard_client, guard_headers = get_auth_client("9876543230")
    committee_client, committee_headers = get_auth_client("9876543250")

    default_rules = resident_client.get("/api/v1/amenities/nonexistent-amenity/rules", headers=resident_headers)
    assert default_rules.status_code == 200
    assert default_rules.json()["booking_window_days"] == 7
    assert default_rules.json()["max_daily_slots_per_flat"] == 1

    empty_guard_list = guard_client.get("/api/v1/amenities/bookings", headers=guard_headers)
    assert empty_guard_list.status_code == 200
    assert empty_guard_list.json() == []

    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        hall = db.query(Amenity).filter(Amenity.name == "Clubhouse Banquet Hall").first()
        assert flat is not None and hall is not None
        slot = (
            db.query(AmenitySlot)
            .filter(
                AmenitySlot.amenity_id == hall.id,
                AmenitySlot.slot_date == get_effective_now().date() + timedelta(days=5),
            )
            .first()
        )
        assert slot is not None
        slot_id = slot.id
        flat_id = flat.id
    finally:
        db.close()

    booking_response = resident_client.post(
        "/api/v1/amenities/bookings",
        json={"flat_id": flat_id, "slot_id": slot_id, "idempotency_key": f"list-{uuid.uuid4().hex}"},
        headers=resident_headers,
    )
    assert booking_response.status_code == 201
    booking_id = booking_response.json()["id"]

    resident_list = resident_client.get("/api/v1/amenities/bookings", headers=resident_headers)
    assert resident_list.status_code == 200
    assert any(item["id"] == booking_id for item in resident_list.json())

    committee_list = committee_client.get(f"/api/v1/amenities/bookings?flat_id={flat_id}", headers=committee_headers)
    assert committee_list.status_code == 200
    assert any(item["id"] == booking_id for item in committee_list.json())

    closure_response = committee_client.post(
        "/api/v1/amenities/closures",
        json={
            "amenity_id": hall.id,
            "start_date": slot.slot_date.isoformat(),
            "end_date": slot.slot_date.isoformat(),
            "reason": "Scheduled safety inspection",
        },
        headers=committee_headers,
    )
    assert closure_response.status_code == 201
    slots_response = resident_client.get(
        f"/api/v1/amenities/{hall.id}/slots?target_date={slot.slot_date.isoformat()}",
        headers=resident_headers,
    )
    assert slots_response.status_code == 200
    assert all(item["is_closed"] is True for item in slots_response.json())
