# Township One — Implementation Status & Requirement Matrix

## 1. Scope Boundary & Release Summary

Township One is delivered as a verified, production-ready core release implementing resident authentication, township data architecture, maintenance billing, test payments, running accounting ledgers, and a bilingual PWA resident experience.

| Requirement Area | Planned Scope | Implementation Status | Automated Verification |
|---|---|---|---|
| **Township Foundation** | 28 towers, 2,400 flats, 180 staff, 4 gates | **Complete** | `tests/test_seed.py` (Passed) |
| **Authentication & RBAC** | Passwordless phone OTP, single-use, JTI revocation, permissions | **Complete** | `tests/test_auth.py` (Passed) |
| **Maintenance Billing** | Area-rate tariff (₹6.50/sq ft), grace period, leap year, multi-bill aggregation | **Complete** | `tests/test_billing.py` (Passed) |
| **Payment Gateway** | Idempotency locking, request fingerprinting, conflict handling, vouchers | **Complete** | `tests/test_payments.py`, `tests/test_payment_concurrency.py` (Passed) |
| **Resident PWA** | 2-tap payment CTA, multi-bill selection, offline app shell, trilingual i18n | **Complete** | `frontend/src/__tests__/app.test.ts` (Passed), Vite Build (Passed) |
| **Accounting Ledger** | Dual-entry DEBIT/CREDIT records, running post-transaction balances | **Complete** | `tests/test_integration.py` (Passed) |
| **Financial Precision** | Decimal arithmetic (ROUND_HALF_UP), binary float immunity | **Complete** | `tests/test_money_precision.py` (Passed) |

---

## 2. Verified Persona Checklist

The local demo database (`township_one.db`) is fully initialized with verified sample personas as of **`2026-11-06`**:

- [x] **Neeraj Kulkarni (Flat T07-1203):**
  - Phone: `9876543210` (Demo OTP: `123456`)
  - Status: Owner, 1,150 sq ft, Fully Paid (₹7,475.00), Outstanding Due: ₹0.00.
- [x] **Swati Joshi (Flat T12-0408):**
  - Phone: `9876543211` (Demo OTP: `123456`)
  - Status: Tenant, 980 sq ft, Unpaid Bill due 2026-09-20 (Exactly 47 days overdue), Outstanding Due: ₹6,370.00.
- [x] **Aamir Shaikh (Flat T21-1601):**
  - Phone: `9876543212` (Demo OTP: `123456`)
  - Status: Owner, 1,640 sq ft, Partially Paid ₹5,000.00 due 2026-10-19 (Exactly 18 days overdue), Outstanding Due: ₹5,660.00.
- [x] **Ananya Kulkarni (Flat T07-1203):**
  - Phone: `9876543213` (Demo OTP: `123456`)
  - Status: Family Member, `can_pay_bills = False` (View permitted, payment blocked).
- [x] **Vikram Sardesai (Management Committee):**
  - Phone: `9876543250` (Demo OTP: `123456`)
  - Status: Committee Member, Authorized for Township Aggregate Metrics, Blocked from Individual Flats.
- [x] **Suresh Shinde (Gate Security):**
  - Phone: `9876543230` (Demo OTP: `123456`)
  - Status: Security Guard, Authorized for Gate Passes, Blocked from Financial Ledgers.

---

## 3. Product Roadmap (Future Phases)

The following modules represent future planned phases beyond the current release:
- **Phase 2 (Operations & Service Delivery):** Multi-tenant complaint lifecycle, automatic category-based staff routing, SLA breach notifications, and photo attachments.
- **Phase 3 (Security & Visitor Access):** Fast-pass QR generation, offline gate tablet sync via IndexedDB, and automated 90-day DPDP photo purging.
- **Phase 4 (Treasury & Committee Governance):** Bank statement reconciliation parser (CSV/MT940), automated match score heuristic, and committee audit pack generator.
