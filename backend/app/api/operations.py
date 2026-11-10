"""Operational endpoints that are not exposed to resident-facing roles."""

import hmac

from fastapi import APIRouter, Header, HTTPException, status

from backend.app.core.config import settings
from backend.app.services.visitor_service import purge_visitor_photos

router = APIRouter(prefix="/ops", tags=["Operations"])


@router.post("/retention/visitor-photos")
def run_visitor_photo_retention(
    x_retention_job_token: str | None = Header(default=None, alias="X-Retention-Job-Token"),
):
    """Purge visitor photos whose 90-day retention window has elapsed.

    This endpoint is intended for a scheduler such as GitHub Actions. It fails
    closed unless a high-entropy, separately configured job token is present.
    """
    expected = settings.RETENTION_JOB_TOKEN.strip()
    supplied = (x_retention_job_token or "").strip()
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retention job authentication failed.",
        )

    deleted_count = purge_visitor_photos()
    return {"deleted_photos": deleted_count, "retention_days": 90}
