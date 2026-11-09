# Township One — Feature Status

**Repository:** `https://github.com/Jagadeesh58/Township_one.git`  

---

## 1. Feature Status

| Feature | Status | Verified By Test / Command | Notes |
|---|---|---|---|
| **Township Spatial Modeling** | Built | `tests/test_seed.py` | 28 towers, 2,400 flats, 180 staff members, 4 gates |
| **Passwordless Phone OTP Auth** | Built | `tests/test_auth.py` | Persistent `OTPChallenge`, IP & phone rate limits, single-use |
| **Cookie Session & CSRF Protection** | Built | `tests/test_auth.py`, `tests/test_permissions_regression.py` | `township_session` HttpOnly cookie, double-submit `X-CSRF-Token` |
| **Role-Based Access Control (RBAC)** | Built | `tests/test_permissions_regression.py` | Server-side role boundaries for Resident, Help Desk, Accounts, Guard, Committee |
| **Maintenance Billing Engine** | Built | `tests/test_billing.py`, `tests/test_money_precision.py` | Area-based calculation (₹6.50/sq ft), leap year simple interest, 5-day grace period |
| **Simulated Payment Gateway** | Built | `tests/test_payments.py`, `tests/test_payment_concurrency.py` | Cryptographic SHA-256 idempotency fingerprinting, outcome simulation |
| **Dual-Entry Accounting Ledger** | Built | `tests/test_resident_security.py` | DEBIT on bill issue, CREDIT on payment, running balance tracking |
| **Decimal Currency Precision** | Built | `tests/test_money_precision.py`, `tests/test_resident_security.py` | Zero binary floating-point drift (`ROUND_HALF_UP` Decimal) |
| **Payment Receipts** | Built | `tests/test_payments.py` | Sequential receipt numbering, tamper-evident transaction references |
| **Bank Statement Matching Engine** | Built | `tests/test_bank_matching.py` | Canonical statement preview, deterministic safety rules, 60 / 385 rows auto-matched (15.58% coverage), 325 rows held for review with non-empty reasons, 0 false auto-postings verified, review queue |
| **Complaint Lifecycle State Machine** | Built | `tests/test_complaints.py` | Explicit state transitions (HTTP 409 Conflict on illegal transition), flat-scoping, rating & reopen |
| **Trilingual Emergency Detection** | Built | `tests/test_complaints.py`, `tests/test_ml.py` | Deterministic regex detector across en/hi/mr forcing CRITICAL urgency and SafetyEvent |
| **AI Complaint Classification & Fallback** | Built | `tests/test_ml.py` | Groq API client with local TF-IDF + MultinomialNB fallback trained on 360-row multilingual dataset |
| **Semantic Duplicate Detection** | Built | `tests/test_complaints.py`, `tests/test_ml.py` | Character n-gram TF-IDF cosine similarity with incident group linking |
| **Private Photo Streaming** | Built | `tests/test_complaints.py`, `tests/test_visitors.py` | Pillow MIME verification, EXIF stripping, 5-minute signed streaming |
| **Accounts Workspace UI** | Built | `frontend/src/__tests__/features.test.tsx` | Statement upload, preview table, commit action, review queue handlers |
| **Help Desk Queue UI** | Built | `frontend/src/__tests__/features.test.tsx` | Status/category/urgency filters, SLA badges, AI evidence card, one-tap optimistic correction |
| **Resident Complaints UI** | Built | `frontend/src/__tests__/features.test.tsx` | Ticket submission with photo upload, my complaints, 1-5 star resolution rating, reopen request |
| **Notification Bell & In-App Alerts** | Built | `frontend/src/__tests__/features.test.tsx` | Unread badge count, safety escalation alerts, mark-all-read |
| **Trilingual Localization** | Built | `frontend/src/__tests__/translations.test.ts` | English, Marathi, and Hindi translations |
| **PWA Cache Lifecycle** | Built | `frontend/src/__tests__/serviceWorker.test.ts` | App shell pre-caching, network-only bypass for `/api/*`, cache wipe on logout |
| **Visitor Entry & Lifecycle** | Built | `tests/test_visitors.py` | State machine (ARRIVED -> AWAITING_APPROVAL -> APPROVED/REJECTED -> ADMITTED -> EXITED), photo upload with EXIF removal, 90-day retention purge CLI, supervisor override with mandatory justification |
| **Pre-Approved Guest Passes & Offline Crypto** | Built | `tests/test_guest_codes.py` | 6-digit one-time code verification, single-use counter decrement, ECDSA P-256 compact credential verification for offline gate terminals, gate time-anchor and public key endpoints |
| **Guard Gate Terminal UI** | Built | `frontend/src/pages/GuardGateTerminal.tsx` | Gate switcher (1-4), online/offline status badge, guest pass verification, visitor arrival recorder with photo upload, live entries log, admit/exit/supervisor-override actions, outdoor night theme toggle, touch targets >= 48px |
| **Amenity Booking & Concurrency Locking** | Built | `tests/test_amenities.py`, `frontend/src/pages/AmenityBookingPage.tsx` | Slot listing with capacity counter, idempotency key enforcement, flat daily booking limit (HTTP 409), cancellation workflow with 2-hour cutoff, amenity closure manager cancelling conflicting bookings |
| **Community Notice Board** | Built | `tests/test_notices.py`, `frontend/src/pages/ResidentHomePage.tsx` | Immutable revision history (append-only), tower-targeted scoping, trilingual support with automatic language fallback indicator ("Shown in English"), read tracking per user per revision |
| **Committee Governance & Dues Ageing** | Built | `tests/test_committee.py`, `frontend/src/pages/CommitteeDashboard.tsx` | Mathematical dues ageing reconciliation (0-30, 31-60, 61-90, 90+ days summing exactly to total outstanding), complaint SLA turnaround metrics, ReportLab PDF download, CSV aggregate export |

---

## 2. Automated Test Verification Summary

### Backend Test Suite
- **Command:** `py -m pytest tests/`
- **Results:** 161 passed, 3 skipped, 0 failures (164 collected)
- **Key Modules Tested:**
  - `tests/test_amenities.py`: 6 passed
  - `tests/test_auth.py`: 26 passed
  - `tests/test_bank_matching.py`: 12 passed
  - `tests/test_billing.py`: 8 passed
  - `tests/test_committee.py`: 5 passed
  - `tests/test_complaints.py`: 6 passed
  - `tests/test_guest_codes.py`: 4 passed
  - `tests/test_health.py`: 7 passed
  - `tests/test_integration.py`: 1 passed
  - `tests/test_migrations.py`: 1 passed
  - `tests/test_ml.py`: 27 passed
  - `tests/test_money_precision.py`: 5 passed
  - `tests/test_notices.py`: 5 passed
  - `tests/test_payment_concurrency.py`: 2 passed, 2 skipped (PostgreSQL concurrency tests)
  - `tests/test_payments.py`: 10 passed, 1 skipped (Razorpay webhook verification signature test)
  - `tests/test_permissions_regression.py`: 7 passed
  - `tests/test_resident_security.py`: 10 passed
  - `tests/test_seed.py`: 11 passed
  - `tests/test_visitors.py`: 8 passed

### Frontend Test & Build Suite
- **TypeScript Verification:** `cd frontend && npx tsc --noEmit` — PASSED (0 errors)
- **Unit & Component Tests:** `cd frontend && npm test` — 41 passed across 7 test files (0 failures)
- **Production Bundle Build:** `cd frontend && npm run build` — PASSED (`dist/index.html`, `dist/assets/index-*.js`, `dist/assets/index-*.css`)

---

## 3. Reviewer Personas (Demo Reference Date: `2026-11-06`)

| Persona | Phone | Demo OTP | Role / Flat | State |
|---|---|---|---|---|
| **Neeraj Kulkarni** | `9876543210` | `123456` | Owner, Flat T07-1203 | 1,150 sq ft, settled dues (₹7,475.00 paid), ₹0.00 outstanding |
| **Swati Joshi** | `9876543211` | `123456` | Tenant, Flat T12-0408 | 980 sq ft, 47 days overdue (due 2026-09-20), ₹6,370.00 outstanding |
| **Aamir Shaikh** | `9876543212` | `123456` | Owner, Flat T21-1601 | 1,640 sq ft, 18 days overdue (due 2026-10-19), ₹5,660.00 outstanding |
| **Ananya Kulkarni** | `9876543213` | `123456` | Family Member, Flat T07-1203 | Can view dues summary, cannot execute payments |
| **Priya Sharma** | `9876543214` | `123456` | Owner, Flat T03-0201 | 1,150 sq ft, routine maintenance account |
| **Ramesh Patil** | `9876543220` | `123456` | Help Desk Staff | Authorized for complaints queue, triage, and incident linking |
| **Suresh Shinde** | `9876543230` | `123456` | Security Guard | Gate access, visitor entry logging, admission, offline sync, guest pass verification |
| **Anita Deshmukh** | `9876543240` | `123456` | Accounts Staff | Authorized for bank statement imports, review queue, and ledger posting |
| **Vikram Sardesai** | `9876543250` | `123456` | Committee Member | Authorized for aggregate governance dashboard, dues ageing, SLA metrics, PDF/CSV report exports |
| **System Admin** | `9876543200` | `123456` | Administrator | Full administrative authority across all modules |
