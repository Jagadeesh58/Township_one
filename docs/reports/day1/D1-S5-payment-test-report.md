# D1-S5 Payment Test Report — Test Payments and Receipts

**Date:** 2026-11-07  
**Session:** D1-S5  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s5_payments.py`  

---

## 1. Execution Summary
- **Total Tests:** 8
- **Passed:** 8
- **Failed:** 0
- **Duration:** 7.79s
- **Status:** PASS

---

## 2. Payment Invariants Validated
1. **Double Payment Prevention:**
   - Attempting to pay an already-paid bill (T07-1203) returns HTTP 400 Bad Request.
2. **Strict Outcome Validation:**
   - `TYPO_SUCCESS`, `UNKNOWN`, `null`, and lowercase `success` are rejected with HTTP 422 Unprocessable Entity.
   - Zero side-effects: dues remain unchanged, no payment record created.
3. **Non-SUCCESS Outcomes:**
   - `FAILED`, `PENDING`, `EXPIRED` record payment status but do NOT alter dues or generate receipts.
4. **Cross-Flat Idempotency Key Isolation:**
   - Reusing another resident's key returns generic HTTP 409 without revealing any resident, flat, bill, or receipt info.
5. **Payload Divergence Rejection:**
   - Reusing same key with altered amount returns HTTP 409 Conflict.
   - Replaying identical payload returns original payment and receipt.
6. **Receipt and Payment IDOR Protection:**
   - Resident B cannot view Resident A's receipt or payment (HTTP 403 Forbidden).
7. **Over-Allocation Prevention:**
   - Submitting an amount exceeding the current balance returns HTTP 400 Bad Request.

---

## 3. Command & Output
```bash
py -3.11 -m pytest tests/test_d1_s5_payments.py -v
```
```text
tests/test_d1_s5_payments.py::test_pay_already_paid_bill_rejected PASSED [ 12%]
tests/test_d1_s5_payments.py::test_invalid_payment_outcomes_rejected PASSED [ 25%]
tests/test_d1_s5_payments.py::test_payment_failure_pending_expired_leaves_dues_intact PASSED [ 37%]
tests/test_d1_s5_payments.py::test_cross_flat_idempotency_key_replay_and_leakage_prevention PASSED [ 50%]
tests/test_d1_s5_payments.py::test_idempotency_key_payload_divergence_returns_409 PASSED [ 62%]
tests/test_d1_s5_payments.py::test_cross_resident_receipt_and_payment_access_denied PASSED [ 75%]
tests/test_d1_s5_payments.py::test_family_member_without_pay_permission_blocked PASSED [ 87%]
tests/test_d1_s5_payments.py::test_payment_exceeding_balance_rejected PASSED [100%]
======================== 8 passed in 7.79s =========================
```
