import os
import sys
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


def seed_database(target_engine=None):
    active_engine = target_engine if target_engine is not None else default_engine
    
    # Environment safety check
    db_url_str = str(active_engine.url)
    if "prod" in db_url_str.lower() and os.environ.get("CONFIRM_PROD_SEED") != "YES_I_AM_SURE":
        raise RuntimeError("Refusing to seed production database without explicit CONFIRM_PROD_SEED=YES_I_AM_SURE")

    print(f"Recreating database tables on: {db_url_str}...")
    Base.metadata.drop_all(bind=active_engine)
    Base.metadata.create_all(bind=active_engine)

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
            name="Maharashtra Society Bye-laws Demo Rule (Pending Federation Approval)",
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
            g = Gate(gate_number=g_num, name=g_name, location_description=g_desc)
            db.add(g)
            gates.append(g)
        db.flush()

        print("3. Creating 28 Towers...")
        towers = []
        for i in range(1, 29):
            t_code = f"T{i:02d}"
            t_name = f"Tower {i}"
            t = Tower(code=t_code, name=t_name, total_floors=22, flats_per_floor=4)
            db.add(t)
            towers.append(t)
        db.flush()

        print("4. Creating 2,400 Flats across 28 Towers...")
        # 20 towers with 86 flats, 8 towers with 85 flats = 20*86 + 8*85 = 1720 + 680 = 2,400 flats!
        flats_dict = {}
        total_flats_created = 0
        areas_pool = [Decimal("980.00"), Decimal("1150.00"), Decimal("1420.00"), Decimal("1640.00")]

        for idx, t in enumerate(towers):
            flats_in_this_tower = 86 if idx < 20 else 85
            for f_idx in range(1, flats_in_this_tower + 1):
                floor = ((f_idx - 1) // 4) + 1
                unit = ((f_idx - 1) % 4) + 1
                f_num = f"{t.code}-{floor:02d}{unit:02d}"

                # Ensure exact sample flat numbers from the brief are present
                if t.code == "T12" and f_idx == 16:
                    f_num = "T12-0408"
                    floor = 4
                elif t.code == "T07" and f_idx == 47:
                    f_num = "T07-1203"
                    floor = 12
                elif t.code == "T21" and f_idx == 61:
                    f_num = "T21-1601"
                    floor = 16

                # Area mapping
                if f_num == "T07-1203":
                    area = Decimal("1150.00")
                elif f_num == "T12-0408":
                    area = Decimal("980.00")
                elif f_num == "T21-1601":
                    area = Decimal("1640.00")
                else:
                    area = areas_pool[f_idx % len(areas_pool)]

                bhk = "2 BHK" if area < Decimal("1000") else ("3 BHK" if area < Decimal("1500") else "4 BHK")
                flat_obj = Flat(
                    tower_id=t.id,
                    flat_number=f_num,
                    floor_number=floor,
                    area_sqft=area,
                    bhk_type=bhk
                )
                db.add(flat_obj)
                flats_dict[f_num] = flat_obj
                total_flats_created += 1

        db.flush()
        print(f"   Created {total_flats_created} flats.")

        print("5. Creating 180 Staff Members...")
        departments = [
            ("Plumbing", 30),
            ("Electrical", 30),
            ("Security", 50),
            ("Housekeeping", 40),
            ("Accounts", 10),
            ("Help Desk & Operations", 20)
        ]
        staff_list = []
        s_counter = 1
        for dept, count in departments:
            for j in range(count):
                st_code = f"STF-{s_counter:03d}"
                st = StaffMember(
                    staff_code=st_code,
                    name=f"Staff {dept[:4]} {j+1}",
                    designation=f"{dept} Specialist" if dept not in ["Security", "Housekeeping"] else f"{dept} Associate",
                    department=dept,
                    shift="Morning" if j % 3 == 0 else ("Evening" if j % 3 == 1 else "Night"),
                    is_available=True
                )
                db.add(st)
                staff_list.append(st)
                s_counter += 1
        db.flush()
        print(f"   Created {len(staff_list)} staff members.")

        print("6. Creating Key Reviewer Users & Role Assignments...")
        # 1. Resident 1 (Sample Flat T07-1203, Neeraj Kulkarni - Owner)
        u_neeraj = User(phone="9876543210", name="Neeraj Kulkarni", email="neeraj.kulkarni@example.com")
        db.add(u_neeraj)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_neeraj.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T07-1203"].id))
        db.add(FlatMembership(flat_id=flats_dict["T07-1203"].id, user_id=u_neeraj.id, member_type="OWNER", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 2. Resident 2 / Tenant (Sample Flat T12-0408, Swati Joshi - Tenant)
        u_swati = User(phone="9876543211", name="Swati Joshi", email="swati.joshi@example.com")
        db.add(u_swati)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_swati.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T12-0408"].id))
        db.add(FlatMembership(flat_id=flats_dict["T12-0408"].id, user_id=u_swati.id, member_type="TENANT", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 3. Resident 3 (Sample Flat T21-1601, Aamir Shaikh - Owner)
        u_aamir = User(phone="9876543212", name="Aamir Shaikh", email="aamir.shaikh@example.com")
        db.add(u_aamir)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_aamir.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T21-1601"].id))
        db.add(FlatMembership(flat_id=flats_dict["T21-1601"].id, user_id=u_aamir.id, member_type="OWNER", can_pay_bills=True, can_approve_visitors=True, can_raise_complaints=True))

        # 4. Family Member Account for T07-1203 (Ananya Kulkarni - Restricted Permission Test)
        u_ananya = User(phone="9876543213", name="Ananya Kulkarni", email="ananya.kulkarni@example.com")
        db.add(u_ananya)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_ananya.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T07-1203"].id))
        # Ananya has visitor & complaint access, but CANNOT pay bills
        db.add(FlatMembership(flat_id=flats_dict["T07-1203"].id, user_id=u_ananya.id, member_type="FAMILY", can_pay_bills=False, can_approve_visitors=True, can_raise_complaints=True))

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
        # 1) T07-1203: 1150 sqft, Monthly Bill 7475, Paid 7475, Overdue 0, 0 complaints
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
            transaction_reference="TXN-T07-20261105-9921",
            idempotency_key="IDEM-SEEDED-T07-PAID",
            paid_at=datetime(2026, 11, 5, 10, 30, tzinfo=timezone.utc),
            receipt_number="REC-202611-00101",
            payer_user_id=u_neeraj.id
        )
        db.add(p1)
        db.flush()
        db.add(Receipt(payment_id=p1.id, receipt_number="REC-202611-00101", flat_number="T07-1203", resident_name="Neeraj Kulkarni", amount=Decimal("7475.00"), payment_mode="UPI", transaction_reference="TXN-T07-20261105-9921", issued_at=p1.paid_at))
        db.add(FlatLedgerEntry(flat_id=f1.id, entry_type="CREDIT", amount=Decimal("7475.00"), balance_after=Decimal("0.00"), description="Payment via UPI - REC-202611-00101", reference_id=p1.id, created_at=p1.paid_at))

        # 2) T12-0408: 980 sqft, Monthly Bill 6370, Paid 0, Overdue 47 days, 1 water leak complaint
        f2 = flats_dict["T12-0408"]
        # Overdue exactly 47 days relative to demo_now (2026-11-06) -> Due date = 2026-09-20
        bill2_due = demo_now - timedelta(days=47)
        bill2 = Bill(
            flat_id=f2.id,
            billing_rule_id=rule.id,
            billing_rule_version="v1.0-demo",
            period_month=9,
            period_year=2026,
            issue_date=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
            due_date=bill2_due,
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
        db.add(FlatLedgerEntry(flat_id=f2.id, entry_type="DEBIT", amount=Decimal("6370.00"), balance_after=Decimal("6370.00"), description="Maintenance Bill - Sept 2026 (Overdue 47 days)", reference_id=bill2.id, created_at=bill2.issue_date))

        # 3) T21-1601: 1640 sqft, Monthly Bill 10660, Paid 5000, Overdue 18 days, 0 complaints
        f3 = flats_dict["T21-1601"]
        # Overdue exactly 18 days relative to demo_now (2026-11-06) -> Due date = 2026-10-19
        bill3_due = demo_now - timedelta(days=18)
        bill3 = Bill(
            flat_id=f3.id,
            billing_rule_id=rule.id,
            billing_rule_version="v1.0-demo",
            period_month=10,
            period_year=2026,
            issue_date=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
            due_date=bill3_due,
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
        
        # Partial payment of 5000
        p3 = Payment(
            flat_id=f3.id,
            bill_id=bill3.id,
            amount=Decimal("5000.00"),
            currency="INR",
            status="SUCCESS",
            payment_method="BANK_TRANSFER",
            transaction_reference="TXN-T21-20261022-8114",
            idempotency_key="IDEM-SEEDED-T21-PARTIAL",
            paid_at=datetime(2026, 10, 22, 14, 15, tzinfo=timezone.utc),
            receipt_number="REC-202610-00445",
            payer_user_id=u_aamir.id
        )
        db.add(p3)
        db.flush()
        db.add(Receipt(payment_id=p3.id, receipt_number="REC-202610-00445", flat_number="T21-1601", resident_name="Aamir Shaikh", amount=Decimal("5000.00"), payment_mode="Bank Transfer", transaction_reference="TXN-T21-20261022-8114", issued_at=p3.paid_at))
        db.add(FlatLedgerEntry(flat_id=f3.id, entry_type="CREDIT", amount=Decimal("5000.00"), balance_after=Decimal("5660.00"), description="Partial Payment - REC-202610-00445", reference_id=p3.id, created_at=p3.paid_at))

        print("8. Seeding Sample Complaints & Ten Linked Lift Incidents...")
        # 1. Swati Joshi's water leak complaint
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

        # 2. Lift outage primary complaint in Tower 7
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

        # Ten separate lift complaints from ten flats in Tower 7 linked to same incident group (Requirement 4.5)
        tower_7_flats = [f for f_name, f in flats_dict.items() if f_name.startswith("T07-") and f_name != "T07-1203"][:9]
        for idx_l, t7_flat in enumerate(tower_7_flats):
            t_num = f"CMP-2026-10{idx_l+10}"
            c_lift_dup = Complaint(
                ticket_number=t_num,
                flat_id=t7_flat.id,
                user_id=u_neeraj.id,  # Associated resident
                title=f"Tower 7 Lift Fault reported by {t7_flat.flat_number}",
                description=f"Resident from {t7_flat.flat_number} reports passenger lift #2 is malfunctioning and vibrating.",
                category="LIFT",
                urgency="MEDIUM",
                status="IN_PROGRESS",
                assigned_staff_id=staff_list[31].id,
                duplicate_of_id=c_lift_primary.id,  # Linked to primary incident group, individually open!
                created_at=datetime(2026, 11, 5, 8, 0, tzinfo=timezone.utc) + timedelta(minutes=30 + idx_l * 2)
            )
            db.add(c_lift_dup)

        # 3. Safety escalation incident (gas odor)
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

        # 4. Electrical complaint
        c_elec = Complaint(
            ticket_number="CMP-2026-1025",
            flat_id=flats_dict["T12-0402"].id,
            user_id=u_admin.id,
            title="Corridor emergency lights flickering in Tower 12",
            description="Corridor light fixture is humming and flickering intermittently on the 4th floor.",
            category="ELECTRICAL",
            urgency="LOW",
            status="SUBMITTED",
            created_at=datetime(2026, 11, 5, 14, 0, tzinfo=timezone.utc)
        )
        db.add(c_elec)

        # 5. Housekeeping complaint
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
            title="Mandatory Water Tank Cleaning - Tower 01 to 14",
            content="Water supply will be temporarily shut off between 10:00 AM and 2:00 PM on Tuesday for scheduled overhead tank disinfection.",
            target_audience="ALL",
            priority="URGENT",
            published_at=datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        )
        n2 = Notice(
            title="Diwali Community Cultural Evening & Fireworks Safety Advisory",
            content="Residents are cordially invited to the grand Diwali celebration at the Central Lawn on Saturday at 6:30 PM. Please use designated zones for eco-friendly fireworks.",
            target_audience="ALL",
            priority="NORMAL",
            published_at=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
        )
        db.add(n1)
        db.add(n2)

        am1 = Amenity(name="Tennis Court 1", description="Floodlit synthetic acrylic surface court", hourly_fee=Decimal("150.00"), capacity=4, rules="Non-marking shoes mandatory. Max 1 hour per flat per day.")
        am2 = Amenity(name="Clubhouse Banquet Hall", description="Air-conditioned party hall with pantry", hourly_fee=Decimal("1200.00"), capacity=100, rules="Pre-booking deposit required. Music allowed till 10 PM.")
        am3 = Amenity(name="Swimming Pool", description="Olympic length lap pool with certified lifeguard", hourly_fee=Decimal("0.00"), capacity=30, rules="Proper swimwear mandatory. Children under 12 must be accompanied.")
        db.add(am1)
        db.add(am2)
        db.add(am3)

        db.commit()
        print("Township One seed completed successfully!")
        return {
            "towers": len(towers),
            "flats": total_flats_created,
            "staff": len(staff_list),
            "gates": len(gates),
        }
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
