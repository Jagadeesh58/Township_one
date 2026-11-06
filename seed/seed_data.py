import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import random

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.entities import (
    User, UserRoleAssignment, Tower, Flat, FlatMembership,
    StaffMember, Gate, BillingRule, Bill, BillLine, Payment,
    FlatLedgerEntry, Receipt, Complaint, Notice, Amenity
)


def seed_database():
    print("Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
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
        now_dt = datetime.now(timezone.utc)

        # Standard areas
        areas_pool = [Decimal("980.00"), Decimal("1150.00"), Decimal("1420.00"), Decimal("1640.00")]

        for idx, t in enumerate(towers):
            flats_in_this_tower = 86 if idx < 20 else 85
            for f_idx in range(1, flats_in_this_tower + 1):
                # Standard floor and unit
                floor = ((f_idx - 1) // 4) + 1
                unit = ((f_idx - 1) % 4) + 1
                f_num = f"{t.code}-{floor:02d}{unit:02d}"

                # Ensure exact sample flat numbers from the brief are present
                if t.code == "T12" and f_idx == 16:  # Replace one flat in T12 with T12-0408
                    f_num = "T12-0408"
                    floor = 4
                elif t.code == "T07" and f_idx == 47: # Replace one flat in T07 with T07-1203
                    f_num = "T07-1203"
                    floor = 12
                elif t.code == "T21" and f_idx == 61: # Replace one flat in T21 with T21-1601
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
        # 180 on-site staff across departments
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
        # 1. Resident 1 (Sample Flat T07-1203, Neeraj Kulkarni)
        u_neeraj = User(phone="9876543210", name="Neeraj Kulkarni", email="neeraj.kulkarni@example.com")
        db.add(u_neeraj)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_neeraj.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T07-1203"].id))
        db.add(FlatMembership(flat_id=flats_dict["T07-1203"].id, user_id=u_neeraj.id, member_type="OWNER"))

        # 2. Resident 2 / Tenant (Sample Flat T12-0408, Swati Joshi)
        u_swati = User(phone="9876543211", name="Swati Joshi", email="swati.joshi@example.com")
        db.add(u_swati)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_swati.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T12-0408"].id))
        db.add(FlatMembership(flat_id=flats_dict["T12-0408"].id, user_id=u_swati.id, member_type="TENANT"))

        # 3. Resident 3 (Sample Flat T21-1601, Aamir Shaikh)
        u_aamir = User(phone="9876543212", name="Aamir Shaikh", email="aamir.shaikh@example.com")
        db.add(u_aamir)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_aamir.id, role_code="RESIDENT", scope_type="FLAT", scope_id=flats_dict["T21-1601"].id))
        db.add(FlatMembership(flat_id=flats_dict["T21-1601"].id, user_id=u_aamir.id, member_type="OWNER"))

        # 4. Help Desk Staff (Ramesh Patil)
        u_helpdesk = User(phone="9876543220", name="Ramesh Patil", email="ramesh.helpdesk@township.demo")
        db.add(u_helpdesk)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_helpdesk.id, role_code="HELPDESK", scope_type="TOWNSHIP"))
        # Link to staff member
        staff_list[160].user_id = u_helpdesk.id
        staff_list[160].name = "Ramesh Patil"

        # 5. Guard (Suresh Shinde)
        u_guard = User(phone="9876543230", name="Suresh Shinde", email="suresh.guard@township.demo")
        db.add(u_guard)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_guard.id, role_code="GUARD", scope_type="GATE", scope_id=gates[0].id))

        # 6. Accounts Staff (Anita Deshmukh)
        u_accounts = User(phone="9876543240", name="Anita Deshmukh", email="anita.accounts@township.demo")
        db.add(u_accounts)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_accounts.id, role_code="ACCOUNTS", scope_type="TOWNSHIP"))

        # 7. Committee Member (Vikram Sardesai)
        u_committee = User(phone="9876543250", name="Vikram Sardesai", email="vikram.committee@township.demo")
        db.add(u_committee)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_committee.id, role_code="COMMITTEE", scope_type="TOWNSHIP"))

        # 8. Admin / Operator
        u_admin = User(phone="9876543200", name="System Admin", email="admin@township.demo")
        db.add(u_admin)
        db.flush()
        db.add(UserRoleAssignment(user_id=u_admin.id, role_code="ADMIN", scope_type="TOWNSHIP"))

        db.flush()

        print("7. Seeding Exact Sample Flat Bills, Ledger Entries & Payments...")
        # Exact Brief Data:
        # 1) T07-1203: 1150 sqft, Monthly Bill 7475, Paid 7475, Overdue 0, 0 complaints
        f1 = flats_dict["T07-1203"]
        bill1 = Bill(
            flat_id=f1.id,
            billing_rule_id=rule.id,
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
        db.add(FlatLedgerEntry(flat_id=f1.id, entry_type="DEBIT", amount=Decimal("7475.00"), balance_after=Decimal("7475.00"), description="Maintenance Bill - Nov 2026", reference_id=bill1.id))
        
        # Payment for T07-1203 (Paid in the first 10 days of the month!)
        p1 = Payment(
            flat_id=f1.id,
            bill_id=bill1.id,
            amount=Decimal("7475.00"),
            status="SUCCESS",
            payment_method="UPI_SIMULATED",
            transaction_reference="UPI-T07-20261105-9921",
            paid_at=datetime(2026, 11, 5, 10, 30, tzinfo=timezone.utc),
            receipt_number="REC-202611-00101",
            payer_user_id=u_neeraj.id
        )
        db.add(p1)
        db.flush()
        db.add(Receipt(payment_id=p1.id, receipt_number="REC-202611-00101", flat_number="T07-1203", resident_name="Neeraj Kulkarni", amount=Decimal("7475.00"), payment_mode="UPI", transaction_reference="UPI-T07-20261105-9921", issued_at=p1.paid_at))
        db.add(FlatLedgerEntry(flat_id=f1.id, entry_type="CREDIT", amount=Decimal("7475.00"), balance_after=Decimal("0.00"), description="Payment via UPI - REC-202611-00101", reference_id=p1.id))

        # 2) T12-0408: 980 sqft, Monthly Bill 6370, Paid 0, Overdue 47 days, 1 water leak complaint
        f2 = flats_dict["T12-0408"]
        # Overdue by 47 days relative to Nov 6 2026 -> Due date ~ Sept 20 2026
        bill2 = Bill(
            flat_id=f2.id,
            billing_rule_id=rule.id,
            period_month=9,
            period_year=2026,
            issue_date=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc),
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
        db.add(FlatLedgerEntry(flat_id=f2.id, entry_type="DEBIT", amount=Decimal("6370.00"), balance_after=Decimal("6370.00"), description="Maintenance Bill - Sept 2026 (Overdue 47 days)", reference_id=bill2.id))

        # 3) T21-1601: 1640 sqft, Monthly Bill 10660, Paid 5000, Overdue 18 days, 0 complaints
        f3 = flats_dict["T21-1601"]
        # Overdue 18 days relative to Nov 6 2026 -> Due date ~ Oct 19 2026
        bill3 = Bill(
            flat_id=f3.id,
            billing_rule_id=rule.id,
            period_month=10,
            period_year=2026,
            issue_date=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc),
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
        db.add(FlatLedgerEntry(flat_id=f3.id, entry_type="DEBIT", amount=Decimal("10660.00"), balance_after=Decimal("10660.00"), description="Maintenance Bill - Oct 2026", reference_id=bill3.id))
        
        # Partial payment of 5000
        p3 = Payment(
            flat_id=f3.id,
            bill_id=bill3.id,
            amount=Decimal("5000.00"),
            status="SUCCESS",
            payment_method="BANK_TRANSFER",
            transaction_reference="NEFT-T21-20261022-8114",
            paid_at=datetime(2026, 10, 22, 14, 15, tzinfo=timezone.utc),
            receipt_number="REC-202610-00445",
            payer_user_id=u_aamir.id
        )
        db.add(p3)
        db.flush()
        db.add(Receipt(payment_id=p3.id, receipt_number="REC-202610-00445", flat_number="T21-1601", resident_name="Aamir Shaikh", amount=Decimal("5000.00"), payment_mode="Bank Transfer", transaction_reference="NEFT-T21-20261022-8114", issued_at=p3.paid_at))
        db.add(FlatLedgerEntry(flat_id=f3.id, entry_type="CREDIT", amount=Decimal("5000.00"), balance_after=Decimal("5660.00"), description="Partial Payment - REC-202610-00445", reference_id=p3.id))

        print("8. Seeding Sample Complaint Scenarios...")
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

        # 2. Lift outage reported in Tower 7 (candidate duplicate scenario)
        c2 = Complaint(
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
        db.add(c2)

        # 3. Safety escalation incident (gas odor)
        c3 = Complaint(
            ticket_number="CMP-2026-1003",
            flat_id=flats_dict["T12-0401"].id,
            user_id=u_admin.id,
            title="Strong LPG gas leak smell near corridor shaft",
            description="LPG gas smell detected near pipeline shaft on 4th floor corridor outside 0407.",
            category="SECURITY",
            urgency="CRITICAL",
            status="IN_PROGRESS",
            is_safety_escalation=True,
            assigned_staff_id=staff_list[60].id,
            created_at=datetime(2026, 11, 6, 7, 10, tzinfo=timezone.utc),
            first_response_at=datetime(2026, 11, 6, 7, 13, tzinfo=timezone.utc)
        )
        db.add(c3)

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
