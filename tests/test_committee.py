from decimal import Decimal

from fastapi.testclient import TestClient

from backend.app.core.database import SessionLocal
from backend.app.main import app
from backend.app.models.entities import OTPChallenge


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


def test_committee_dashboard_access_control():
    comm_client, comm_headers = get_auth_client("9876543250")  # Vikram Sardesai (Committee)
    admin_client, admin_headers = get_auth_client("9876543200")  # Admin
    resident_client, resident_headers = get_auth_client("9876543210")  # Resident (Neeraj)
    guard_client, guard_headers = get_auth_client("9876543230")  # Guard (Suresh)

    # 1. Committee member has access
    comm_res = comm_client.get("/api/v1/committee/report", headers=comm_headers)
    assert comm_res.status_code == 200

    # 2. Admin has access
    admin_res = admin_client.get("/api/v1/committee/report", headers=admin_headers)
    assert admin_res.status_code == 200

    # 3. Resident is denied access (403 Forbidden)
    res_res = resident_client.get("/api/v1/committee/report", headers=resident_headers)
    assert res_res.status_code == 403

    # 4. Guard is denied access (403 Forbidden)
    guard_res = guard_client.get("/api/v1/committee/report", headers=guard_headers)
    assert guard_res.status_code == 403


def test_financial_metrics_and_ageing_reconciliation():
    client, headers = get_auth_client("9876543250")  # Committee

    res = client.get("/api/v1/committee/report", headers=headers)
    assert res.status_code == 200
    data = res.json()

    fin = data["financials"]
    total_billed = Decimal(str(fin["total_billed"]))
    total_collected = Decimal(str(fin["total_collected"]))
    total_outstanding = Decimal(str(fin["total_outstanding"]))
    collection_rate = Decimal(str(fin["collection_rate_percent"]))

    # Mathematical consistency
    assert total_collected <= total_billed
    assert Decimal("0.00") <= collection_rate <= Decimal("100.00")

    # Dues ageing bands must sum exactly to total_outstanding
    ageing = fin["ageing"]
    b_0_30 = Decimal(str(ageing["band_0_30_days"]))
    b_31_60 = Decimal(str(ageing["band_31_60_days"]))
    b_61_90 = Decimal(str(ageing["band_61_90_days"]))
    b_90_plus = Decimal(str(ageing["band_90_plus_days"]))

    sum_bands = b_0_30 + b_31_60 + b_61_90 + b_90_plus
    assert sum_bands == total_outstanding


def test_complaints_turnaround_metrics():
    client, headers = get_auth_client("9876543250")  # Committee

    res = client.get("/api/v1/committee/report", headers=headers)
    assert res.status_code == 200
    comp = res.json()["complaints"]

    total = comp["total_complaints"]
    open_unres = comp["open_unresolved_count"]
    closed_res = comp["closed_resolved_count"]

    assert total == open_unres + closed_res
    assert Decimal(str(comp["reopened_rate_percent"])) >= Decimal("0.00")


def test_report_csv_export():
    client, headers = get_auth_client("9876543250")  # Committee

    res = client.get("/api/v1/committee/report/csv", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]

    csv_text = res.text
    assert "Committee Governance" in csv_text
    assert "Total Billed" in csv_text
    assert "Total Outstanding" in csv_text
    assert "Bank Matching" in csv_text
    assert "Client target, not an achieved result" in csv_text


def test_report_pdf_export():
    client, headers = get_auth_client("9876543250")  # Committee

    res = client.get("/api/v1/committee/report/pdf", headers=headers)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert "attachment; filename=" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")
