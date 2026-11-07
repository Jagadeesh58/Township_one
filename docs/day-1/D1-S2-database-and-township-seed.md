# D1-S2 — Database and Township Seed

**Day:** Day 1  
**Session ID:** D1-S2  
**Session Name:** Database and township seed  
**Responsibility:** 28 towers, 2,400 flats, 180 staff, four gates and exact sample data  

---

## 1. Objective
Populate the database with the exact structural scale specified in Challenge Brief 2 (Company A Township in Pune): exactly 28 towers, 2,400 flats, 180 staff, 4 security gates, and exact reviewer test personas with correct financial dues and complaints. Implement strict fail-closed safety guards against accidental resets of hosted or production databases.

---

## 2. Files Created or Modified
- `seed/seed_data.py` — Complete seed script with `is_safe_local_database()` safety checks, fail-closed confirmation flags (`--mode reset-demo --confirm-local-demo` or `CONFIRM_LOCAL_DEMO_RESET=true`), and generation of 10 distinct synthetic lift complaint reporters.
- `backend/app/models/entities.py` — Entity schema validations for `Gate`, `StaffMember`, `Flat`, `FlatMembership`, `Amenity`, `Complaint`, `Bill`, and `Payment`.
- `tests/test_d1_s2_seed.py` — Seed validation suite checking entity counts, sample flats, distinct lift reporters, reviewer roles, and destructive reset guards.

---

## 3. Implementation Completed
1. **Township Scale Validation:**
   - Towers: Exactly 28 towers (T01 through T28).
   - Flats: Exactly 2,400 flats across 28 towers.
   - Staff: Exactly 180 staff members across Security (80), Housekeeping (50), Maintenance (35), and Admin/Accounts (15).
   - Gates: Exactly 4 security gates (North Main, South Express, East Commercial, West Service).
2. **Reviewer Persona Flats:**
   - **Flat T07-1203:** Neeraj Kulkarni (Owner, 1,150 sq ft, 2 BHK, ₹7,475.00 maintenance, Fully Paid, zero balance). Family member Ananya Kulkarni (`can_pay_bills=False`).
   - **Flat T12-0408:** Swati Joshi (Tenant, 980 sq ft, 2 BHK, ₹6,370.00 maintenance, Overdue >40 days, balance ₹6,370.00).
   - **Flat T21-1601:** Aamir Shaikh (Owner, 1,640 sq ft, 3 BHK, ₹10,660.00 maintenance, Partially Paid ₹5,000.00, balance ₹5,660.00, Overdue >15 days).
3. **10 Distinct Synthetic Reporters for Lift Complaint:**
   Synthetic lift emergency `CMP-2026-1002` ("Tower 7 Passenger Lift 2 Jerking Between 11th and 12th Floor") is linked to 10 distinct resident reporters (Kavita Rao, Rajesh Nair, Pooja Mehta, Sunil Verma, Deepa Iyer, Manoj Joshi, Sangeeta Kale, Arvind Kadam, Vandana Deshpande, Alok Pathak) across Tower 7, all active and SLA-tracked.
4. **Fail-Closed Seed Reset Safety:**
   - `is_safe_local_database()` rejects remote/cloud URLs (`neon.tech`, `amazonaws.com`, `supabase.co`, etc.).
   - Destructive `--mode reset-demo` strictly requires explicit `--confirm-local-demo` or env flag `CONFIRM_LOCAL_DEMO_RESET=true`.
   - Non-destructive `--mode safe` provides safe upserting.

---

## 4. Database Schema Entities
- `Tower` (id, code, name, total_floors, total_flats)
- `Flat` (id, tower_id, flat_number, floor_number, bhk_type, area_sqft)
- `Gate` (id, gate_number, name, location_description)
- `StaffMember` (id, staff_code, name, phone, designation, department, shift, is_available)
- `BillingRule` (id, name, version, rate_per_sqft, due_day_of_month, grace_period_days, late_fee_percentage_pa, is_active)
- `Bill` & `BillLine` (id, flat_id, period_month, period_year, principal_amount, late_fee_amount, total_amount, paid_amount, balance_amount, status)
- `Complaint` (id, ticket_number, flat_id, category, title, description, priority, status, sla_due_at)

---

## 5. Tests Executed and Results
Command:
```bash
py -3.11 -m pytest tests/test_d1_s2_seed.py -v
```
Output:
```text
tests/test_d1_s2_seed.py::test_seed_entity_counts PASSED                 [ 11%]
tests/test_d1_s2_seed.py::test_sample_flat_t07_1203_exact_values PASSED  [ 22%]
tests/test_d1_s2_seed.py::test_sample_flat_t12_0408_exact_values PASSED  [ 33%]
tests/test_d1_s2_seed.py::test_sample_flat_t21_1601_exact_values PASSED  [ 44%]
tests/test_d1_s2_seed.py::test_family_member_permission_boundaries PASSED [ 55%]
tests/test_d1_s2_seed.py::test_ten_linked_lift_complaints_with_distinct_reporters PASSED [ 66%]
tests/test_d1_s2_seed.py::test_reviewer_role_assignments PASSED          [ 77%]
tests/test_d1_s2_seed.py::test_seed_safety_rejects_unconfirmed_destructive_reset PASSED [ 88%]
tests/test_d1_s2_seed.py::test_seed_safety_rejects_remote_database_urls PASSED [100%]
======================== 9 passed in 4.57s =========================
```

---

## 6. Acceptance Criteria
- [x] Exactly 28 towers, 2,400 flats, 180 staff, 4 gates verified.
- [x] Sample flats T07-1203, T12-0408, T21-1601 have exact specified financial statuses.
- [x] 10 distinct reporters linked to Tower 7 lift complaint.
- [x] Unconfirmed or remote destructive resets fail closed.

---

## 7. Remaining Defects or Limitations
- None. Fully seeded and verified.
