# Township One — Feature Status

**Repository:** `https://github.com/Jagadeesh58/Township_one.git`  
**Current Phase:** Core Release (Resident Authentication, Spatial Modeling, Maintenance Billing, Payments & Ledgers)

---

## 1. Feature Status

| Feature | Status | Verified By Test / Command | Notes |
|---|---|---|---|
| **Township Spatial Modeling** | Built | `tests/test_seed.py` | 28 towers, 2,400 flats, 180 staff members, 4 gates |
| **Passwordless Phone OTP Auth** | Built | `tests/test_auth.py` | Persistent `OTPChallenge`, IP & phone rate limits, single-use |
| **Cookie Session & CSRF Protection** | Built | `tests/test_auth.py`, `tests/test_resident_security.py` | `township_session` HttpOnly cookie, double-submit `X-CSRF-Token` |
| **Role-Based Access Control (RBAC)** | Built | `tests/test_auth.py`, `tests/test_resident_security.py` | Database-backed role assignments; committee blocked from individual flats |
| **Maintenance Billing Engine** | Built | `tests/test_billing.py`, `tests/test_money_precision.py` | Area-based calculation (₹6.50/sq ft), leap year simple interest, 5-day grace period |
| **Simulated Payment Gateway** | Built | `tests/test_payments.py`, `tests/test_payment_concurrency.py` | Cryptographic SHA-256 idempotency fingerprinting, outcome simulation |
| **Dual-Entry Accounting Ledger** | Built | `tests/test_integration.py`, `tests/test_resident_security.py` | DEBIT on bill issue, CREDIT on payment, running balance tracking |
| **Decimal Currency Precision** | Built | `tests/test_money_precision.py`, `tests/test_resident_security.py` | Zero binary floating-point drift (`ROUND_HALF_UP` Decimal) |
| **Payment Receipts** | Built | `tests/test_payments.py` | Sequential receipt numbering, tamper-evident transaction references |
| **Resident PWA Interface** | Built | `frontend/src/__tests__/app.test.ts`, `frontend/src/__tests__/components.test.tsx` | Responsive layout (320px–1024px), 2-tap dues payment shortcut, offline shell |
| **Trilingual Localization** | Built | `tests/test_resident_security.py`, `frontend/src/__tests__/components.test.tsx` | English, Marathi, Hindi complete translations |
| **PWA Cache Lifecycle** | Built | `tests/test_resident_security.py`, `frontend/public/sw.js` | App shell pre-caching, network-only bypass for `/api/*`, cache wipe on logout |
| **Committee Aggregate Metrics** | In Progress | `backend/app/api/billing.py::get_committee_aggregate` | High-level collection efficiency and aggregate totals |
| **Bank Statement Reconciliation (MT940/CSV)** | Not built yet | — | Scheduled for future release |
| **Complaint Lifecycle & Helpdesk Dispatch** | Not built yet | — | Scheduled for future release |
| **AI Complaint Classification** | Not built yet | — | Scheduled for future release |
| **Visitor Gate Check-in & Dynamic PINs** | Not built yet | — | Scheduled for future release |
| **Amenity Booking Slot Reservation** | Not built yet | — | Scheduled for future release |
| **Digital Notice Board Publishing** | Not built yet | — | Scheduled for future release |
| **Committee Audit Pack Generator** | Not built yet | — | Scheduled for future release |

---

## 2. Reviewer Personas (Demo Reference Date: `2026-11-06`)

| Persona | Phone | Demo OTP | Role / Flat | State |
|---|---|---|---|---|
| **Neeraj Kulkarni** | `9876543210` | `123456` | Owner, Flat T07-1203 | 1,150 sq ft, fully settled dues (₹7,475.00 paid), ₹0.00 outstanding |
| **Swati Joshi** | `9876543211` | `123456` | Tenant, Flat T12-0408 | 980 sq ft, 47 days overdue (due 2026-09-20), ₹6,370.00 outstanding |
| **Aamir Shaikh** | `9876543212` | `123456` | Owner, Flat T21-1601 | 1,640 sq ft, 18 days overdue (due 2026-10-19), ₹5,660.00 outstanding |
| **Ananya Kulkarni** | `9876543213` | `123456` | Family Member, Flat T07-1203 | Can view dues summary, cannot execute payments |
| **Anita Deshmukh** | `9876543240` | `123456` | Accounts Staff | Authorized for bill generation and financial ledger views |
| **Vikram Sardesai** | `9876543250` | `123456` | Committee Member | Authorized for aggregate metrics; individual flat drilldown blocked |
| **Suresh Shinde** | `9876543230` | `123456` | Security Guard | Gate access; billing and financial records blocked |
| **System Admin** | `9876543200` | `123456` | Administrator | Full administrative authority across all modules |
