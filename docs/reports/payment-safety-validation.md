# Payment Safety & Idempotency Validation Report

**Test Suites:**
- `tests/test_payments.py` (10 tests, 100% Passed)
- `tests/test_payment_concurrency.py` (2 tests, 100% Passed)
- `tests/test_money_precision.py` (5 tests, 100% Passed)

---

## 1. Idempotency Key Replay Matrix

| Scenario | Client Action | Server Handling | Result Status | Information Leaked? |
|---|---|---|---|---|
| **Identical Retry** | Resident A submits key `K` with identical bill, flat, and amount | Recognizes completed key; retrieves original payment & voucher | **HTTP 200 OK** (Same payment returned) | None (Owner) |
| **Altered Amount** | Resident A reuses key `K` with altered amount | Detects payload hash divergence | **HTTP 409 Conflict** | None |
| **Altered Bill** | Resident A reuses key `K` with different bill ID | Detects payload hash divergence | **HTTP 409 Conflict** | None |
| **Cross-Resident Collision** | Resident B attempts to submit key `K` used by Resident A | Detects principal user ID mismatch | **HTTP 409 Conflict** | **ZERO LEAKAGE** (Resident A's name, flat, amount, and receipt are completely suppressed) |
| **Short Key (< 8 chars)** | Resident submits key `"test"` | Schema validator rejects key | **HTTP 422 Unprocessable** | None |
| **Missing Key** | Resident omits idempotency key | Schema validator enforces mandatory field | **HTTP 422 Unprocessable** | None |

---

## 2. Concurrency & Race Condition Verification

### 2.1 Identical Key Concurrent Submissions (`test_concurrent_identical_idempotency_requests`)
- **Setup:** 5 concurrent threads executed via `ThreadPoolExecutor` submitting the identical key `K` simultaneously for the same bill and amount.
- **Result:**
  - Exactly 1 thread committed the payment record.
  - Competing threads either received the committed result (HTTP 200) or serialized lock conflict (HTTP 409).
  - Database count: `SELECT COUNT(*) FROM payments WHERE idempotency_key = K` equals **EXACTLY 1**.

### 2.2 Over-Allocation Defense (`test_concurrent_payments_prevent_over_allocation`)
- **Setup:** 4 concurrent threads each attempting to pay the entire remaining balance of a bill simultaneously with distinct idempotency keys.
- **Result:**
  - Exactly 1 thread successfully completed payment (HTTP 200).
  - The remaining 3 threads were rejected with HTTP 400 Bad Request ("cannot exceed current outstanding balance").
  - Final bill balance: ₹0.00.
  - Final paid amount: Does not exceed total bill amount.

---

## 3. Financial Precision & IEEE 754 Float Immunity

Tests in `tests/test_money_precision.py` verify that monetary calculations avoid floating-point drift:
- Floating-point failure: `0.1 + 0.2 = 0.30000000000000004` (Assertion verified in test).
- Decimal immunity: `Decimal("0.10") + Decimal("0.20") == Decimal("0.30")` (Exact match).
- Banker's half-up rounding: `Decimal("10.005") -> Decimal("10.01")`, `Decimal("10.004") -> Decimal("10.00")`.
- Leap year interest calculation: 366 days @ 10% on ₹1,000.00 yields exactly ₹100.00 in leap years (2024), and 365 days @ 10% yields exactly ₹100.00 in non-leap years (2025).
