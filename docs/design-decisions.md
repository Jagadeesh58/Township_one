# TOWNSHIP ONE — DESIGN DECISIONS (ADR SUMMARY)

---

## ADR 001: Cryptographic Request Fingerprinting for Idempotent Payments
- **Context:** Payment retries must be idempotent, but naive implementations either reuse the idempotency key as the transaction reference or expose one resident's payment data when another resident submits a conflicting key.
- **Decision:** Separate `idempotency_key` (stored in `PaymentIdempotencyRecord`) from `transaction_reference` (`TXN-SIM-...`). Hash the request payload using SHA-256 (`user_id:flat_id:bill_id:amount:currency:payment_method:outcome`). If another user reuses a key, return a generic HTTP 409 without disclosing any metadata.
- **Consequences:** Eliminates payment data leakage, satisfies PCI-DSS & OWASP privacy guidelines, prevents duplicate debits.

---

## ADR 002: Strict State Machine for Payment Outcomes
- **Context:** Test payment endpoints can accidentally treat unverified outcomes or typo strings (e.g. `TYPO_SUCCESS`, `UNKNOWN`) as valid transactions.
- **Decision:** Enforce server-side `PaymentOutcomeEnum` accepting strictly `SUCCESS`, `PENDING`, `FAILED`, and `EXPIRED`. Invalid values return HTTP 422 immediately with zero database writes.
- **Consequences:** Unvalidated strings can never alter balances or issue receipts. Non-SUCCESS outcomes record an audit log but preserve unpaid dues.

---

## ADR 003: Strict Role-Based Access Control on Financial Endpoints
- **Context:** In large townships, Committee Members and Security Guards have broad administrative or physical authority, creating potential risk of financial data inspection.
- **Decision:** Bar Committee members from individual flat billing summaries (`/flats/{id}/summary`); permit only aggregate statistical endpoints (`/committee/aggregate`). Bar Security Guards from all billing and payment endpoints.
- **Consequences:** Strict resident financial confidentiality adhering to DPDP Act 2023 principles.

---

## ADR 004: Fail-Closed Seed and Database Migration Policy
- **Context:** Running seed or test scripts against hosted/remote production databases can cause catastrophic data loss.
- **Decision:** Implement `is_safe_local_database()` in `seed_data.py` to reject remote hostnames (Neon, RDS, Supabase). Require `--confirm-local-demo` or `CONFIRM_LOCAL_DEMO_RESET=true` for destructive drops. Fail Alembic migrations fast if dynamic URL cannot be resolved.
- **Consequences:** Destructive commands cannot execute accidentally against cloud databases.
