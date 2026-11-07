# D1-S2 Seed Validation Report — Database and Township Seed

**Date:** 2026-11-07  
**Session:** D1-S2  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s2_seed.py`  

---

## 1. Execution Summary
- **Total Tests:** 9
- **Passed:** 9
- **Failed:** 0
- **Duration:** 4.57s
- **Status:** PASS

---

## 2. Seed Invariants Validated
1. **Township Scale Metrics:**
   - Towers: 28 (T01 through T28)
   - Flats: 2,400 total
   - Staff Members: 180 (80 Guards, 50 Housekeeping, 35 Maintenance, 15 Admin/Accounts)
   - Gates: 4 (North Main Gate 1, South Express Gate 2, East Commercial Gate 3, West Service Gate 4)
2. **Reviewer Demo Personas:**
   - **T07-1203:** Neeraj Kulkarni (Owner, 1,150 sqft, ₹7,475.00 billed, ₹7,475.00 paid, ₹0.00 balance)
   - **T12-0408:** Swati Joshi (Tenant, 980 sqft, ₹6,370.00 billed, ₹0.00 paid, ₹6,370.00 balance, overdue >40 days)
   - **T21-1601:** Aamir Shaikh (Owner, 1,640 sqft, ₹10,660.00 billed, ₹5,000.00 paid, ₹5,660.00 balance, overdue >15 days)
3. **Emergency Incident Validation:**
   - Ticket `CMP-2026-1002` ("Tower 7 Passenger Lift 2 Jerking Between 11th and 12th Floor") is backed by 10 distinct resident reporters living in Tower 7.
4. **Seed Reset Policy:**
   - Unconfirmed `--mode reset-demo` fails closed with code 1.
   - Remote database URLs are blocked.

---

## 3. Command & Output
```bash
py -3.11 -m pytest tests/test_d1_s2_seed.py -v
```
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
