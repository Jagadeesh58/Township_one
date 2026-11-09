"""
Township One - Bank Statement Import & Matching API Endpoints.

Provides:
- Statement CSV Preview (dry run, non-mutating)
- Statement CSV Commit (idempotent, atomic ledger posting)
- Review Queue & Human-in-the-Loop Actions (APPROVE, REJECT, HOLD, CORRECT_MAPPING)
- Import History and Bank Account listings
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import require_role, verify_csrf
from backend.app.models.entities import AuditEvent, BankAccount, BankImportFile, BankRow, Flat, User
from backend.app.schemas.bank import (
    BankAccountResponse,
    BankImportCommitResponse,
    BankImportPreviewResponse,
    BankRowPreviewItem,
    BankRowResponse,
    ReviewActionRequest,
)
from backend.app.services.bank_matching import commit_bank_statement, handle_review_action, preview_bank_statement

router = APIRouter(prefix="/bank", tags=["Bank Statement Matching"])


def to_row_response(row: BankRow, db: Session) -> BankRowResponse:
    flat_num: str | None = None
    if row.matched_flat_id:
        f = db.query(Flat).filter(Flat.id == row.matched_flat_id).first()
        if f:
            flat_num = f.flat_number

    return BankRowResponse(
        id=row.id,
        import_file_id=row.import_file_id,
        original_row_number=row.original_row_number,
        txn_date=row.txn_date,
        value_date=row.value_date,
        narration=row.narration,
        direction=row.direction,
        amount=Decimal(str(row.amount)) if row.amount is not None else None,
        currency=row.currency or "INR",
        utr=row.utr,
        payer_upi=row.payer_upi,
        flat_ref=row.flat_ref,
        decision=row.decision,
        decision_reason=row.decision_reason,
        review_status=row.review_status,
        matched_flat_id=row.matched_flat_id,
        matched_flat_number=flat_num,
        matched_bill_id=row.matched_bill_id,
        matched_payment_id=row.matched_payment_id,
        correction_reason=row.correction_reason,
        raw_row=row.raw_row,
        audit_trail=row.audit_trail,
    )


@router.get("/accounts", response_model=list[BankAccountResponse])
def list_bank_accounts(
    current_user: User = Depends(require_role(["ACCOUNTS", "COMMITTEE", "ADMIN"])), db: Session = Depends(get_db)
):
    """Lists registered active bank accounts for township maintenance collections."""
    accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
    return accounts


@router.post("/imports/preview", response_model=BankImportPreviewResponse)
async def preview_statement(
    file: UploadFile = File(...),
    account_no: str | None = Form(None),
    current_user: User = Depends(require_role(["ACCOUNTS", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    Non-mutating statement preview.
    Validates CSV columns, formats, positive amounts, recognized account, and returns
    proposed matching decisions without modifying the database.
    """
    try:
        content = await file.read()
        res = preview_bank_statement(
            db=db, content=content, filename=file.filename or "statement.csv", bank_account_no=account_no
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Statement preview failed: {str(e)}")

    preview_items = []
    auto_match_count = 0
    review_count = 0
    duplicate_count = 0

    for r in res["rows"]:
        cand_dec = r.get("candidate_decision")
        if cand_dec == "AUTO_MATCH":
            auto_match_count += 1
        elif cand_dec == "DUPLICATE_NO_OP":
            duplicate_count += 1
        elif cand_dec in ["REVIEW", "INVALID"]:
            review_count += 1

        amt_val = None
        if r.get("amount"):
            try:
                amt_val = Decimal(str(r["amount"]))
            except Exception:
                amt_val = None

        preview_items.append(
            BankRowPreviewItem(
                original_row_number=r["row_number"],
                txn_date=r.get("txn_date"),
                value_date=r.get("value_date"),
                narration=r.get("narration"),
                direction=r.get("direction"),
                amount=amt_val,
                currency=r.get("currency") or "INR",
                utr=r.get("utr"),
                payer_upi=r.get("payer_upi"),
                flat_ref=r.get("flat_ref"),
                decision=r.get("candidate_decision"),
                decision_reason=r.get("candidate_reason"),
                parse_status="ACCEPTED" if r.get("is_valid") else "INVALID",
                parse_errors=r.get("errors") or None,
                matched_flat_number=r.get("flat_ref"),
            )
        )

    return BankImportPreviewResponse(
        file_sha256=res["file_sha256"],
        duplicate_file=res["duplicate_file"],
        total_rows=res["total_rows"],
        accepted_rows=res["accepted_rows"],
        invalid_rows=res["invalid_rows"],
        total_credit_amount=Decimal(str(res["total_credit"])),
        total_debit_amount=Decimal(str(res["total_debit"])),
        auto_match_count=auto_match_count,
        review_count=review_count,
        duplicate_count=duplicate_count,
        rows=preview_items,
    )


@router.post("/imports/commit", response_model=BankImportCommitResponse)
async def commit_statement(
    file: UploadFile = File(...),
    account_no: str | None = Form(None),
    current_user: User = Depends(require_role(["ACCOUNTS", "ADMIN"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Idempotent statement commit.
    Saves BankImportFile and BankRows, executes deterministic auto-match postings,
    and returns processing totals.
    """
    try:
        content = await file.read()
        res = commit_bank_statement(
            db=db,
            content=content,
            filename=file.filename or "statement.csv",
            uploaded_by_user_id=current_user.id,
            bank_account_no=account_no,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Statement commit failed: {str(e)}")

    is_duplicate = res.get("status") == "ALREADY_PROCESSED"
    return BankImportCommitResponse(
        import_file_id=res["import_file_id"],
        filename=res["filename"],
        file_sha256=res["file_sha256"],
        total_rows=res["total_rows"],
        accepted_rows=res["accepted_rows"],
        invalid_rows=res["invalid_rows"],
        auto_matched_count=res.get("auto_matched_count", 0),
        review_count=res.get("review_count", 0),
        duplicate_count=res.get("duplicate_count", 0),
        is_duplicate=is_duplicate,
    )


@router.get("/imports")
def list_statement_imports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role(["ACCOUNTS", "COMMITTEE", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """Lists past statement import batches."""
    offset = (page - 1) * page_size
    imports = db.query(BankImportFile).order_by(BankImportFile.uploaded_at.desc()).offset(offset).limit(page_size).all()

    total = db.query(BankImportFile).count()

    items = []
    for imp in imports:
        items.append(
            {
                "id": imp.id,
                "filename": imp.filename,
                "file_sha256": imp.file_sha256,
                "bank_account_id": imp.bank_account_id,
                "uploaded_by_user_id": imp.uploaded_by_user_id,
                "uploaded_at": imp.uploaded_at,
                "total_rows": imp.total_rows,
                "accepted_rows": imp.accepted_rows,
                "invalid_rows": imp.invalid_rows,
            }
        )

    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.get("/imports/{import_id}/rows", response_model=list[BankRowResponse])
def get_import_rows(
    import_id: str,
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(require_role(["ACCOUNTS", "COMMITTEE", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """Retrieves statement rows for a given import batch."""
    q = db.query(BankRow).filter(BankRow.import_file_id == import_id)
    if status_filter:
        q = q.filter(BankRow.review_status == status_filter)

    rows = q.order_by(BankRow.original_row_number.asc()).all()
    return [to_row_response(r, db) for r in rows]


@router.get("/review-queue", response_model=list[BankRowResponse])
def get_review_queue(
    review_status: str = Query("PENDING"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_role(["ACCOUNTS", "COMMITTEE", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """Retrieves bank statement rows awaiting human accounts review."""
    offset = (page - 1) * page_size
    rows = (
        db.query(BankRow)
        .filter(BankRow.decision == "REVIEW", BankRow.review_status == review_status)
        .order_by(BankRow.original_row_number.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return [to_row_response(r, db) for r in rows]


@router.post("/rows/{row_id}/action", response_model=BankRowResponse)
def apply_review_action(
    row_id: str,
    action_req: ReviewActionRequest,
    current_user: User = Depends(require_role(["ACCOUNTS", "ADMIN"])),
    _csrf: None = Depends(verify_csrf),
    db: Session = Depends(get_db),
):
    """
    Applies review decision: APPROVE, REJECT, HOLD, or CORRECT_MAPPING.
    Posts atomically to bill and ledger on APPROVE.
    """
    try:
        updated_row = handle_review_action(
            db=db,
            bank_row_id=row_id,
            action=action_req.action,
            reviewer_user_id=current_user.id,
            target_flat_id=action_req.target_flat_id,
            target_bill_id=action_req.target_bill_id,
            reason=action_req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return to_row_response(updated_row, db)


@router.get("/audit")
def list_bank_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_role(["ACCOUNTS", "COMMITTEE", "ADMIN"])),
    db: Session = Depends(get_db),
):
    """Returns append-only audit trail for statement imports and review decisions."""
    offset = (page - 1) * page_size
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_type == "BANK_ROW")
        .order_by(AuditEvent.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "action": e.action,
            "actor_user_id": e.actor_user_id,
            "actor_role": e.actor_role,
            "created_at": e.created_at,
            "old_state": e.old_state,
            "new_state": e.new_state,
            "reason": e.reason,
        }
        for e in events
    ]
