"""
Day 1 · D1-S2 — Database and Township Seed: Synthetic Dataset Generator.

Responsibility:
- Deterministically seed 28 towers, 2,400 flats, 180 staff members, and 4 gates.
- Restore exact reviewer sample data for T07-1203, T12-0408, and T21-1601.
- Provide ten distinct synthetic residents for ten open lift complaints linked to CMP-2026-1002.
- Enforce strict fail-closed safety policy protecting remote/production databases against destructive reset.
- Support non-destructive idempotent seeding (--mode safe) and guarded demo reset (--mode reset-demo --confirm-local-demo).

Related documentation:
docs/day-1/D1-S2-database-and-township-seed.md
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.core.database import engine as default_engine, Base
from backend.app.models.entities import (
    User, UserRoleAssignment, Tower, Flat, FlatMembership,
    StaffMember, Gate, BillingRule, Bill, BillLine, Payment,
    PaymentIdempotencyRecord, FlatLedgerEntry, Receipt, Complaint, Notice, Amenity
)


def is_safe_local_database(url_str: str) -> bool:
    """
    Checks if a database URL is strictly a local developer/demo database.
    Rejects any remote or hosted cloud database (e.g. Neon, AWS RDS, Supabase, Render).
    """
    url_lower = url_str.lower()
    if url_lower.startswith("sqlite"):
        return True

    remote_markers = [
        "neon.tech", "amazonaws.com", "supabase.co", "render.com",
        "cockroachlabs.cloud", "aivencloud.com", "azure.com"
    ]
    for marker in remote_markers:
        if marker in url_lower:
            return False

    if "@localhost" in url_lower or "@127.0.0.1" in url_lower or "@::1" in url_lower:
        return True

    return False


def seed_database(target_engine=None, mode: str = "safe", confirm_local_demo: bool = False):
    """
    Seeds Township One database with 2,400 flats, 28 towers, 180 staff, 4 gates,
    and verified sample records as of DEMO_AS_OF_DATE (2026-11-06T00:00:00Z).
    """
    active_engine = target_engine if target_engine is not None else default_engine
    db_url_str = str(active_engine.url)

    # 1. Environment Safety Checks
    if settings.APP_ENV.lower() == "production" or os.environ.get("TOWNSHIP_ENV") == "production":
        raise RuntimeError("FATAL SECURITY VIOLATION: Seeding or resetting is strictly prohibited in production.")

    if mode == "reset-demo":
        if not is_safe_local_database(db_url_str):
            raise RuntimeError(
                f"FATAL: Refusing destructive reset on non-local / remote database: {db_url_str}"
            )
        if not confirm_local_demo and os.environ.get("CONFIRM_LOCAL_DEMO_RESET") != "true":
            raise RuntimeError(
                "Destructive demo reset requires explicit confirmation. "
                "Pass --confirm-local-demo or set CONFIRM_LOCAL_DEMO_RESET=true."
            )
        print(f"Executing clean demo database reset on local database: {db_url_str}...")
        Base.metadata.drop_all(bind=active_engine)
        Base.metadata.create_all(bind=active_engine)
    else:
        # mode == 'safe' (idempotent, non-destructive)
        print(f"Running safe non-destructive seed check on: {db_url_str}...")
        Base.metadata.create_all(bind=active_engine)
        SessionCheck = sessionmaker(autocommit=False, autoflush=False, bind=active_engine)
        check_db = SessionCheck()
        try:
            existing_flats = check_db.query(Flat).count()
            if existing_flats >= 2400:
                print(f"Safe seed: Database already fully seeded ({existing_flats} flats present). Preserving existing records.")
                return
        finally:
            check_db.close()

    Session = sessionmaker(autocommit=False, autoflush=False, bind=active_engine)
    db = Session()

    try:
        # Reference date consistency: 2026-11-06T00:00:00Z
        try:
            demo_now = datetime.fromisoformat(settings.DEMO_AS_OF_DATE.replace("Z", "+00:00"))
        except Exception:
            demo_now = datetime(2026, 11, 6, 0, 0, tzinfo=timezone.utc)

        print("1. Creating Billing Rules...")
        rule = BillingRule(
            id="rule-demo-v1",
            name="Maharashtra Society Bye-laws Demo Rule (Illustrative Demo Assumption)",
            rate_per_sqft=Decimal("6.50"),
            due_day_of_month=15,
            grace_period_days=5,
            late_fee_percentage_pa=Decimal("18.00"),
            version="v1.0-demo",
            is_active=True
        )
        db.add(rule)
        db.flush()

        print("2. Creating 4 Gates...")
        gate_names = [
            (1, "Main North Gate", "Main boulevard vehicle & visitor entry"),
            (2, "South Gate", "Near Tower 18-28 service exit"),
            (3, "East Gate", "Pedestrian & school bus pickup gate"),
            (4, "West Gate", "Clubhouse and sports arena delivery gate")
        ]
        gates = []
        for g_num, g_name, g_desc in gate_names:
            gate = Gate(gate_number=g_num, name=g_name, location_description=g_desc)
            db.add(gate)
            gates.append(gate)
        db.flush()

        print("3. Creating 28 Towers...")
        towers = []
        for t_idx in range(1, 29):
            code = f"T{t_idx:02d}"
            name = f"Tower {t_idx}"
            tower = Tower(code=code, name=name, total_floors=20, flats_per_floor=4)
            db.add(tower)
            towers.append(tower)
        db.flush()

        print("4. Creating 2,400 Flats across 28 Towers...")
        flats_dict = {}
        total_flats_created = 0

        # Exact sample areas required by challenge brief:
        exact_areas = {
            "T07-1203": Decimal("1150.00"),
            "T12-0408": Decimal("980.00"),
            "T21-1601": Decimal("1640.00")
        }

        for idx, t in enumerate(towers):
            flats_in_this_tower = 86 if idx < 20 else 85
            for f_idx in range(1, flats_in_this_tower + 1):
                floor = ((f_idx - 1) // 4) + 1
                unit = ((f_idx - 1) % 4) + 1
                flat_num = f"{t.code}-{floor:02d}{unit:02d}"

                # Ensure exact sample flat numbers from the brief are present
                if t.code == "T12" and f_idx == 16:
                    flat_num = "T12-0408"
                    floor = 4
                elif t.code == "T07" and f_idx == 47:
                    flat_num = "T07-1203"
                    floor = 12
                elif t.code == "T21" and f_idx == 61:
                    flat_num = "T21-1601"
                    floor = 16

                # Area calculation
                if flat_num in exact_areas:
                    area = exact_areas[flat_num]
                elif unit == 1:
                    area = Decimal("1640.00")  # 3 BHK
                elif unit == 2:
                    area = Decimal("1420.00")  # 3 BHK
                elif unit == 3:
                    area = Decimal("1150.00")  # 2 BHK
                else:
                    area = Decimal("980.00")   # 2 BHK Compact

                flat = Flat(
                    tower_id=t.id,
                    flat_number=flat_num,
                    floor_number=floor,
                    area_sqft=area,
                    bhk_type="3 BHK" if area >= Decimal("1420.00") else "2 BHK"
                )
                db.add(flat)
                flats_dict[flat_num] = flat
                total_flats_created += 1

        db.flush()
        print(f"   Created {total_flats_created} flats.")

        print("5. Creating 180 Staff Members...")
        roles_distribution = [
            ("SECURITY", 80),
            ("HOUSEKEEPING", 45),
            ("MAINTENANCE", 35),
            ("MANAGEMENT", 20)
        ]
        staff_list = []
        staff_idx = 1
        for role_name, count in roles_distribution:
            for _ in range(count):
                st = StaffMember(
                    staff_code=f"EMP-T1-{staff_idx:04d}",
                    name=f"Staff {staff_idx} ({role_name.capitalize()})",
                    designation=role_name.capitalize(),
                    department="Operations" if role_name in ["MANAGEMENT", "SECURITY"] else role_name.capitalize(),
                    shift="Morning" if staff_idx % 2 == 0 else "Evening",
                    is_available=True
                )
                db.add(st)
                staff_list.append(st)
                staff_idx += 1
        db.flush()
        print(f"   Created {len(staff_list)} staff members.")

        print("6. Creating Key Reviewer Users & Role Assignments...")
        # 1. Neeraj Kulkarni (Owner of T07-1203)
        u_neeraj = User(phone="9876543210", name="Neeraj Kulkarni", email="neeraj.kulkarni@township.demo")
        db.add(u_neeraj)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_neeraj.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T07-1203"].id))
        db.add(FlatMembership(user_id=u_neeraj.id, flat_id=flats_dict["T07-1203"].id, member_type="OWNER", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 2. Swati Joshi (Tenant in T12-0408)
        u_swati = User(phone="9876543211", name="Swati Joshi", email="swati.joshi@township.demo")
        db.add(u_swati)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_swati.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T12-0408"].id))
        db.add(FlatMembership(user_id=u_swati.id, flat_id=flats_dict["T12-0408"].id, member_type="TENANT", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 3. Aamir Shaikh (Owner of T21-1601)
        u_aamir = User(phone="9876543212", name="Aamir Shaikh", email="aamir.shaikh@township.demo")
        db.add(u_aamir)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_aamir.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T21-1601"].id))
        db.add(FlatMembership(user_id=u_aamir.id, flat_id=flats_dict["T21-1601"].id, member_type="OWNER", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 4. Family Member (Ananya Kulkarni, Family in T07-1203 without pay privileges)
        u_family = User(phone="9876543213", name="Ananya Kulkarni", email="ananya.kulkarni@township.demo")
        db.add(u_family)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_family.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T07-1203"].id))
        db.add(FlatMembership(user_id=u_family.id, flat_id=flats_dict["T07-1203"].id, member_type="FAMILY", can_pay_bills=False, can_approve_visitors=True, can_raise_complaints=True))

        # 5. Help Desk Staff (Ramesh Patil)
        u_helpdesk = User(phone="9876543220", name="Ramesh Patil", email="ramesh.helpdesk@township.demo")
        db.add(u_helpdesk)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_helpdesk.id, role_code="HELPDESK", scope_type="TOWNSHIP"))
        staff_list[160].user_id = u_helpdesk.id
        staff_list[160].name = "Ramesh Patil"

        # 6. Guard (Suresh Shinde)
        u_guard = User(phone="9876543230", name="Suresh Shinde", email="suresh.guard@township.demo")
        db.add(u_guard)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_guard.id, role_code="GUARD", scope_type="GATE", scope_id=gates[0].id))

        # 7. Accounts Staff (Anita Deshmukh)
        u_accounts = User(phone="9876543240", name="Anita Deshmukh", email="anita.accounts@township.demo")
        db.add(u_accounts)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_accounts.id, role_code="ACCOUNTS", scope_type="TOWNSHIP"))

        # 8. Committee Member (Vikram Sardesai)
        u_committee = User(phone="9876543250", name="Vikram Sardesai", email="vikram.committee@township.demo")
        db.add(u_committee)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_committee.id, role_code="COMMITTEE", scope_type="TOWNSHIP"))

        # 9. Admin / Operator
        u_admin = User(phone="9876543200", name="System Admin", email="admin@township.demo")
        db.add(u_admin)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_admin.id, role_code="ADMIN", scope_type="TOWNSHIP"))

        db.flush()

        print("7. Seeding Exact Sample Flat Bills, Ledger Entries & Payments...")
        # 1) T07-1203: 1,150 sqft, Monthly Bill ₹7,475, Paid ₹7,475, Overdue 0, 0 complaints
        f1 = flats_dict["T07-1203"]
        bill1 = Bill(
            flat_id=f1.id,
            billing_rule_id=rule.id,
            billing_rule_version="v1.0-demo",
            period_month=11,
            period_year=2026,
            issue_date=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 11, 15, 0, 0, tzinfo=timezone.utc),
            area_sqft=Decimal("1150.00"),
            rate_per_sqft=Decimal("6.50"),
            principal_amount=Decimal("7475.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("7475.00"),
            paid_amount=Decimal("7475.00"),
            balance_amount=Decimal("0.00"),
            status="PAID"
        )
        db.add(bill1)
        db.flush()
        db.add(BillLine(bill_id=bill1.id, line_type="PRINCIPAL", description="Monthly Maintenance (1,150 sq ft @ ₹6.50/sq ft)", amount=Decimal("7475.00")))
        db.add(FlatLedgerEntry(flat_id=f1.id, entry_type="DEBIT", amount=Decimal("7475.00"), balance_after=Decimal("7475.00"), description="Maintenance Bill - Nov 2026", reference_id=bill1.id, created_at=bill1.issue_date))

        # Payment for T07-1203 (Paid in the first 10 days of the month!)
        p1 = Payment(
            flat_id=f1.id,
            bill_id=bill1.id,
            amount=Decimal("7475.00"),
            currency="INR",
            status="SUCCESS",
            payment_method="UPI_SIMULATED",
            transaction_reference="TXN-SIM-20261103-T071203",
            idempotency_key="IDEM-T07-1203-NOV2026",
            paid_at=datetime(2026, 11, 3, 14, 22, tzinfo=timezone.utc),
            receipt_number="REC-2026-0001",
            payer_user_id=u_neeraj.id
        )
        db.add(p1)
        db.flush()

        r1 = Receipt(
            payment_id=p1.id,
            receipt_number=p1.receipt_number,
            flat_number="T07-1203",
            resident_name="Neeraj Kulkarni",
            amount=Decimal("7475.00"),
            payment_mode="UPI_SIMULATED",
            transaction_reference=p1.transaction_reference,
            issued_at=p1.paid_at
        )
        db.add(r1)
        db.add(FlatLedgerEntry(flat_id=f1.id, entry_type="CREDIT", amount=Decimal("7475.00"), balance_after=Decimal("0.00"), description="Payment received - UPI (Full)", reference_id=p1.transaction_reference, created_at=p1.paid_at))

        # 2) T12-0408: 980 sqft, Monthly Bill ₹6,370, Unpaid (₹0 paid), 47 days overdue as of 2026-11-06
        # Issue date: 2026-09-01, Due date: 2026-09-15. Overdue days = 47 days.
        f2 = flats_dict["T12-0408"]
        bill2 = Bill(
            flat_id=f2.id,
            billing_rule_id=rule.id,
            billing_rule_version="v1.0-demo",
            period_month=9,
            period_year=2026,
            issue_date=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
            area_sqft=Decimal("980.00"),
            rate_per_sqft=Decimal("6.50"),
            principal_amount=Decimal("6370.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("6370.00"),
            paid_amount=Decimal("0.00"),
            balance_amount=Decimal("6370.00"),
            status="OVERDUE"
        )
        db.add(bill2)
        db.flush()
        db.add(BillLine(bill_id=bill2.id, line_type="PRINCIPAL", description="Monthly Maintenance (980 sq ft @ ₹6.50/sq ft)", amount=Decimal("6370.00")))
        db.add(FlatLedgerEntry(flat_id=f2.id, entry_type="DEBIT", amount=Decimal("6370.00"), balance_after=Decimal("6370.00"), description="Maintenance Bill - Sep 2026", reference_id=bill2.id, created_at=bill2.issue_date))

        # 3) T21-1601: 1,640 sqft, Bill ₹10,660, Partially Paid ₹5,000, Outstanding ₹5,660, 18 days overdue
        # Issue date: 2026-10-01, Due date: 2026-10-15. Overdue days = 18 days.
        f3 = flats_dict["T21-1601"]
        bill3 = Bill(
            flat_id=f3.id,
            billing_rule_id=rule.id,
            billing_rule_version="v1.0-demo",
            period_month=10,
            period_year=2026,
            issue_date=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc),
            area_sqft=Decimal("1640.00"),
            rate_per_sqft=Decimal("6.50"),
            principal_amount=Decimal("10660.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("10660.00"),
            paid_amount=Decimal("5000.00"),
            balance_amount=Decimal("5660.00"),
            status="PARTIALLY_PAID"
        )
        db.add(bill3)
        db.flush()
        db.add(BillLine(bill_id=bill3.id, line_type="PRINCIPAL", description="Monthly Maintenance (1,640 sq ft @ ₹6.50/sq ft)", amount=Decimal("10660.00")))
        db.add(FlatLedgerEntry(flat_id=f3.id, entry_type="DEBIT", amount=Decimal("10660.00"), balance_after=Decimal("10660.00"), description="Maintenance Bill - Oct 2026", reference_id=bill3.id, created_at=bill3.issue_date))

        # Partial Payment for T21-1601
        p3 = Payment(
            flat_id=f3.id,
            bill_id=bill3.id,
            amount=Decimal("5000.00"),
            currency="INR",
            status="SUCCESS",
            payment_method="NETBANKING_SIMULATED",
            transaction_reference="TXN-SIM-20261014-T211601",
            idempotency_key="IDEM-T21-1601-OCT2026",
            paid_at=datetime(2026, 10, 14, 11, 10, tzinfo=timezone.utc),
            receipt_number="REC-2026-0002",
            payer_user_id=u_aamir.id
        )
        db.add(p3)
        db.flush()

        r3 = Receipt(
            payment_id=p3.id,
            receipt_number=p3.receipt_number,
            flat_number="T21-1601",
            resident_name="Aamir Shaikh",
            amount=Decimal("5000.00"),
            payment_mode="NETBANKING_SIMULATED",
            transaction_reference=p3.transaction_reference,
            issued_at=p3.paid_at
        )
        db.add(r3)
        db.add(FlatLedgerEntry(flat_id=f3.id, entry_type="CREDIT", amount=Decimal("5000.00"), balance_after=Decimal("5660.00"), description="Partial payment received - NetBanking", reference_id=p3.transaction_reference, created_at=p3.paid_at))

        db.flush()

        print("8. Seeding Sample Complaints & Ten Linked Lift Incidents with 10 Distinct Reporters...")
        # 1. Water leakage complaint for Swati Joshi (T12-0408)
        c1 = Complaint(
            ticket_number="CMP-2026-1001",
            flat_id=f2.id,
            user_id=u_swati.id,
            title="Severe bathroom ceiling water seepage",
            description="Continuous water dripping from the flat above into the master bathroom. Causing ceiling paint damage.",
            category="WATER_SUPPLY",
            urgency="HIGH",
            status="IN_PROGRESS",
            assigned_staff_id=staff_list[0].id,
            created_at=datetime(2026, 11, 4, 9, 15, tzinfo=timezone.utc),
            first_response_at=datetime(2026, 11, 4, 9, 35, tzinfo=timezone.utc)
        )
        db.add(c1)

        # 2. Lift outage primary complaint in Tower 7 (Reported by Neeraj Kulkarni)
        c_lift_primary = Complaint(
            ticket_number="CMP-2026-1002",
            flat_id=f1.id,
            user_id=u_neeraj.id,
            title="Tower 7 Passenger Lift #2 not stopping on 12th floor",
            description="Passenger lift #2 skips floor 12 and makes a loud grinding vibration when descending.",
            category="LIFT",
            urgency="MEDIUM",
            status="ASSIGNED",
            assigned_staff_id=staff_list[31].id,
            created_at=datetime(2026, 11, 5, 8, 20, tzinfo=timezone.utc),
            first_response_at=datetime(2026, 11, 5, 8, 45, tzinfo=timezone.utc)
        )
        db.add(c_lift_primary)
        db.flush()

        # 10 Distinct synthetic residents for 10 separate lift complaints across 10 flats in Tower 7 (D1-S2.4)
        lift_reporter_names = [
            ("Kavita Rao", "9876543301"),
            ("Rajesh Nair", "9876543302"),
            ("Pooja Mehta", "9876543303"),
            ("Sunil Verma", "9876543304"),
            ("Deepa Iyer", "9876543305"),
            ("Manoj Joshi", "9876543306"),
            ("Anand Kadam", "9876543307"),
            ("Sneha Patil", "9876543308"),
            ("Girish Deshpande", "9876543309"),
        ]
        tower_7_flats = [f for f_name, f in flats_dict.items() if f_name.startswith("T07-") and f_name != "T07-1203"][:9]

        for idx_l, (t7_flat, (r_name, r_phone)) in enumerate(zip(tower_7_flats, lift_reporter_names)):
            # Distinct synthetic user & membership
            u_reporter = User(phone=r_phone, name=r_name, email=f"{r_name.lower().replace(' ', '.')}@township.demo")
            db.add(u_reporter)
            db.flush()
            db.add(UserRoleAssignment(user_id=u_reporter.id, role_code="RESIDENT", scope_type="FLAT", scope_id=t7_flat.id))
            db.add(FlatMembership(user_id=u_reporter.id, flat_id=t7_flat.id, member_type="OWNER", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

            t_num = f"CMP-2026-10{idx_l+10}"
            c_lift_dup = Complaint(
                ticket_number=t_num,
                flat_id=t7_flat.id,
                user_id=u_reporter.id,  # Distinct reporter identity!
                title=f"Tower 7 Lift Fault reported by {r_name} ({t7_flat.flat_number})",
                description=f"Resident {r_name} from {t7_flat.flat_number} reports passenger lift #2 is malfunctioning and vibrating.",
                category="LIFT",
                urgency="MEDIUM",
                status="IN_PROGRESS",
                assigned_staff_id=staff_list[31].id,
                duplicate_of_id=c_lift_primary.id,  # Linked to primary incident group, individually open!
                created_at=datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=30 + idx_l * 2)
            )
            db.add(c_lift_dup)

        # 3. Safety escalation incident (Cooking gas odor in Tower 12)
        c_safety = Complaint(
            ticket_number="CMP-2026-1003",
            flat_id=flats_dict["T12-0401"].id,
            user_id=u_admin.id,
            title="Strong LPG gas leak smell near corridor shaft",
            description="LPG gas smell detected near pipeline shaft on 4th floor corridor outside 0401.",
            category="SECURITY",
            urgency="CRITICAL",
            status="IN_PROGRESS",
            is_safety_escalation=True,
            assigned_staff_id=staff_list[60].id,
            created_at=datetime(2026, 11, 6, 7, 10, tzinfo=timezone.utc),
            first_response_at=datetime(2026, 11, 6, 7, 13, tzinfo=timezone.utc)
        )
        db.add(c_safety)

        # 4. Electrical issue (Corridor lighting)
        c_elec = Complaint(
            ticket_number="CMP-2026-1025",
            flat_id=flats_dict["T12-0402"].id,
            user_id=u_admin.id,
            title="Corridor emergency lights flickering in Tower 12",
            description="Corridor light fixture humming and flickering intermittently on the 4th floor.",
            category="ELECTRICAL",
            urgency="LOW",
            status="SUBMITTED",
            created_at=datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc)
        )
        db.add(c_elec)

        # 5. Housekeeping issue (Waste chute)
        c_house = Complaint(
            ticket_number="CMP-2026-1026",
            flat_id=flats_dict["T21-1602"].id,
            user_id=u_admin.id,
            title="Garbage chute blockage on 16th floor",
            description="Waste chute intake door jammed shut with cardboard box.",
            category="CLEANLINESS",
            urgency="MEDIUM",
            status="ASSIGNED",
            assigned_staff_id=staff_list[110].id,
            created_at=datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
        )
        db.add(c_house)

        print("9. Seeding Community Notices & Amenities...")
        n1 = Notice(
            title="Tower 7 Lift #2 Maintenance Underway",
            content="Technicians from Otis are attending to passenger lift #2 in Tower 7. Estimated restoration by 6:00 PM today.",
            target_audience="TOWER",
            target_tower_id=towers[6].id,
            priority="URGENT",
            published_at=datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 11, 7, 23, 59, tzinfo=timezone.utc)
        )
        db.add(n1)

        n2 = Notice(
            title="Township Annual General Meeting (AGM) Notice",
            content="Annual General Meeting of Township One Co-operative Housing Federation is scheduled for 22nd November 2026 at the Main Clubhouse.",
            target_audience="ALL",
            priority="NORMAL",
            published_at=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 11, 23, 23, 59, tzinfo=timezone.utc)
        )
        db.add(n2)

        amenity_data = [
            ("Clubhouse Banquet Hall", "Capacity: 250 guests. Fully air-conditioned.", Decimal("1200.00"), 250, "Pre-booking required."),
            ("Olympic Swimming Pool", "8-lane 50m temperature-controlled pool.", Decimal("0.00"), 40, "Proper swimwear mandatory."),
            ("Badminton Court 1", "Indoor wooden floor court.", Decimal("150.00"), 4, "Non-marking shoes required."),
            ("Badminton Court 2", "Indoor synthetic court.", Decimal("150.00"), 4, "Non-marking shoes required."),
            ("Tennis Court", "Floodlit hard court.", Decimal("200.00"), 4, "Max 1 hour per flat per day."),
            ("Squash Court", "Glass back wall squash court.", Decimal("150.00"), 2, "Goggles recommended.")
        ]
        for a_name, a_desc, a_fee, a_cap, a_rules in amenity_data:
            am = Amenity(name=a_name, description=a_desc, hourly_fee=a_fee, capacity=a_cap, rules=a_rules)
            db.add(am)

        db.commit()
        print("Township One seed completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Township One Safe Database Seeder")
    parser.add_argument(
        "--mode",
        choices=["safe", "reset-demo"],
        default="safe",
        help="Seeding mode: 'safe' (idempotent, non-destructive) or 'reset-demo' (destructive clean reset)"
    )
    parser.add_argument(
        "--confirm-local-demo",
        action="store_true",
        help="Explicit confirmation required to execute destructive reset on local demo database"
    )
    args = parser.parse_args()

    seed_database(mode=args.mode, confirm_local_demo=args.confirm_local_demo)
