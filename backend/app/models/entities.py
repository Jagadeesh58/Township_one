import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, JSON, Float
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    flat_memberships = relationship("FlatMembership", back_populates="user", cascade="all, delete-orphan")
    staff_profile = relationship("StaffMember", back_populates="user", uselist=False)
    complaints = relationship("Complaint", back_populates="user")
    uploaded_bank_files = relationship("BankImportFile", back_populates="uploaded_by")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_code = Column(String(30), nullable=False)  # RESIDENT, HELPDESK, GUARD, ACCOUNTS, COMMITTEE, ADMIN
    scope_type = Column(String(30), default="TOWNSHIP")  # TOWNSHIP, TOWER, FLAT, GATE
    scope_id = Column(String(36), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="role_assignments")


class RevokedToken(Base):
    """Persistent token revocation store for multi-worker session security."""
    __tablename__ = "revoked_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    token_jti = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    revoked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)


class Tower(Base):
    __tablename__ = "towers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(10), unique=True, index=True, nullable=False)  # T01 .. T28
    name = Column(String(50), nullable=False)
    total_floors = Column(Integer, default=20)
    flats_per_floor = Column(Integer, default=4)

    flats = relationship("Flat", back_populates="tower")
    complaints = relationship("Complaint", back_populates="tower")
    incident_groups = relationship("IncidentGroup", back_populates="tower")


class Flat(Base):
    __tablename__ = "flats"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tower_id = Column(String(36), ForeignKey("towers.id"), nullable=False)
    flat_number = Column(String(20), unique=True, index=True, nullable=False)  # e.g. T07-1203
    floor_number = Column(Integer, nullable=False)
    area_sqft = Column(Numeric(10, 2), nullable=False)  # e.g. 1150.00
    bhk_type = Column(String(10), default="3 BHK")

    tower = relationship("Tower", back_populates="flats")
    memberships = relationship("FlatMembership", back_populates="flat")
    bills = relationship("Bill", back_populates="flat")
    ledger_entries = relationship("FlatLedgerEntry", back_populates="flat")
    complaints = relationship("Complaint", back_populates="flat")
    registered_upis = relationship("RegisteredUPI", back_populates="flat")


class FlatMembership(Base):
    __tablename__ = "flat_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    member_type = Column(String(20), nullable=False)  # OWNER, TENANT, FAMILY
    is_active = Column(Boolean, default=True)
    can_pay_bills = Column(Boolean, default=True)
    can_approve_visitors = Column(Boolean, default=True)
    can_raise_complaints = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    flat = relationship("Flat", back_populates="memberships")
    user = relationship("User", back_populates="flat_memberships")


class StaffMember(Base):
    __tablename__ = "staff_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    staff_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    designation = Column(String(50), nullable=False)
    department = Column(String(50), nullable=False)  # Plumbing, Electrical, Security, Housekeeping, Accounts, Operations
    shift = Column(String(20), default="Morning")  # Morning, Evening, Night
    is_available = Column(Boolean, default=True)

    user = relationship("User", back_populates="staff_profile")
    complaints = relationship("Complaint", back_populates="assigned_staff")
    shifts = relationship("StaffShift", back_populates="staff")


class Gate(Base):
    __tablename__ = "gates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    gate_number = Column(Integer, unique=True, nullable=False)  # 1, 2, 3, 4
    name = Column(String(50), nullable=False)  # Main North Gate, South Gate, etc.
    location_description = Column(String(100), nullable=True)


class BillingRule(Base):
    __tablename__ = "billing_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    rate_per_sqft = Column(Numeric(10, 2), nullable=False, default=Decimal("6.50"))
    due_day_of_month = Column(Integer, default=15)
    grace_period_days = Column(Integer, default=5)
    late_fee_percentage_pa = Column(Numeric(5, 2), default=Decimal("18.00"))  # Illustrative demo rule
    version = Column(String(20), default="v1.0-demo")
    is_active = Column(Boolean, default=True)


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("flat_id", "period_month", "period_year", name="uq_flat_bill_period"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    billing_rule_id = Column(String(36), ForeignKey("billing_rules.id"), nullable=True)
    billing_rule_version = Column(String(50), default="v1.0-demo", nullable=False)
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    
    area_sqft = Column(Numeric(10, 2), nullable=False)
    rate_per_sqft = Column(Numeric(10, 2), nullable=False)
    principal_amount = Column(Numeric(14, 2), nullable=False)
    late_fee_amount = Column(Numeric(14, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), default=Decimal("0.00"))
    balance_amount = Column(Numeric(14, 2), nullable=False)
    status = Column(String(20), default="ISSUED")  # ISSUED, PARTIALLY_PAID, PAID, OVERDUE

    flat = relationship("Flat", back_populates="bills")
    lines = relationship("BillLine", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="bill")
    matched_bank_rows = relationship("BankRow", back_populates="matched_bill")


class BillLine(Base):
    __tablename__ = "bill_lines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    bill_id = Column(String(36), ForeignKey("bills.id"), nullable=False)
    line_type = Column(String(20), nullable=False)  # PRINCIPAL, LATE_FEE, ADJUSTMENT
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)

    bill = relationship("Bill", back_populates="lines")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    bill_id = Column(String(36), ForeignKey("bills.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    payment_method = Column(String(30), default="TEST_PAYMENT")  # TEST_PAYMENT, BANK_TRANSFER, UPI, CHEQUE
    status = Column(String(20), default="SUCCESS")  # PENDING, SUCCESS, FAILED, EXPIRED, REFUNDED
    transaction_reference = Column(String(50), unique=True, nullable=False)
    idempotency_key = Column(String(100), index=True, nullable=False)
    paid_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    receipt_number = Column(String(50), unique=True, nullable=True)
    payer_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    bill = relationship("Bill", back_populates="payments")
    receipt = relationship("Receipt", back_populates="payment", uselist=False, cascade="all, delete-orphan")
    matched_bank_rows = relationship("BankRow", back_populates="matched_payment")


class PaymentIdempotencyRecord(Base):
    __tablename__ = "payment_idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    bill_id = Column(String(36), ForeignKey("bills.id"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(10), default="INR", nullable=True)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=True)
    response_code = Column(Integer, nullable=True)
    response_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))



class FlatLedgerEntry(Base):
    __tablename__ = "flat_ledger_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    entry_type = Column(String(20), nullable=False)  # INVOICE, PAYMENT, REVERSAL, CREDIT_NOTE
    amount = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    description = Column(String(255), nullable=False)
    reference_id = Column(String(50), nullable=True)  # Bill ID, Payment ID, Bank Row ID
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    flat = relationship("Flat", back_populates="ledger_entries")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False, unique=True)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    flat_number = Column(String(20), nullable=False)
    resident_name = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_mode = Column(String(30), nullable=False)
    transaction_reference = Column(String(50), nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment = relationship("Payment", back_populates="receipt")


# --- Bank Statement Matching Models ---

class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account_no = Column(String(50), unique=True, index=True, nullable=False)
    bank_name = Column(String(100), nullable=False)
    ifsc_code = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    import_files = relationship("BankImportFile", back_populates="bank_account")
    rows = relationship("BankRow", back_populates="bank_account")


class BankImportFile(Base):
    __tablename__ = "bank_import_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_sha256 = Column(String(64), nullable=False, index=True)
    uploaded_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_rows = Column(Integer, default=0)
    accepted_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)

    bank_account = relationship("BankAccount", back_populates="import_files")
    uploaded_by = relationship("User", back_populates="uploaded_bank_files")
    rows = relationship("BankRow", back_populates="import_file", cascade="all, delete-orphan")


class BankRow(Base):
    __tablename__ = "bank_rows"
    __table_args__ = (
        UniqueConstraint("import_file_id", "original_row_number", name="uq_import_file_row"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    import_file_id = Column(String(36), ForeignKey("bank_import_files.id"), nullable=False)
    bank_account_id = Column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    original_row_number = Column(Integer, nullable=False)
    raw_row = Column(JSON, nullable=False)
    txn_date = Column(DateTime, nullable=True)
    value_date = Column(DateTime, nullable=True)
    narration = Column(Text, nullable=True)
    direction = Column(String(10), nullable=True)  # CREDIT, DEBIT
    amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(10), default="INR")
    utr = Column(String(100), nullable=True, index=True)
    payer_upi = Column(String(100), nullable=True, index=True)
    flat_ref = Column(String(50), nullable=True, index=True)
    parse_status = Column(String(20), default="ACCEPTED")  # ACCEPTED, INVALID
    parse_errors = Column(JSON, nullable=True)
    decision = Column(String(50), nullable=True)  # AUTO_MATCH, DUPLICATE_NO_OP, REVIEW
    decision_reason = Column(String(100), nullable=True)
    next_action = Column(String(50), nullable=True)  # APPROVE, REJECT, HOLD, CORRECT_MAPPING, NO_ACTION
    matched_flat_id = Column(String(36), ForeignKey("flats.id"), nullable=True)
    matched_bill_id = Column(String(36), ForeignKey("bills.id"), nullable=True)
    matched_payment_id = Column(String(36), ForeignKey("payments.id"), nullable=True)
    review_status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED, HELD, CORRECTED, AUTO_POSTED
    reviewed_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    correction_reason = Column(Text, nullable=True)
    audit_trail = Column(JSON, default=list)

    import_file = relationship("BankImportFile", back_populates="rows")
    bank_account = relationship("BankAccount", back_populates="rows")
    matched_flat = relationship("Flat")
    matched_bill = relationship("Bill", back_populates="matched_bank_rows")
    matched_payment = relationship("Payment", back_populates="matched_bank_rows")


class RegisteredUPI(Base):
    __tablename__ = "registered_upi_ids"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    upi_id = Column(String(100), nullable=False, index=True)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    flat = relationship("Flat", back_populates="registered_upis")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(50), nullable=False)  # BANK_ROW, PAYMENT, COMPLAINT, CLASSIFICATION, SAFETY
    entity_id = Column(String(36), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role = Column(String(30), nullable=True)
    old_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# --- Complaints, Teams, Shifts, Decisions & Safety Models ---

class StaffTeam(Base):
    __tablename__ = "staff_teams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False)
    category = Column(String(30), nullable=False)


class StaffShift(Base):
    __tablename__ = "staff_shifts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    staff_id = Column(String(36), ForeignKey("staff_members.id"), nullable=False)
    shift_name = Column(String(20), default="Morning")  # Morning, Evening, Night
    is_on_duty = Column(Boolean, default=True)

    staff = relationship("StaffMember", back_populates="shifts")


class IncidentGroup(Base):
    __tablename__ = "incident_groups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tower_id = Column(String(36), ForeignKey("towers.id"), nullable=False)
    category = Column(String(30), nullable=False)
    title = Column(String(150), nullable=False)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    tower = relationship("Tower", back_populates="incident_groups")
    members = relationship("IncidentGroupMember", back_populates="incident_group", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="incident_group")


class IncidentGroupMember(Base):
    __tablename__ = "incident_group_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_group_id = Column(String(36), ForeignKey("incident_groups.id"), nullable=False)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False)
    linked_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident_group = relationship("IncidentGroup", back_populates="members")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_number = Column(String(30), unique=True, index=True, nullable=False)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    tower_id = Column(String(36), ForeignKey("towers.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(30), default="UNCLASSIFIED", nullable=False)  # PLUMBING, ELECTRICAL, LIFT, CLEANLINESS, WATER_SUPPLY, SECURITY, COMMON_AREA, GENERAL, UNCLASSIFIED
    urgency = Column(String(20), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    language = Column(String(20), default="en", nullable=False)
    status = Column(String(30), default="SUBMITTED", nullable=False)  # SUBMITTED, ASSIGNED, IN_PROGRESS, AWAITING_RESIDENT, RESOLVED, CLOSED, REOPEN_REQUESTED
    version = Column(Integer, default=1, nullable=False)  # Optimistic concurrency lock
    assigned_staff_id = Column(String(36), ForeignKey("staff_members.id"), nullable=True)
    assigned_team = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    resolution_summary = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1 to 5
    reopen_requested = Column(Boolean, default=False)
    reopen_reason = Column(Text, nullable=True)
    is_safety_escalation = Column(Boolean, default=False)
    duplicate_of_id = Column(String(36), ForeignKey("complaints.id"), nullable=True)
    incident_group_id = Column(String(36), ForeignKey("incident_groups.id"), nullable=True)

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

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role = Column(String(30), nullable=True)
    event_type = Column(String(50), nullable=False)  # CREATED, ASSIGNED, STATUS_CHANGED, COMMENTED, REOPENED, RATED, SAFETY_ESCALATED, CATEGORY_CORRECTED
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="events")


class ComplaintAttachment(Base):
    __tablename__ = "complaint_attachments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False)
    storage_key = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="attachments")


class ClassificationDecision(Base):
    __tablename__ = "classification_decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False)
    actor_type = Column(String(20), nullable=False)  # AI_GROQ, AI_LOCAL, HUMAN_HELP_DESK
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    category = Column(String(30), nullable=False)
    urgency = Column(String(20), nullable=False)
    short_reason = Column(Text, nullable=True)
    language = Column(String(20), default="en")
    confidence = Column(Float, nullable=True)
    needs_human_review = Column(Boolean, default=False)
    provider = Column(String(50), nullable=True)
    model_version = Column(String(50), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    fallback_used = Column(Boolean, default=False)
    expected_version = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="decisions")


class SafetyEvent(Base):
    __tablename__ = "safety_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False)
    trigger_pattern = Column(String(100), nullable=False)
    matched_text = Column(Text, nullable=False)
    language = Column(String(20), nullable=False)
    duty_manager_notified = Column(Boolean, default=True)
    notification_sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, DISMISSED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    complaint = relationship("Complaint", back_populates="safety_events")
    actions = relationship("SafetyEventAction", back_populates="safety_event", cascade="all, delete-orphan")


class SafetyEventAction(Base):
    __tablename__ = "safety_event_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    safety_event_id = Column(String(36), ForeignKey("safety_events.id"), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)  # ACKNOWLEDGE, DISMISS
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    safety_event = relationship("SafetyEvent", back_populates="actions")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    channel = Column(String(20), default="IN_APP")
    notification_type = Column(String(50), nullable=False)  # COMPLAINT_UPDATE, PAYMENT_RECEIPT, ACCOUNTS_REVIEW, SAFETY_ESCALATION
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")


class Notice(Base):
    __tablename__ = "notices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    target_audience = Column(String(20), default="ALL")  # ALL, TOWER
    target_tower_id = Column(String(36), ForeignKey("towers.id"), nullable=True)
    priority = Column(String(20), default="NORMAL")  # NORMAL, URGENT
    published_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    gate_id = Column(String(36), ForeignKey("gates.id"), nullable=False)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    visitor_name = Column(String(100), nullable=False)
    purpose = Column(String(100), nullable=False)
    photo_url = Column(String(255), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED, ENTERED, EXITED
    entered_at = Column(DateTime, nullable=True)
    exited_at = Column(DateTime, nullable=True)
    approved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Amenity(Base):
    __tablename__ = "amenities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    hourly_fee = Column(Numeric(10, 2), default=Decimal("0.00"))
    capacity = Column(Integer, default=10)
    rules = Column(Text, nullable=True)


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone = Column(String(20), nullable=False, index=True)
    otp_hash = Column(String(64), nullable=False)
    salt = Column(String(32), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    is_used = Column(Boolean, nullable=False, default=False)
    ip_address = Column(String(45), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
