from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.entities import User
from backend.app.schemas.committee import CommitteeReportResponse
from backend.app.services.committee_service import (
    get_committee_report_data,
    generate_committee_csv,
    generate_committee_pdf,
)

router = APIRouter(prefix="/committee", tags=["committee"])


def verify_committee_access(user: User):
    roles = [r.role_code for r in user.role_assignments]
    if "COMMITTEE" not in roles and "ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Committee dashboard access requires COMMITTEE or ADMIN role."
        )


@router.get("/report", response_model=CommitteeReportResponse)
def get_committee_report(
    period: Optional[str] = Query(None, description="Reporting month (e.g. 2026-11)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_committee_access(current_user)
    report = get_committee_report_data(db, period_str=period)
    return report


@router.get("/report/csv")
def download_committee_report_csv(
    period: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_committee_access(current_user)
    report = get_committee_report_data(db, period_str=period)
    csv_content = generate_committee_csv(report)

    filename = f"township_one_committee_report_{report.reporting_period}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/report/pdf")
def download_committee_report_pdf(
    period: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_committee_access(current_user)
    report = get_committee_report_data(db, period_str=period)
    pdf_bytes = generate_committee_pdf(report)

    filename = f"township_one_committee_report_{report.reporting_period}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
