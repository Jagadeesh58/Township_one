"""
Township One - Database and Township Seed Verification Tests.

Responsibility:
- Verify exact township entity counts: 28 towers, 2,400 flats, 180 staff, 4 gates.
- Verify exact sample flats: T07-1203 (paid), T12-0408 (unpaid, 47 days overdue), T21-1601 (partial, 18 days overdue).
- Verify exact due dates and overdue math against DEMO_AS_OF_DATE (2026-11-06).
- Verify 10 distinct synthetic residents for 10 Tower 7 lift complaints linked to CMP-2026-1002.
- Verify fail-closed seed reset safety policy (refusing unconfirmed or remote database resets).
- Verify safe mode idempotency and partial seed protection.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
import pytest
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.entities import (
    Tower, Flat, StaffMember, Gate, Bill, Complaint, User, UserRoleAssignment, FlatMembership
)
from seed.seed_data import is_safe_local_database, seed_database


def test_seed_entity_counts():
    db = SessionLocal()
    try:
        towers_count = db.query(Tower).count()
        flats_count = db.query(Flat).count()
        staff_count = db.query(StaffMember).count()
        gates_count = db.query(Gate).count()

        assert towers_count == 28, f"Expected 28 towers, got {towers_count}"
        assert flats_count == 2400, f"Expected 2400 flats, got {flats_count}"
        assert staff_count == 180, f"Expected 180 staff, got {staff_count}"
        assert gates_count == 4, f"Expected 4 gates, got {gates_count}"
    finally:
        db.close()


def test_sample_flat_t07_1203_exact_values():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T07-1203").first()
        assert flat is not None
        assert flat.area_sqft == Decimal("1150.00")

        # Check owner membership
        membership = db.query(FlatMembership).filter(
            FlatMembership.flat_id == flat.id,
            FlatMembership.member_type == "OWNER"
        ).first()
        assert membership is not None
        assert membership.user.name == "Neeraj Kulkarni"
        assert membership.can_pay_bills is True

        # Check bill
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("7475.00")  # 1150 * 6.50
        assert bill.paid_amount == Decimal("7475.00")
        assert bill.balance_amount == Decimal("0.00")
        assert bill.status == "PAID"
    finally:
        db.close()


def test_sample_flat_t12_0408_exact_values_and_overdue_days():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T12-0408").first()
        assert flat is not None
        assert flat.area_sqft == Decimal("980.00")

        # Check tenant membership
        membership = db.query(FlatMembership).filter(FlatMembership.flat_id == flat.id).first()
        assert membership is not None
        assert membership.member_type == "TENANT"
        assert membership.user.name == "Swati Joshi"

        # Check bill: Must be unpaid and exactly 47 days overdue as of 2026-11-06 (due date: 2026-09-20)
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("6370.00")  # 980 * 6.50
        assert bill.paid_amount == Decimal("0.00")
        assert bill.balance_amount == Decimal("6370.00")
        assert bill.status == "OVERDUE"
        assert bill.due_date.strftime("%Y-%m-%d") == "2026-09-20"

        # Overdue math check
        ref_date = datetime(2026, 11, 6)
        due_d = bill.due_date.replace(tzinfo=None)
        assert (ref_date - due_d).days == 47

        # Check open complaint (1 water leak)
        complaint = db.query(Complaint).filter(Complaint.flat_id == flat.id).first()
        assert complaint is not None
        assert complaint.category == "WATER_SUPPLY"
        assert complaint.urgency == "HIGH"
        assert "water" in complaint.description.lower()
    finally:
        db.close()


def test_sample_flat_t21_1601_exact_values_and_overdue_days():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T21-1601").first()
        assert flat is not None
        assert flat.area_sqft == Decimal("1640.00")

        # Check bill: Partially paid ₹5,000, balance ₹5,660, exactly 18 days overdue as of 2026-11-06 (due date: 2026-10-19)
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("10660.00")  # 1640 * 6.50
        assert bill.paid_amount == Decimal("5000.00")
        assert bill.balance_amount == Decimal("5660.00")
        assert bill.status == "PARTIALLY_PAID"
        assert bill.due_date.strftime("%Y-%m-%d") == "2026-10-19"

        # Overdue math check
        ref_date = datetime(2026, 11, 6)
        due_d = bill.due_date.replace(tzinfo=None)
        assert (ref_date - due_d).days == 18
    finally:
        db.close()


def test_family_member_permission_boundaries():
    db = SessionLocal()
    try:
        ananya = db.query(User).filter(User.phone == "9876543213").first()
        assert ananya is not None
        assert ananya.name == "Ananya Kulkarni"

        membership = db.query(FlatMembership).filter(FlatMembership.user_id == ananya.id).first()
        assert membership is not None
        assert membership.member_type == "FAMILY"
        assert membership.can_pay_bills is False  # Restricted permission
        assert membership.can_approve_visitors is True
        assert membership.can_raise_complaints is True
    finally:
        db.close()


def test_ten_linked_lift_complaints_with_distinct_reporters():
    """Verify 10 distinct residents lodged 10 separate lift complaints linked to CMP-2026-1002."""
    db = SessionLocal()
    try:
        primary = db.query(Complaint).filter(Complaint.ticket_number == "CMP-2026-1002").first()
        assert primary is not None
        assert primary.category == "LIFT"

        linked_complaints = db.query(Complaint).filter(Complaint.duplicate_of_id == primary.id).all()
        assert len(linked_complaints) == 9

        all_lift_complaints = [primary] + linked_complaints
        reporter_ids = {c.user_id for c in all_lift_complaints}
        assert len(reporter_ids) == 10, f"Expected 10 distinct reporters, got {len(reporter_ids)}"

        flat_ids = {c.flat_id for c in all_lift_complaints}
        assert len(flat_ids) == 10, f"Expected 10 distinct flats, got {len(flat_ids)}"

        for c in linked_complaints:
            assert c.status in ["ASSIGNED", "IN_PROGRESS", "SUBMITTED"]
            assert c.resolved_at is None
    finally:
        db.close()


def test_reviewer_role_assignments():
    db = SessionLocal()
    try:
        expected_roles = ["RESIDENT", "HELPDESK", "GUARD", "ACCOUNTS", "COMMITTEE", "ADMIN"]
        for role in expected_roles:
            assignment = db.query(UserRoleAssignment).filter(UserRoleAssignment.role_code == role).first()
            assert assignment is not None, f"Expected role {role} to be seeded"
            assert assignment.is_active is True
    finally:
        db.close()


def test_seed_safe_mode_idempotent_on_seeded_db():
    """Verify running safe seed on an already complete database safely succeeds without duplicate insertion."""
    res = seed_database(mode="safe")
    assert res["status"] in ["already_seeded", "seeded"]
    assert res["flats_count"] == 2400


def test_seed_safety_rejects_unconfirmed_destructive_reset():
    """Verify seed_database fails closed if reset-demo is attempted without explicit confirmation."""
    with pytest.raises(RuntimeError) as exc_info:
        seed_database(mode="reset-demo", confirm_local_demo=False)
    assert "Destructive demo reset requires explicit confirmation" in str(exc_info.value)


def test_seed_safety_rejects_remote_database_urls():
    """Verify is_safe_local_database rejects hosted / cloud databases."""
    assert is_safe_local_database("sqlite:///./township_one.db") is True
    assert is_safe_local_database("postgresql://user:pass@localhost:5432/township") is True
    assert is_safe_local_database("postgresql://user:pass@127.0.0.1:5432/township") is True

    # Cloud hosted databases must be blocked
    assert is_safe_local_database("postgresql://user:pass@ep-summer-pool.us-east-2.aws.neon.tech/db") is False
    assert is_safe_local_database("postgresql://user:pass@my-cluster.rds.amazonaws.com/db") is False
    assert is_safe_local_database("postgresql://user:pass@db.supabase.co/township") is False
    assert is_safe_local_database("postgresql://user:pass@dpg-render.com/township") is False


def test_seed_safe_mode_rejects_remote_database_engine():
    """Verify seed_database in both safe and reset-demo mode rejects remote database engines before touching them."""
    class DummyRemoteEngine:
        url = "postgresql://admin:secret@ep-cool-cloud.us-east-2.aws.neon.tech/prod_db"

    dummy_engine = DummyRemoteEngine()

    with pytest.raises(RuntimeError) as exc_safe:
        seed_database(target_engine=dummy_engine, mode="safe")
    assert "Refusing to seed or modify non-local / remote database" in str(exc_safe.value)

    with pytest.raises(RuntimeError) as exc_reset:
        seed_database(target_engine=dummy_engine, mode="reset-demo", confirm_local_demo=True)
    assert "Refusing to seed or modify non-local / remote database" in str(exc_reset.value)
