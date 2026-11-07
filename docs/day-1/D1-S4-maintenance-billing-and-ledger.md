# D1-S4 — Maintenance Billing and Ledger

**Day:** Day 1  
**Session ID:** D1-S4  
**Session Name:** Maintenance billing and ledger  
**Responsibility:** Bill generation, area/rate calculations, late fees and flat balances  

---

## 1. Objective
Implement deterministic financial calculations using Python's `Decimal` type with half-up rounding. Generate area-based monthly maintenance bills, track grace periods, enforce illustrative demo late fee formulas, maintain double-entry flat ledgers, and aggregate multi-bill balances without data contamination.

---

## 2. Files Created or Modified
- `backend/app/services/billing.py` — Fixed 2-decimal half-up currency rounding, area rate calculation, grace period enforcement, demo late fee computation, bill generation, and ledger bookkeeping.
- `backend/app/schemas/billing.py` — Added `unpaid_bills: List[BillResponse]`, `total_outstanding_due: float`, and `total_outstanding_due_inr: str` to `FlatBillingSummaryResponse`.
- `backend/app/api/billing.py` — Multi-bill balance aggregation in `get_flat_billing_summary()`, committee aggregate metrics, and D1-S4 documentation.
- `tests/test_d1_s4_billing.py` — Test suite for area calculations, late fee boundaries, grace periods, multi-bill aggregation, and IDOR prevention.

---

## 3. Implementation Completed
1. **Precise Area-Based Billing:**
   - Principal calculation: `round_currency(area_sqft * rate_per_sqft)`.
   - Rate: ₹6.50 / sq ft.
   - Example flats:
     - 980 sq ft (T12-0408) = ₹6,370.00
     - 1,150 sq ft (T07-1203) = ₹7,475.00
     - 1,640 sq ft (T21-1601) = ₹10,660.00
2. **Grace Period & Late Fee Boundaries:**
   - Bills are due on the 15th of the billing month.
   - 5-day grace period extends through the 20th of the month.
   - As of the 18th or 20th: 0 overdue days, ₹0.00 late fee.
   - Starting on the 21st (past grace period): overdue days are calculated from the original due date (15th).
   - Late fee formula: 18% p.a. simple interest (`Principal * 0.18 * (Days / 365)`), explicitly labelled: *"Demo Rule (18% p.a. simple interest after 5-day grace period) - pending society federation approval"*.
3. **Multi-Bill Outstanding Aggregation:**
   - When a flat owes multiple unpaid bills, `FlatBillingSummaryResponse` includes:
     - `total_outstanding_due`: sum of balances across all unpaid bills.
     - `unpaid_bills`: array of individual unpaid bills with their specific periods and balances.
4. **Dual-Entry Flat Ledger:**
   - When a bill is generated, a `DEBIT` entry is posted to `FlatLedgerEntry` recording the new outstanding balance.

---

## 4. API Endpoints
- `GET /api/v1/billing/flats/{flat_id}/summary` — Detailed flat billing summary with multi-bill aggregation.
- `GET /api/v1/billing/flats/{flat_id}/bills` — Full bill history for a flat.
- `GET /api/v1/billing/bills/{bill_id}` — Single bill line-item breakdown.
- `GET /api/v1/billing/flats/{flat_id}/ledger` — Chronological ledger statement.
- `GET /api/v1/billing/committee/aggregate` — Township-wide financial metrics (Committee/Admin only).

---

## 5. Tests Executed and Results
Command:
```bash
py -3.11 -m pytest tests/test_d4_s4_billing.py -v
```
Output:
```text
tests/test_d1_s4_billing.py::test_principal_calculation_exact PASSED     [ 16%]
tests/test_d1_s4_billing.py::test_demo_late_fee_boundaries PASSED        [ 33%]
tests/test_d1_s4_billing.py::test_grace_period_enforcement PASSED        [ 50%]
tests/test_d1_s4_billing.py::test_billing_summary_aggregates_multiple_unpaid_bills PASSED [ 66%]
tests/test_d1_s4_billing.py::test_billing_cross_flat_idor_denied PASSED  [ 83%]
tests/test_d1_s4_billing.py::test_duplicate_bill_generation_rejected PASSED [100%]
======================== 6 passed in 4.54s =========================
```

---

## 6. Acceptance Criteria
- [x] Area rate calculations exact to two decimal places.
- [x] Grace period strictly honored (no interest before the 21st).
- [x] Multi-bill dues aggregated into `total_outstanding_due`.
- [x] Duplicate bill generation for the same flat/month rejected with HTTP 409.

---

## 7. Remaining Defects or Limitations
- None. Formula and grace boundaries match Maharashtra cooperative society demo guidelines.
