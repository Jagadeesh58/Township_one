# D1-S5 — Test Payments and Receipts

**Day:** Day 1  
**Session ID:** D1-S5  
**Session Name:** Test payments and receipts  
**Responsibility:** Checkout, idempotency, payment statuses, allocation and receipts  

---

## 1. Objective
Build a secure simulated checkout and payment processing engine. Implement cryptographic request fingerprinting, cross-flat idempotency isolation with zero information leakage, strict payment outcome validation (SUCCESS, PENDING, FAILED, EXPIRED only), over-allocation prevention, and atomic ledger credit/receipt generation.

---

## 2. Files Created or Modified
- `backend/app/schemas/payments.py` — Added `PaymentOutcomeEnum` (SUCCESS, PENDING, FAILED, EXPIRED), field validators for idempotency key, and request/response models.
- `backend/app/services/payments.py` — Implemented SHA-256 request fingerprinting (`user_id:flat_id:bill_id:amount:currency:payment_method:outcome`), `PaymentIdempotencyRecord` lifecycle (`IN_PROGRESS` -> `COMPLETED`), dialect-aware concurrency row locking, over-allocation guard, atomic bill balance deduction, ledger `CREDIT` posting, and receipt generation.
- `backend/app/api/payments.py` — Added checkout, payment retrieval, and receipt retrieval endpoints with strict resident access boundaries.
- `tests/test_d1_s5_payments.py` — Test suite for double-payment rejection, invalid outcome rejection, non-SUCCESS dues preservation, cross-flat key replay without leakage, payload divergence rejection, cross-resident receipt IDOR protection, family permission checks, and over-allocation guards.

---

## 3. Implementation Completed
1. **Cryptographic Idempotency & Information Leakage Prevention:**
   - Idempotency key is stored in dedicated `PaymentIdempotencyRecord` table; it is NOT reused as the transaction reference.
   - Unique payment transaction reference is generated separately: `TXN-SIM-{timestamp}-{uuid}`.
   - Replaying identical payload returns original payment and receipt without duplicating database records.
   - Replaying same key with different amount, bill, flat, or user returns HTTP 409 Conflict.
   - When another resident attempts to use a key already used by another flat, system returns a generic HTTP 409 without revealing any resident, flat, bill, or receipt details.
2. **Strict Outcome Validation:**
   - Valid outcomes: `SUCCESS`, `PENDING`, `FAILED`, `EXPIRED`.
   - Any unknown string (e.g. `TYPO_SUCCESS`, `UNKNOWN`), `null`, or unnormalized value is rejected with HTTP 422 Unprocessable Entity.
   - Non-SUCCESS outcomes (`FAILED`, `PENDING`, `EXPIRED`) create payment audit logs but NEVER alter bill balances, post ledger credits, or issue receipts.
3. **Over-Allocation Prevention & Concurrency:**
   - Payments exceeding the bill's current balance are rejected with HTTP 400 Bad Request (`"cannot exceed current outstanding balance"`).
   - Fully paid bills reject subsequent payment attempts with HTTP 400 Bad Request.
   - Dialect-aware row locking (`with_for_update()`) protects against concurrent balance races in multi-process deployments.
4. **Atomic Ledger Reconciliation & Receipts:**
   - On `SUCCESS`, bill balance is decremented and status updated to `PAID` or `PARTIALLY_PAID`.
   - `FlatLedgerEntry` posts a `CREDIT` with the receipt reference.
   - Official `Receipt` record is created: `REC-{YYYYMM}-{UUID}` with resident name, flat number, amount, and timestamp.

---

## 4. API Endpoints
- `POST /api/v1/payments/checkout` — Executes simulated payment attempt.
- `GET /api/v1/payments/{payment_id}` — Retrieves payment record (scoped to flat owner/tenant).
- `GET /api/v1/payments/receipts/{receipt_number}` — Retrieves official receipt (scoped to flat owner/tenant).

---

## 5. Tests Executed and Results
Command:
```bash
py -3.11 -m pytest tests/test_d1_s5_payments.py -v
```
Output:
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

---

## 6. Acceptance Criteria
- [x] Cross-flat idempotency leak prevented with generic 409.
- [x] Invalid outcomes rejected (HTTP 422).
- [x] Over-allocation prevented (HTTP 400).
- [x] SUCCESS atomically produces ledger credit and receipt.

---

## 7. Remaining Defects or Limitations
- Test/simulated payment mode only; bank gateway webhooks scheduled for production phase.
