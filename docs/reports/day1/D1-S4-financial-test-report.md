# D1-S4 Financial Test Report — Maintenance Billing and Ledger

**Date:** 2026-11-07  
**Session:** D1-S4  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s4_billing.py`  

---

## 1. Execution Summary
- **Total Tests:** 6
- **Passed:** 6
- **Failed:** 0
- **Duration:** 4.54s
- **Status:** PASS

---

## 2. Financial Invariants Validated
1. **Decimal Precision & Rounding:**
   - 1,150.00 sqft @ ₹6.50 = ₹7,475.00
   - 980.00 sqft @ ₹6.50 = ₹6,370.00
   - 1,640.00 sqft @ ₹6.50 = ₹10,660.00
   - Zero floating-point rounding errors.
2. **Grace Period Boundary Logic:**
   - Due date: 15th of the month.
   - 5-day grace period: 16th through 20th.
   - Inspection on 18th (within grace): 0 overdue days, ₹0.00 late fee.
   - Inspection on 20th (cutoff): 0 overdue days, ₹0.00 late fee.
   - Inspection on 22nd (past grace): 7 overdue days accrued from 15th.
3. **Multi-Bill Outstanding Aggregation:**
   - When a flat has multiple unpaid bills, `total_outstanding_due` equals the sum of individual balances.
   - Verified on Swati Joshi with August bill (₹6,370) and September bill (₹6,370) -> Total ₹12,740.00.
4. **Duplicate Bill Rejection:**
   - Generating a second bill for the same flat in the same month/year raises HTTP 409 Conflict.

---

## 3. Command & Output
```bash
py -3.11 -m pytest tests/test_d1_s4_billing.py -v
```
```text
tests/test_d1_s4_billing.py::test_principal_calculation_exact PASSED     [ 16%]
tests/test_d1_s4_billing.py::test_demo_late_fee_boundaries PASSED        [ 33%]
tests/test_d1_s4_billing.py::test_grace_period_enforcement PASSED        [ 50%]
tests/test_d1_s4_billing.py::test_billing_summary_aggregates_multiple_unpaid_bills PASSED [ 66%]
tests/test_d1_s4_billing.py::test_billing_cross_flat_idor_denied PASSED  [ 83%]
tests/test_d1_s4_billing.py::test_duplicate_bill_generation_rejected PASSED [100%]
======================== 6 passed in 4.54s =========================
```
