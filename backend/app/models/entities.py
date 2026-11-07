import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
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


class Tower(Base):
    __tablename__ = "towers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(10), unique=True, index=True, nullable=False)  # T01 .. T28
    name = Column(String(50), nullable=False)
    total_floors = Column(Integer, default=20)
    flats_per_floor = Column(Integer, default=4)

    flats = relationship("Flat", back_populates="tower")


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
    status = Column(String(20), default="SUCCESS")  # SUCCESS, PENDING, FAILED, EXPIRED
    payment_method = Column(String(30), default="UPI_SIMULATED")
    transaction_reference = Column(String(50), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(100), nullable=True, index=True)
    paid_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    receipt_number = Column(String(50), unique=True, nullable=True)
    payer_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    bill = relationship("Bill", back_populates="payments")
    receipt = relationship("Receipt", back_populates="payment", uselist=False)


class PaymentIdempotencyRecord(Base):
    __tablename__ = "payment_idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payment_idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    bill_id = Column(String(36), ForeignKey("bills.id"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    request_hash = Column(String(64), nullable=False)
    status = Column(String(20), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, COMPLETED, FAILED
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=True)
    response_code = Column(Integer, nullable=True)
    response_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    payment = relationship("Payment", foreign_keys=[payment_id])


class FlatLedgerEntry(Base):
    __tablename__ = "flat_ledger_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    entry_type = Column(String(20), nullable=False)  # DEBIT (Bill), CREDIT (Payment), ADJUSTMENT
    amount = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    description = Column(String(255), nullable=False)
    reference_id = Column(String(50), nullable=True)  # Bill ID or Payment Reference
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    flat = relationship("Flat", back_populates="ledger_entries")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    payment_id = Column(String(36), ForeignKey("payments.id"), unique=True, nullable=False)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    flat_number = Column(String(20), nullable=False)
    resident_name = Column(String(100), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_mode = Column(String(30), nullable=False)
    transaction_reference = Column(String(50), nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    payment = relationship("Payment", back_populates="receipt")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_number = Column(String(20), unique=True, index=True, nullable=False)
    flat_id = Column(String(36), ForeignKey("flats.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(30), nullable=False)  # PLUMBING, ELECTRICAL, LIFT, CLEANLINESS, WATER_SUPPLY, SECURITY, COMMON_AREA, GENERAL
    urgency = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(20), default="SUBMITTED")  # SUBMITTED, ASSIGNED, IN_PROGRESS, RESOLVED, CLOSED
    assigned_staff_id = Column(String(36), ForeignKey("staff_members.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_summary = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    is_safety_escalation = Column(Boolean, default=False)
    duplicate_of_id = Column(String(36), ForeignKey("complaints.id"), nullable=True)

    flat = relationship("Flat", back_populates="complaints")


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
