from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.entities import Notice, NoticeRevision, NoticeRead, Tower, OTPChallenge


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


def test_tower_targeting_scoping():
    neeraj_client, neeraj_headers = get_auth_client("9876543210")  # Neeraj (Tower 7)
    swati_client, swati_headers = get_auth_client("9876543211")    # Swati (Tower 12)

    # 1. Neeraj (Tower 7 resident) sees both global AGM notice and Tower 7 lift notice
    neeraj_res = neeraj_client.get("/api/v1/notices", headers=neeraj_headers)
    assert neeraj_res.status_code == 200
    neeraj_notices = neeraj_res.json()
    neeraj_titles = [n["title"] for n in neeraj_notices]
    assert any("AGM" in t for t in neeraj_titles)
    assert any("Tower 7 Lift" in t for t in neeraj_titles)

    # 2. Swati (Tower 12 resident) sees AGM notice, but does NOT see Tower 7 lift notice
    swati_res = swati_client.get("/api/v1/notices", headers=swati_headers)
    assert swati_res.status_code == 200
    swati_notices = swati_res.json()
    swati_titles = [n["title"] for n in swati_notices]
    assert any("AGM" in t for t in swati_titles)
    assert not any("Tower 7 Lift" in t for t in swati_titles)


def test_notice_multilingual_and_language_fallback():
    client, headers = get_auth_client("9876543210")

    # 1. Fetch notices in Marathi (lang=mr)
    mr_res = client.get("/api/v1/notices?lang=mr", headers=headers)
    assert mr_res.status_code == 200
    notices = mr_res.json()

    # AGM notice has Marathi text -> no fallback
    agm_notice = next(n for n in notices if "AGM" in n["title"])
    assert agm_notice["is_fallback_language"] is False
    assert "वार्षिक सर्वसाधारण सभा" in agm_notice["body"]

    # Tower 7 Lift notice has English only -> fallback to English with label
    lift_notice = next(n for n in notices if "Tower 7 Lift" in n["title"])
    assert lift_notice["is_fallback_language"] is True
    assert lift_notice["fallback_language_label"] == "Shown in English"
    assert "passenger lift #2" in lift_notice["body"]


def test_revision_immutability():
    helpdesk_client, helpdesk_headers = get_auth_client("9876543220")  # Help Desk (Ramesh)

    db = SessionLocal()
    n = db.query(Notice).filter(Notice.title.like("%Tower 7 Lift%")).first()
    notice_id = n.id
    db.close()

    # 1. Help Desk creates revision 2
    rev2_res = helpdesk_client.post(
        f"/api/v1/notices/{notice_id}/revisions",
        json={
            "title": "Tower 7 Lift #2 Maintenance Extended",
            "body_en": "Otis technicians have requested an additional replacement motor. Estimated restoration extended to 9:00 PM.",
            "audience": "TOWER",
            "severity": "CRITICAL",
        },
        headers=helpdesk_headers,
    )
    assert rev2_res.status_code == 201
    assert rev2_res.json()["revision_number"] == 2

    # 2. Verify all revisions are preserved immutably
    history_res = helpdesk_client.get(f"/api/v1/notices/{notice_id}/revisions", headers=helpdesk_headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 2
    assert history[0]["revision_number"] == 2
    assert history[1]["revision_number"] == 1


def test_read_tracking_per_revision():
    client, headers = get_auth_client("9876543210")  # Neeraj

    # 1. Fetch notices and find an unread notice
    notices_res = client.get("/api/v1/notices", headers=headers)
    assert notices_res.status_code == 200
    notices = notices_res.json()
    target_notice = notices[0]
    rev_id = target_notice["id"]
    assert target_notice["is_read"] is False

    # 2. Mark revision as read
    read_res = client.post(f"/api/v1/notices/revisions/{rev_id}/read", headers=headers)
    assert read_res.status_code == 200

    # 3. Subsequent list reflects is_read == True
    updated_res = client.get("/api/v1/notices", headers=headers)
    assert updated_res.status_code == 200
    updated_notices = updated_res.json()
    matching = next(n for n in updated_notices if n["id"] == rev_id)
    assert matching["is_read"] is True


def test_draft_and_withdrawn_notices_hidden_from_residents():
    helpdesk_client, helpdesk_headers = get_auth_client("9876543220")  # Help Desk
    resident_client, resident_headers = get_auth_client("9876543210")  # Resident

    # 1. Help Desk creates a new notice
    create_res = helpdesk_client.post(
        "/api/v1/notices",
        json={
            "title": "Water Tank Cleaning Notice",
            "body_en": "Overhead water tanks will be sanitized between 10:00 AM and 2:00 PM.",
            "audience": "ALL",
            "severity": "NORMAL",
        },
        headers=helpdesk_headers,
    )
    assert create_res.status_code == 201
    notice_id = create_res.json()["id"]

    # 2. Resident can view the notice
    active_res = resident_client.get("/api/v1/notices", headers=resident_headers)
    assert any(n["title"] == "Water Tank Cleaning Notice" for n in active_res.json())

    # 3. Help Desk withdraws the notice
    withdraw_res = helpdesk_client.post(f"/api/v1/notices/{notice_id}/withdraw", headers=helpdesk_headers)
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "WITHDRAWN"

    # 4. Resident no longer sees the withdrawn notice
    after_res = resident_client.get("/api/v1/notices", headers=resident_headers)
    assert not any(n["title"] == "Water Tank Cleaning Notice" for n in after_res.json())

    # 5. Resident cannot create notices -> 403 Forbidden
    unauth_create = resident_client.post(
        "/api/v1/notices",
        json={"title": "Rogue Notice", "body_en": "Unauthorized text", "audience": "ALL"},
        headers=resident_headers,
    )
    assert unauth_create.status_code == 403
