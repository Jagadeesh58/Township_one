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
| **Bank Statement Matching Engine** | Built | `tests/test_bank_matching.py` | Canonical statement preview, deterministic rules, zero false auto-postings (385-row corpus), review queue |
| **Complaint Lifecycle State Machine** | Built | `tests/test_complaints.py` | Explicit state transitions (HTTP 409 Conflict on illegal transition), flat-scoping, rating & reopen |
| **Trilingual Emergency Detection** | Built | `tests/test_complaints.py`, `tests/test_ml.py` | Deterministic regex detector across en/hi/mr forcing CRITICAL urgency and SafetyEvent |
| **AI Complaint Classification & Fallback** | Built | `tests/test_ml.py` | Groq API client with local TF-IDF + MultinomialNB fallback trained on 360-row multilingual dataset |
| **Semantic Duplicate Detection** | Built | `tests/test_complaints.py`, `tests/test_ml.py` | Character n-gram TF-IDF cosine similarity with incident group linking |
| **Private Photo Streaming** | Built | `tests/test_complaints.py` | Pillow MIME verification, EXIF stripping, 5-minute HMAC signed URLs |
| **Accounts Workspace UI** | Built | `frontend/src/__tests__/features.test.tsx` | Statement upload, preview table, commit action, review queue handlers |
| **Help Desk Queue UI** | Built | `frontend/src/__tests__/features.test.tsx` | Status/category/urgency filters, SLA badges, AI evidence card, one-tap optimistic correction |
| **Resident Complaints UI** | Built | `frontend/src/__tests__/features.test.tsx` | Ticket submission with photo upload, my complaints, 1-5 star resolution rating, reopen request |
| **Notification Bell & In-App Alerts** | Built | `frontend/src/__tests__/features.test.tsx` | Unread badge count, safety escalation alerts, mark-all-read |
| **Trilingual Localization** | Built | `frontend/src/__tests__/translations.test.ts` | Complete English, Marathi, Hindi translations |
| **PWA Cache Lifecycle** | Built | `frontend/src/__tests__/serviceWorker.test.ts` | App shell pre-caching, network-only bypass for `/api/*`, cache wipe on logout |
| **Visitor Gate Check-in & Dynamic PINs** | Scheduled | — | Scheduled for future release |
| **Amenity Booking Slot Reservation** | Scheduled | — | Scheduled for future release |
| **Digital Notice Board Publishing** | Scheduled | — | Scheduled for future release |
| **Committee Audit Pack Generator** | Scheduled | — | Scheduled for future release |

---

## 2. Reviewer Personas (Demo Reference Date: `2026-11-06`)

| Persona | Phone | Demo OTP | Role / Flat | State |
|---|---|---|---|---|
| **Neeraj Kulkarni** | `9876543210` | `123456` | Owner, Flat T07-1203 | 1,150 sq ft, fully settled dues (₹7,475.00 paid), ₹0.00 outstanding |
| **Swati Joshi** | `9876543211` | `123456` | Tenant, Flat T12-0408 | 980 sq ft, 47 days overdue (due 2026-09-20), ₹6,370.00 outstanding |
| **Aamir Shaikh** | `9876543212` | `123456` | Owner, Flat T21-1601 | 1,640 sq ft, 18 days overdue (due 2026-10-19), ₹5,660.00 outstanding |
| **Ananya Kulkarni** | `9876543213` | `123456` | Family Member, Flat T07-1203 | Can view dues summary, cannot execute payments |
| **Priya Sharma** | `9876543214` | `123456` | Owner, Flat T03-0201 | 1,150 sq ft, routine maintenance account |
| **Ramesh Patil** | `9876543220` | `123456` | Help Desk Staff | Authorized for complaints queue, triage, and incident linking |
| **Suresh Shinde** | `9876543230` | `123456` | Security Guard | Gate access; billing, bank, and complaint mutations blocked |
| **Anita Deshmukh** | `9876543240` | `123456` | Accounts Staff | Authorized for bank statement imports, review queue, and ledger posting |
| **Vikram Sardesai** | `9876543250` | `123456` | Committee Member | Authorized for aggregate metrics and complaints queue; individual flat actions blocked |
| **System Admin** | `9876543200` | `123456` | Administrator | Full administrative authority across all modules |
