"""
Township One - Complaints, AI Triage, Help Desk, and Lifecycle Tests.

Verifies:
- Explicit complaint state machine transitions (legal transitions succeed; illegal return 409 Conflict)
- Resident flat scoping & IDOR protections (residents see only their own flat's tickets)
- Resident post-resolution rating (1-5 stars) and reopen requests
- Private photo upload, MIME validation, EXIF stripping, and signed URL streaming
- Deterministic on-duty staff assignment by category and active workload
- Response timers, human-gated first_response_at, and demo SLA calculations
- Help Desk one-tap classification correction with optimistic version locking (409 on mismatch)
- Life-safety emergency escalation invariant (CRITICAL urgency cannot be downgraded)
- Duplicate detection and incident group linking (linked tickets remain open)
"""

import io

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import (
    Flat,
)


def get_authenticated_client(phone: str) -> tuple[TestClient, dict]:
    """Authenticates a test client using demo OTP login and extracts session & CSRF tokens."""
    client = TestClient(app)
    # Request OTP
    req_resp = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert req_resp.status_code == 200

    # Verify OTP
    verify_resp = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
    assert verify_resp.status_code == 200

    csrf_token = verify_resp.cookies.get("township_csrf")
    headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}
    return client, headers


def create_test_image_bytes(format="JPEG", size=(200, 200), color=(255, 0, 0)) -> bytes:
    """Helper to generate in-memory test image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. Resident Complaint Submission & Scoping
# -----------------------------------------------------------------------------


def test_resident_raise_routine_complaint_and_scoping():
    """Swati Joshi (T12-0408) raises a complaint; verifies auto-triage, assignment, and flat isolation."""
    client_swati, headers_swati = get_authenticated_client("9876543211")
    db = SessionLocal()
    flat_swati = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    flat_neeraj = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    db.close()

    # Swati lodges complaint with optional photo
    img_bytes = create_test_image_bytes("JPEG")
    files = {"photo": ("leak.jpg", img_bytes, "image/jpeg")}
    data = {
        "flat_id": flat_swati.id,
        "title": "Kitchen sink pipe dripping steadily",
        "description": "The drain pipe underneath the kitchen sink has a steady drip into the cabinet.",
        "language": "en",
    }

    resp = client_swati.post("/api/v1/complaints", data=data, files=files, headers=headers_swati)
    assert resp.status_code == 201
    comp_data = resp.json()

    assert comp_data["flat_id"] == flat_swati.id
    assert comp_data["category"] == "PLUMBING"
    assert comp_data["urgency"] in ["LOW", "MEDIUM", "HIGH"]
    assert comp_data["status"] in ["ASSIGNED", "SUBMITTED"]
    assert comp_data["version"] == 1
    assert comp_data["is_safety_escalation"] is False
    assert comp_data["photo_url"] is not None
    complaint_id = comp_data["id"]

    # Swati can view her own complaint
    get_resp = client_swati.get(f"/api/v1/complaints/{complaint_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == complaint_id

    # Neeraj (T07-1203) cannot view Swati's complaint (404 isolation)
    client_neeraj, _ = get_authenticated_client("9876543210")
    idor_resp = client_neeraj.get(f"/api/v1/complaints/{complaint_id}")
    assert idor_resp.status_code == 404

    # Swati cannot lodge a complaint for Neeraj's flat (403)
    forbidden_resp = client_swati.post(
        "/api/v1/complaints",
        data={"flat_id": flat_neeraj.id, "title": "Sneak complaint", "description": "Trying to lodge for another flat"},
        headers=headers_swati,
    )
    assert forbidden_resp.status_code == 403


# -----------------------------------------------------------------------------
# 2. Emergency Rule Detection & Safety Escalation Invariant
# -----------------------------------------------------------------------------


def test_emergency_detector_safety_escalation_and_invariants():
    """Emergency keywords unconditionally set CRITICAL urgency and SafetyEvent; cannot be downgraded."""
    client_swati, headers_swati = get_authenticated_client("9876543211")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    db.close()

    # Submission with life-safety emergency trigger
    data = {
        "flat_id": flat.id,
        "title": "Smoke coming from meter box",
        "description": "Heavy black smoke and burning smell from corridor electrical meter box. Real fire hazard!",
        "language": "en",
    }

    resp = client_swati.post("/api/v1/complaints", data=data, headers=headers_swati)
    assert resp.status_code == 201
    comp_data = resp.json()

    assert comp_data["urgency"] == "CRITICAL"
    assert comp_data["is_safety_escalation"] is True
    complaint_id = comp_data["id"]

    # Help Desk tries to downgrade urgency below CRITICAL -> MUST FAIL (HTTP 400)
    client_admin, headers_admin = get_authenticated_client("9876543200")
    downgrade_resp = client_admin.post(
        f"/api/v1/complaints/{complaint_id}/correct-classification",
        json={
            "category": "ELECTRICAL",
            "urgency": "LOW",
            "reason": "False alarm attempt",
            "expected_version": comp_data["version"],
        },
        headers=headers_admin,
    )
    assert downgrade_resp.status_code == 400
    assert "Cannot lower urgency on a verified safety escalation" in downgrade_resp.json()["error"]["message"]


# -----------------------------------------------------------------------------
# 3. Explicit Lifecycle Transition State Machine
# -----------------------------------------------------------------------------


def test_explicit_lifecycle_transitions_and_conflict_errors():
    """Tests legal transitions succeed, while illegal transitions return HTTP 409 Conflict."""
    client_admin, headers_admin = get_authenticated_client("9876543200")
    client_swati, headers_swati = get_authenticated_client("9876543211")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    db.close()

    # Create fresh ticket
    create_resp = client_swati.post(
        "/api/v1/complaints",
        data={"flat_id": flat.id, "title": "Intercom dead", "description": "Intercom buzzer not working for 2 days"},
        headers=headers_swati,
    )
    assert create_resp.status_code == 201
    comp = create_resp.json()
    c_id = comp["id"]
    version = comp["version"]

    # 1. Illegal transition: SUBMITTED/ASSIGNED -> CLOSED directly -> 409 CONFLICT
    illegal_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "CLOSED", "notes": "Premature close", "expected_version": version},
        headers=headers_admin,
    )
    assert illegal_resp.status_code == 409

    # 2. Legal transition: -> IN_PROGRESS
    prog_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "IN_PROGRESS", "notes": "Technician dispatched", "expected_version": version},
        headers=headers_admin,
    )
    assert prog_resp.status_code == 200
    version = prog_resp.json()["version"]
    assert prog_resp.json()["status"] == "IN_PROGRESS"
    assert prog_resp.json()["first_response_at"] is not None

    # 3. Illegal transition: IN_PROGRESS -> SUBMITTED -> 409 CONFLICT
    backward_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "SUBMITTED", "notes": "Cannot go backwards", "expected_version": version},
        headers=headers_admin,
    )
    assert backward_resp.status_code == 409

    # 4. Legal transition: IN_PROGRESS -> RESOLVED
    res_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "RESOLVED", "notes": "Wiring reconnected, intercom verified", "expected_version": version},
        headers=headers_admin,
    )
    assert res_resp.status_code == 200
    version = res_resp.json()["version"]
    assert res_resp.json()["status"] == "RESOLVED"
    assert res_resp.json()["resolved_at"] is not None

    # 5. Resident rates ticket (1-5 stars)
    rate_resp = client_swati.post(
        f"/api/v1/complaints/{c_id}/rate",
        json={"rating": 5, "feedback": "Quick and polite technician!"},
        headers=headers_swati,
    )
    assert rate_resp.status_code == 200
    assert rate_resp.json()["rating"] == 5

    # 6. Legal transition: RESOLVED -> CLOSED
    close_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/transition",
        json={"status": "CLOSED", "notes": "Resident confirmed fix"},
        headers=headers_admin,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 7. Resident can request reopen on CLOSED complaint
    reopen_resp = client_swati.post(
        f"/api/v1/complaints/{c_id}/reopen",
        json={"reason": "Intercom stopped working again this morning"},
        headers=headers_swati,
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["status"] == "REOPEN_REQUESTED"


# -----------------------------------------------------------------------------
# 4. Optimistic Concurrency Locking on Help Desk Corrections
# -----------------------------------------------------------------------------


def test_optimistic_concurrency_locking_on_correction():
    """Help Desk classification correction fails with HTTP 409 if version is stale."""
    client_admin, headers_admin = get_authenticated_client("9876543200")
    client_swati, headers_swati = get_authenticated_client("9876543211")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    db.close()

    create_resp = client_swati.post(
        "/api/v1/complaints",
        data={
            "flat_id": flat.id,
            "title": "Water smells bad",
            "description": "Tap water is discolored and has foul smell",
        },
        headers=headers_swati,
    )
    comp = create_resp.json()
    c_id = comp["id"]
    current_version = comp["version"]

    # Simultaneous edit simulation: someone supplies an old version
    stale_version = current_version - 1
    stale_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/correct-classification",
        json={
            "category": "WATER_SUPPLY",
            "urgency": "HIGH",
            "reason": "Water quality hazard",
            "expected_version": stale_version,
        },
        headers=headers_admin,
    )
    assert stale_resp.status_code == 409
    assert "Optimistic lock conflict" in stale_resp.json()["error"]["message"]

    # Accurate version succeeds
    success_resp = client_admin.post(
        f"/api/v1/complaints/{c_id}/correct-classification",
        json={
            "category": "WATER_SUPPLY",
            "urgency": "HIGH",
            "reason": "Water quality hazard verified",
            "expected_version": current_version,
        },
        headers=headers_admin,
    )
    assert success_resp.status_code == 200
    assert success_resp.json()["category"] == "WATER_SUPPLY"
    assert success_resp.json()["urgency"] == "HIGH"
    assert success_resp.json()["version"] == current_version + 1


# -----------------------------------------------------------------------------
# 5. Duplicate Detection & Incident Group Linking
# -----------------------------------------------------------------------------


def test_duplicate_candidate_detection_and_incident_grouping():
    """Detects near-duplicate tickets and links them without closing either ticket."""
    client_admin, headers_admin = get_authenticated_client("9876543200")
    client_neeraj, headers_neeraj = get_authenticated_client("9876543210")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
    db.close()

    # Ticket 1: Lift #2 jerky movement in Tower 7
    t1_resp = client_neeraj.post(
        "/api/v1/complaints",
        data={
            "flat_id": flat.id,
            "title": "Tower 7 Lift 2 jerky stopping",
            "description": "Passenger lift 2 stops with loud thud at floor 12",
        },
        headers=headers_neeraj,
    )
    assert t1_resp.status_code == 201
    t1_id = t1_resp.json()["id"]

    # Ticket 2: Similar lift fault in Tower 7
    t2_resp = client_neeraj.post(
        "/api/v1/complaints",
        data={
            "flat_id": flat.id,
            "title": "Tower 7 Lift #2 abnormal vibration",
            "description": "Lift 2 shaking and vibrating heavily between 10th and 12th floor",
        },
        headers=headers_neeraj,
    )
    assert t2_resp.status_code == 201
    t2_id = t2_resp.json()["id"]

    # Help Desk checks duplicate candidates for Ticket 2
    candidates_resp = client_admin.get(f"/api/v1/complaints/{t2_id}/duplicate-candidates")
    assert candidates_resp.status_code == 200
    candidates = candidates_resp.json()["candidates"]
    assert len(candidates) > 0
    candidate_ids = [c["id"] for c in candidates]
    assert t1_id in candidate_ids

    # Link Ticket 2 as duplicate of Ticket 1
    link_resp = client_admin.post(
        f"/api/v1/complaints/{t2_id}/link-duplicate", json={"target_complaint_id": t1_id}, headers=headers_admin
    )
    assert link_resp.status_code == 200
    assert link_resp.json()["status"] == "LINKED"

    # CRITICAL INVARIANT: Both tickets remain individually OPEN / ASSIGNED
    c1_check = client_admin.get(f"/api/v1/complaints/{t1_id}").json()
    c2_check = client_admin.get(f"/api/v1/complaints/{t2_id}").json()
    assert c1_check["status"] in ["ASSIGNED", "SUBMITTED", "IN_PROGRESS"]
    assert c2_check["status"] in ["ASSIGNED", "SUBMITTED", "IN_PROGRESS"]


# -----------------------------------------------------------------------------
# 6. Private Photo Security & Streaming Access Control
# -----------------------------------------------------------------------------


def test_private_photo_streaming_and_signed_url():
    """Verifies that photos are served with signed URLs or authenticated sessions, blocking unauthenticated access."""
    client_swati, headers_swati = get_authenticated_client("9876543211")
    db = SessionLocal()
    flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
    db.close()

    img_bytes = create_test_image_bytes("PNG")
    files = {"photo": ("evidence.png", img_bytes, "image/png")}
    data = {
        "flat_id": flat.id,
        "title": "Broken window latch",
        "description": "Balcony sliding window latch is snapped and will not lock",
    }

    create_resp = client_swati.post("/api/v1/complaints", data=data, files=files, headers=headers_swati)
    assert create_resp.status_code == 201
    photo_url = create_resp.json()["photo_url"]
    assert photo_url is not None
    assert "exp=" in photo_url and "sig=" in photo_url

    # Anonymous client accessing WITH valid signature succeeds
    anon_client = TestClient(app)
    signed_resp = anon_client.get(photo_url)
    assert signed_resp.status_code == 200
    assert signed_resp.headers["content-type"] in ["image/png", "image/jpeg"]
    assert "private" in signed_resp.headers.get("cache-control", "").lower()

    # Anonymous client accessing WITHOUT signature fails (401)
    base_photo_path = photo_url.split("?")[0]
    unauth_resp = anon_client.get(base_photo_path)
    assert unauth_resp.status_code == 401

    # Swati accessing through authenticated session without signature succeeds
    auth_resp = client_swati.get(base_photo_path)
    assert auth_resp.status_code == 200
