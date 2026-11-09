import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    # Relationships
    role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    flat_memberships = relationship("FlatMembership", back_populates="user", cascade="all, delete-orphan")
    staff_profile = relationship("StaffMember", back_populates="user", uselist=False)
    complaints = relationship("Complaint", back_populates="user")
    uploaded_bank_files = relationship("BankImportFile", back_populates="uploaded_by")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # RESIDENT, HELPDESK, GUARD, ACCOUNTS, COMMITTEE, ADMIN
    scope_type: Mapped[str | None] = mapped_column(
        String(30), default="TOWNSHIP", nullable=True
    )  # TOWNSHIP, TOWER, FLAT, GATE
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    user = relationship("User", back_populates="role_assignments")


class RevokedToken(Base):
    """Persistent token revocation store for multi-worker session security."""

    __tablename__ = "revoked_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    token_jti: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Tower(Base):
    __tablename__ = "towers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)  # T01 .. T28
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    total_floors: Mapped[int | None] = mapped_column(Integer, default=20, nullable=True)
    flats_per_floor: Mapped[int | None] = mapped_column(Integer, default=4, nullable=True)

    flats = relationship("Flat", back_populates="tower")
    complaints = relationship("Complaint", back_populates="tower")
    incident_groups = relationship("IncidentGroup", back_populates="tower")


class Flat(Base):
    __tablename__ = "flats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    tower_id: Mapped[str] = mapped_column(String(36), ForeignKey("towers.id"), nullable=False)
    flat_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g. T07-1203
    floor_number: Mapped[int] = mapped_column(Integer, nullable=False)
    area_sqft: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # e.g. 1150.00
    bhk_type: Mapped[str | None] = mapped_column(String(10), default="3 BHK", nullable=True)

    tower = relationship("Tower", back_populates="flats")
    memberships = relationship("FlatMembership", back_populates="flat")
    bills = relationship("Bill", back_populates="flat")
    ledger_entries = relationship("FlatLedgerEntry", back_populates="flat")
    complaints = relationship("Complaint", back_populates="flat")
    registered_upis = relationship("RegisteredUPI", back_populates="flat")


class FlatMembership(Base):
    __tablename__ = "flat_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    member_type: Mapped[str] = mapped_column(String(20), nullable=False)  # OWNER, TENANT, FAMILY
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    can_pay_bills: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    can_approve_visitors: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    can_raise_complaints: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    flat = relationship("Flat", back_populates="memberships")
    user = relationship("User", back_populates="flat_memberships")


class StaffMember(Base):
    __tablename__ = "staff_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    staff_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[str] = mapped_column(String(50), nullable=False)
    department: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # Plumbing, Electrical, Security, Housekeeping, Accounts, Operations
    shift: Mapped[str | None] = mapped_column(String(20), default="Morning", nullable=True)  # Morning, Evening, Night
    is_available: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)

    user = relationship("User", back_populates="staff_profile")
    complaints = relationship("Complaint", back_populates="assigned_staff")
    shifts = relationship("StaffShift", back_populates="staff")


class Gate(Base):
    __tablename__ = "gates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    gate_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)  # 1, 2, 3, 4
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # Main North Gate, South Gate, etc.
    location_description: Mapped[str | None] = mapped_column(String(100), nullable=True)


class BillingRule(Base):
    __tablename__ = "billing_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_per_sqft: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("6.50"))
    due_day_of_month: Mapped[int | None] = mapped_column(Integer, default=15, nullable=True)
    grace_period_days: Mapped[int | None] = mapped_column(Integer, default=5, nullable=True)
    late_fee_percentage_pa: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), default=Decimal("18.00"), nullable=True
    )  # Illustrative demo rule
    version: Mapped[str | None] = mapped_column(String(20), default="v1.0-demo", nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True, nullable=True)


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (UniqueConstraint("flat_id", "period_month", "period_year", name="uq_flat_bill_period"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    billing_rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("billing_rules.id"), nullable=True)
    billing_rule_version: Mapped[str] = mapped_column(String(50), default="v1.0-demo", nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    area_sqft: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rate_per_sqft: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    late_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=True)
    balance_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str | None] = mapped_column(
        String(20), default="ISSUED", nullable=True
    )  # ISSUED, PARTIALLY_PAID, PAID, OVERDUE

    flat = relationship("Flat", back_populates="bills")
    lines = relationship("BillLine", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")
    matched_bank_rows = relationship("BankRow", back_populates="matched_bill")


class BillLine(Base):
    __tablename__ = "bill_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    bill_id: Mapped[str] = mapped_column(String(36), ForeignKey("bills.id"), nullable=False)
    line_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PRINCIPAL, LATE_FEE, ADJUSTMENT
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    bill = relationship("Bill", back_populates="lines")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_transaction_reference", "transaction_reference", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    bill_id: Mapped[str] = mapped_column(String(36), ForeignKey("bills.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    payment_method: Mapped[str | None] = mapped_column(
        String(30), default="TEST_PAYMENT", nullable=True
    )  # TEST_PAYMENT, BANK_TRANSFER, UPI, CHEQUE
    status: Mapped[str | None] = mapped_column(
        String(20), default="SUCCESS", nullable=True
    )  # PENDING, SUCCESS, FAILED, EXPIRED, REFUNDED
    transaction_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    payer_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    bill = relationship("Bill", back_populates="payments")
    receipt = relationship("Receipt", back_populates="payment", uselist=False, cascade="all, delete-orphan")
    matched_bank_rows = relationship("BankRow", back_populates="matched_payment")


class PaymentIdempotencyRecord(Base):
    __tablename__ = "payment_idempotency_records"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    bill_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bills.id"), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), default="INR", nullable=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED", nullable=False)
    payment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("payments.id"), nullable=True)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)


class FlatLedgerEntry(Base):
    __tablename__ = "flat_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)  # INVOICE, PAYMENT, REVERSAL, CREDIT_NOTE
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Bill ID, Payment ID, Bank Row ID
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    flat = relationship("Flat", back_populates="ledger_entries")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id"), nullable=False, unique=True)
    receipt_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    flat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    resident_name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    transaction_reference: Mapped[str] = mapped_column(String(50), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    payment = relationship("Payment", back_populates="receipt")


# --- Bank Statement Matching Models ---


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    account_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ifsc_code: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    import_files = relationship("BankImportFile", back_populates="bank_account")
    rows = relationship("BankRow", back_populates="bank_account")


class BankImportFile(Base):
    __tablename__ = "bank_import_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    bank_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    bank_account = relationship("BankAccount", back_populates="import_files")
    uploaded_by = relationship("User", back_populates="uploaded_bank_files")
    rows = relationship("BankRow", back_populates="import_file", cascade="all, delete-orphan")


class BankRow(Base):
    __tablename__ = "bank_rows"
    __table_args__ = (UniqueConstraint("import_file_id", "original_row_number", name="uq_import_file_row"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    import_file_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_import_files.id"), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    original_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_row: Mapped[Any] = mapped_column(JSON, nullable=False)
    txn_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    value_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    narration: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # CREDIT, DEBIT
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), default="INR", nullable=True)
    utr: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    payer_upi: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    flat_ref: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    parse_status: Mapped[str] = mapped_column(String(20), default="ACCEPTED", nullable=False)  # ACCEPTED, INVALID
    parse_errors: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)  # AUTO_MATCH, DUPLICATE_NO_OP, REVIEW
    decision_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_action: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # APPROVE, REJECT, HOLD, CORRECT_MAPPING, NO_ACTION
    matched_flat_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("flats.id"), nullable=True)
    matched_bill_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bills.id"), nullable=True)
    matched_payment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("payments.id"), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False
    )  # PENDING, APPROVED, REJECTED, HELD, CORRECTED, AUTO_POSTED
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_trail: Mapped[Any | None] = mapped_column(JSON, default=list, nullable=True)

    import_file = relationship("BankImportFile", back_populates="rows")
    bank_account = relationship("BankAccount", back_populates="rows")
    matched_flat = relationship("Flat")
    matched_bill = relationship("Bill", back_populates="matched_bank_rows")
    matched_payment = relationship("Payment", back_populates="matched_bank_rows")


class BankPosting(Base):
    __tablename__ = "bank_postings"
    __table_args__ = (UniqueConstraint("bank_account_id", "utr", name="uq_bank_postings_account_utr"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    bank_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    utr: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bank_row_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_rows.id"), nullable=False)
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    bank_account = relationship("BankAccount")
    bank_row = relationship("BankRow")
    payment = relationship("Payment")


class RegisteredUPI(Base):
    __tablename__ = "registered_upi_ids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    upi_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    flat = relationship("Flat", back_populates="registered_upis")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # BANK_ROW, PAYMENT, COMPLAINT, CLASSIFICATION, SAFETY
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    old_state: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)


# --- Complaints, Teams, Shifts, Decisions & Safety Models ---


class StaffTeam(Base):
    __tablename__ = "staff_teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)


class StaffShift(Base):
    __tablename__ = "staff_shifts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff_members.id"), nullable=False)
    shift_name: Mapped[str] = mapped_column(String(20), default="Morning", nullable=False)  # Morning, Evening, Night
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    staff = relationship("StaffMember", back_populates="shifts")


class IncidentGroup(Base):
    __tablename__ = "incident_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    tower_id: Mapped[str] = mapped_column(String(36), ForeignKey("towers.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    tower = relationship("Tower", back_populates="incident_groups")
    members = relationship("IncidentGroupMember", back_populates="incident_group", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="incident_group")


class IncidentGroupMember(Base):
    __tablename__ = "incident_group_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    incident_group_id: Mapped[str] = mapped_column(String(36), ForeignKey("incident_groups.id"), nullable=False)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=False)
    linked_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    incident_group = relationship("IncidentGroup", back_populates="members")


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    tower_id: Mapped[str] = mapped_column(String(36), ForeignKey("towers.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), default="UNCLASSIFIED", nullable=False
    )  # PLUMBING, ELECTRICAL, LIFT, CLEANLINESS, WATER_SUPPLY, SECURITY, COMMON_AREA, GENERAL, UNCLASSIFIED
    urgency: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="SUBMITTED", nullable=False
    )  # SUBMITTED, ASSIGNED, IN_PROGRESS, AWAITING_RESIDENT, RESOLVED, CLOSED, REOPEN_REQUESTED
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Optimistic concurrency lock
    assigned_staff_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("staff_members.id"), nullable=True)
    assigned_team: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1 to 5
    reopen_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reopen_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_safety_escalation: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=True)
    incident_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incident_groups.id"), nullable=True)

    flat = relationship("Flat", back_populates="complaints")
    tower = relationship("Tower", back_populates="complaints")
    user = relationship("User", back_populates="complaints")
    assigned_staff = relationship("StaffMember", back_populates="complaints")
    incident_group = relationship("IncidentGroup", back_populates="complaints")
    events = relationship("ComplaintEvent", back_populates="complaint", cascade="all, delete-orphan")
    attachments = relationship("ComplaintAttachment", back_populates="complaint", cascade="all, delete-orphan")
    decisions = relationship("ClassificationDecision", back_populates="complaint", cascade="all, delete-orphan")
    safety_events = relationship("SafetyEvent", back_populates="complaint", cascade="all, delete-orphan")


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # CREATED, ASSIGNED, STATUS_CHANGED, COMMENTED, REOPENED, RATED, SAFETY_ESCALATED, CATEGORY_CORRECTED
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    complaint = relationship("Complaint", back_populates="events")


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    complaint = relationship("Complaint", back_populates="attachments")


class ClassificationDecision(Base):
    __tablename__ = "classification_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # AI_GROQ, AI_LOCAL, HUMAN_HELP_DESK
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)
    short_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="en", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expected_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    complaint = relationship("Complaint", back_populates="decisions")


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    complaint_id: Mapped[str] = mapped_column(String(36), ForeignKey("complaints.id"), nullable=False)
    trigger_pattern: Mapped[str] = mapped_column(String(100), nullable=False)
    matched_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    duty_manager_notified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, ACKNOWLEDGED, DISMISSED
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    complaint = relationship("Complaint", back_populates="safety_events")
    actions = relationship("SafetyEventAction", back_populates="safety_event", cascade="all, delete-orphan")


class SafetyEventAction(Base):
    __tablename__ = "safety_event_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    safety_event_id: Mapped[str] = mapped_column(String(36), ForeignKey("safety_events.id"), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # ACKNOWLEDGE, DISMISS
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    safety_event = relationship("SafetyEvent", back_populates="actions")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="IN_APP", nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # COMPLAINT_UPDATE, PAYMENT_RECEIPT, ACCOUNTS_REVIEW, SAFETY_ESCALATION
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)

    user = relationship("User", back_populates="notifications")


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str | None] = mapped_column(String(20), default="ALL", nullable=True)  # ALL, TOWER
    target_tower_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("towers.id"), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), default="NORMAL", nullable=True)  # NORMAL, URGENT
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PUBLISHED")  # DRAFT, PUBLISHED, WITHDRAWN
    current_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    revisions = relationship("NoticeRevision", back_populates="notice", cascade="all, delete-orphan")


class NoticeRevision(Base):
    __tablename__ = "notice_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    notice_id: Mapped[str] = mapped_column(String(36), ForeignKey("notices.id"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    body_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_mr: Mapped[str | None] = mapped_column(Text, nullable=True)
    publish_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    audience: Mapped[str] = mapped_column(String(20), nullable=False, default="ALL")  # ALL, TOWER
    tower_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("towers.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")  # NORMAL, CRITICAL
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    notice = relationship("Notice", back_populates="revisions")
    tower = relationship("Tower")
    created_by = relationship("User")
    reads = relationship("NoticeRead", back_populates="revision", cascade="all, delete-orphan")


class NoticeRead(Base):
    __tablename__ = "notice_reads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    notice_revision_id: Mapped[str] = mapped_column(String(36), ForeignKey("notice_revisions.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    revision = relationship("NoticeRevision", back_populates="reads")
    user = relationship("User")


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    gate_id: Mapped[str] = mapped_column(String(36), ForeignKey("gates.id"), nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    visitor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(
        String(20), default="PENDING", nullable=True
    )  # PENDING, APPROVED, REJECTED, ENTERED, EXITED
    entered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=True)


class VisitorPhoto(Base):
    __tablename__ = "visitor_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)  # nulled on 90-day retention purge
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    capture_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    content_type: Mapped[str] = mapped_column(String(50), nullable=False, default="image/jpeg")
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    entries = relationship("VisitorEntry", back_populates="photo")


class PreApproval(Base):
    __tablename__ = "pre_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    gate_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("gates.id"), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # Salted SHA-256 verifier
    credential_jwt: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Compact ECDSA P-256 signed offline credential
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    flat = relationship("Flat")
    created_by = relationship("User")
    gate = relationship("Gate")
    entries = relationship("VisitorEntry", back_populates="pre_approval")


class VisitorEntry(Base):
    __tablename__ = "visitor_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    gate_id: Mapped[str] = mapped_column(String(36), ForeignKey("gates.id"), nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    visitor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="AWAITING_APPROVAL")
    # Statuses: AWAITING_APPROVAL, APPROVED, REJECTED, ADMITTED, EXITED, EXPIRED, OVERRIDDEN_ADMIT
    created_by_guard: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_decided_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approval_decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    photo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("visitor_photos.id"), nullable=True)
    pre_approval_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("pre_approvals.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ONLINE")  # ONLINE, OFFLINE_SYNC
    client_event_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    gate = relationship("Gate")
    flat = relationship("Flat")
    photo = relationship("VisitorPhoto", back_populates="entries")
    pre_approval = relationship("PreApproval", back_populates="entries")
    events = relationship("VisitorEvent", back_populates="visitor_entry", cascade="all, delete-orphan")
    overrides = relationship("SupervisorOverride", back_populates="visitor_entry", cascade="all, delete-orphan")


class VisitorEvent(Base):
    __tablename__ = "visitor_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    visitor_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("visitor_entries.id"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    visitor_entry = relationship("VisitorEntry", back_populates="events")
    actor = relationship("User")


class SupervisorOverride(Base):
    __tablename__ = "supervisor_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    visitor_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("visitor_entries.id"), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    override_type: Mapped[str] = mapped_column(String(50), nullable=False, default="OVERRIDDEN_ADMIT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    visitor_entry = relationship("VisitorEntry", back_populates="overrides")
    actor = relationship("User")


class Amenity(Base):
    __tablename__ = "amenities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hourly_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, default=10, nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)

    slots = relationship("AmenitySlot", back_populates="amenity", cascade="all, delete-orphan")
    amenity_rules = relationship("AmenityRule", back_populates="amenity", cascade="all, delete-orphan")
    closures = relationship("AmenityClosure", back_populates="amenity", cascade="all, delete-orphan")


class AmenitySlot(Base):
    __tablename__ = "amenity_slots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    amenity_id: Mapped[str] = mapped_column(String(36), ForeignKey("amenities.id"), nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    booked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    amenity = relationship("Amenity", back_populates="slots")
    bookings = relationship("AmenityBooking", back_populates="slot")


class AmenityRule(Base):
    __tablename__ = "amenity_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    amenity_id: Mapped[str] = mapped_column(String(36), ForeignKey("amenities.id"), nullable=False)
    booking_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    max_daily_slots_per_flat: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cancellation_cutoff_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    amenity = relationship("Amenity", back_populates="amenity_rules")


class AmenityClosure(Base):
    __tablename__ = "amenity_closures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    amenity_id: Mapped[str] = mapped_column(String(36), ForeignKey("amenities.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    amenity = relationship("Amenity", back_populates="closures")
    created_by = relationship("User")


class AmenityBooking(Base):
    __tablename__ = "amenity_bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    flat_id: Mapped[str] = mapped_column(String(36), ForeignKey("flats.id"), nullable=False)
    slot_id: Mapped[str] = mapped_column(String(36), ForeignKey("amenity_slots.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CONFIRMED")  # CONFIRMED, CANCELLED
    fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    fee_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PAID_TEST"
    )  # PAID_TEST, PENDING, CANCELLED
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    flat = relationship("Flat")
    slot = relationship("AmenitySlot", back_populates="bookings")
    user = relationship("User")


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    salt: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
