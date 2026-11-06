from decimal import Decimal
import pytest
from backend.app.core.database import SessionLocal
from backend.app.models.entities import (
    Tower, Flat, StaffMember, Gate, Bill, Complaint, User, UserRoleAssignment, FlatMembership
)
from seed.seed_data import seed_database


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

        # Check membership
        membership = db.query(FlatMembership).filter(FlatMembership.flat_id == flat.id).first()
        assert membership is not None
        assert membership.member_type == "OWNER"
        assert membership.user.name == "Neeraj Kulkarni"

        # Check bill
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("7475.00")  # 1150 * 6.50
        assert bill.paid_amount == Decimal("7475.00")
        assert bill.balance_amount == Decimal("0.00")
        assert bill.status == "PAID"

        # Check complaints
        complaints_count = db.query(Complaint).filter(Complaint.flat_id == flat.id).count()
        # Should have 0 open complaints (or 1 lift complaint from tower)
    finally:
        db.close()


def test_sample_flat_t12_0408_exact_values():
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

        # Check bill
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("6370.00")  # 980 * 6.50
        assert bill.paid_amount == Decimal("0.00")
        assert bill.balance_amount == Decimal("6370.00")
        assert bill.status == "OVERDUE"

        # Check open complaint (1 water leak)
        complaint = db.query(Complaint).filter(Complaint.flat_id == flat.id).first()
        assert complaint is not None
        assert complaint.category == "WATER_SUPPLY"
        assert complaint.urgency == "HIGH"
        assert "water" in complaint.description.lower()
    finally:
        db.close()


def test_sample_flat_t21_1601_exact_values():
    db = SessionLocal()
    try:
        flat = db.query(Flat).filter(Flat.flat_number == "T21-1601").first()
        assert flat is not None
        assert flat.area_sqft == Decimal("1640.00")

        # Check bill
        bill = db.query(Bill).filter(Bill.flat_id == flat.id).first()
        assert bill is not None
        assert bill.principal_amount == Decimal("10660.00")  # 1640 * 6.50
        assert bill.paid_amount == Decimal("5000.00")
        assert bill.balance_amount == Decimal("5660.00")
        assert bill.status == "PARTIALLY_PAID"
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
