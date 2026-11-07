# TOWNSHIP ONE — Gated Township Resident & Operations Platform

**Client:** Company A, Pune  
**Township Context:** 2,400 apartments across 28 towers, 180 on-site staff, 4 access gates, managing ₹22–26 crore annual maintenance budget.  
**Scope Authority:** Challenge Brief Part C: Brief 2 (Gated township's resident app for maintenance, complaints, and visitors).

---

## 1. System Architecture Overview

Township One is designed as a secure, high-performance, mobile-first PWA backed by a modular FastAPI backend with strict server-side authorization:

- **Frontend:** React 19 + TypeScript + Vite. Accessible mobile PWA (`user-scalable` enabled for pinch-to-zoom accessibility), precached offline application shell via service worker (`sw.js` strictly bypassing `/api/*`), trilingual support (English, Marathi, Hindi), responsive touch targets (≥44×44px).
- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2. Stateless architecture, server-side role resolution and flat membership validation, granular IDOR boundaries.
- **Database & Precision:** SQLite for zero-setup local development, PostgreSQL compatible for production deployment. Financial balances and ledger entries use `NUMERIC(14,2)` / Python `Decimal` with strict bankers-rounding-free arithmetic.
- **Database Migrations:** Alembic reproducible schema migrations (`alembic/versions/`) enabling reproducible zero-state database provisioning without relying on raw `create_all` shortcuts.
- **Isolated Testing:** Test execution uses dedicated `TEST_DATABASE_URL` (`sqlite:///./township_one_test.db`). Production/demo databases (`township_one.db`) are strictly guarded against test mutation.
- **Data Protection:** Built in compliance with India's **Digital Personal Data Protection (DPDP) Act 2023**: Purpose limitation, notice, strict role-based access control, and complete separation between resident PII and administrative/committee aggregate views.

---

## 2. Reviewer Persona Matrix & Test Credentials

Authentication uses OTP simulation for local and demo environments (fixed mock OTP: `123456`).

| Persona / Role | Name | Phone Number | Flat / Scope | Permitted Access | Restricted / Blocked Access |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Resident (Tenant)** | Swati Joshi | `9876543211` | T12-0408 (980 sqft) | View own bills, pay ₹6,370 overdue dues, test checkout, lodge complaints, view notices | Other flats' bills/receipts (403), committee reports (403), gate logs (403) |
| **Resident (Owner)** | Neeraj Kulkarni | `9876543210` | T07-1203 (1,150 sqft) | View own bills (₹7,475 paid, ₹0 due), receipts, flat ledger, complaints | Other flats' finances (403), paying already-paid bill (400) |
| **Family Member** | Ananya Kulkarni | `9876543213` | T07-1203 | View flat billing summary & complaints (`can_pay_bills=False`) | Initiating payments / checkout (403) |
| **Resident (Owner)** | Aamir Shaikh | `9876543212` | T21-1601 (1,640 sqft) | View ₹5,660 balance (₹5,000 paid of ₹10,660), pay dues | Other flats' bills/receipts (403) |
| **Help Desk** | Ramesh Patil | `9876543220` | Township Support | Complaint triage, assignment, status tracking, SLA monitoring | Financial postings (403), bank imports, visitor photos |
| **Security Guard** | Suresh Shinde | `9876543230` | Gate 1 | Visitor verification, entry/exit logging | Resident financial records (403), complaint details (403) |
| **Accounts Staff** | Anita Deshmukh | `9876543240` | Finance Office | Bank statement import, manual reconciliation, bill generation | Visitor security photos, committee governance actions |
| **Committee Member** | Vikram Sardesai | `9876543250` | Management Committee | Aggregate township collections, receivables, ageing metrics | **Strictly blocked from individual flat drill-down (403)** |
| **Admin / Operator**| System Admin | `9876543200` | Township Admin | Configuration, audit logs, system diagnostics | Audited privileged access |

---

## 3. Exact Sample Ground Truth (As of 2026-11-06)

Deterministic demo date: `DEMO_AS_OF_DATE = 2026-11-06T00:00:00Z`.

1. **Flat T07-1203 (Neeraj Kulkarni):**
   - Area: 1,150 sq ft @ ₹6.50/sq ft = ₹7,475.00
   - Paid: ₹7,475.00 in full on 2026-11-03
   - Current Outstanding: ₹0.00
   - Overdue Days: 0
   - Complaints: 0

2. **Flat T12-0408 (Swati Joshi, Tenant):**
   - Area: 980 sq ft @ ₹6.50/sq ft = ₹6,370.00
   - Issued: 2026-09-01 | Due: 2026-09-15 | Grace ends: 2026-09-20
   - Paid: ₹0.00
   - Current Outstanding: ₹6,370.00
   - Overdue Days: 47 days (as of 2026-11-06)
   - Illustrative Late Fee: ₹176.43 (18% p.a. simple interest per Maharashtra Co-operative Societies bye-laws)
   - Complaints: 1 active ticket (Water leakage from ceiling, In Progress)

3. **Flat T21-1601 (Aamir Shaikh):**
   - Area: 1,640 sq ft @ ₹6.50/sq ft = ₹10,660.00
   - Issued: 2026-10-01 | Due: 2026-10-15 | Grace ends: 2026-10-20
   - Paid: ₹5,000.00 on 2026-10-14
   - Current Outstanding: ₹5,660.00
   - Overdue Days: 18 days (as of 2026-11-06)
   - Complaints: 0

4. **Tower 7 Lift Incident (CMP-2026-1002):**
   - Linked incident grouping 10 distinct lift complaints from 10 flats across Tower 7.
   - Status: IN_PROGRESS (never auto-closed until root-cause physical resolution).

---

## 4. Step-by-Step Setup Instructions

### Prerequisites
- **Python:** 3.11 or later
- **Node.js:** v18, v20, or v24 & npm
- **Git**

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/Jagadeesh58/township-one.git
cd township-one

# Create and activate Python virtual environment
py -3.11 -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
# Backend dependencies (pinned)
pip install -r requirements.txt

# Frontend dependencies (clean lockfile)
cd frontend
npm ci
cd ..
```

### Step 3: Configure Environment Variables
Copy template `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```env
APP_NAME="Township One"
APP_ENV="development"
SECRET_KEY="REDACTED"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Demo application database
DATABASE_URL="sqlite:///./township_one.db"

# Dedicated test database (must never match DATABASE_URL)
TEST_DATABASE_URL="sqlite:///./township_one_test.db"

# Reviewer baseline date (ISO 8601)
DEMO_AS_OF_DATE="2026-11-06T00:00:00Z"
DEFAULT_GRACE_PERIOD_DAYS=5
DEMO_LATE_FEE_PERCENTAGE_PA=18.00
```

### Step 4: Run Alembic Migrations
```bash
# Apply migrations to database from zero
alembic upgrade head
```

### Step 5: Seed Demo Database
```bash
# Populates 28 towers, 2,400 flats, 180 staff, 4 gates, and exact sample flats
python seed/seed_data.py
```

### Step 6: Start Application Services
Open two terminal windows:

**Terminal 1 — Backend (FastAPI):**
```bash
py -3.11 -m uvicorn backend.app.main:app --reload --port 8000
```
- API Base: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

**Terminal 2 — Frontend (Vite PWA):**
```bash
cd frontend
npm run dev
```
- Frontend Web App: `http://localhost:5173`

---

## 5. Verification & Test Suite Execution

All tests execute against the dedicated test database (`TEST_DATABASE_URL`), ensuring zero mutation of demo records.

### Run Automated Backend Test Suite
```bash
py -3.11 -m pytest tests/ -v
```

**Coverage includes 35 comprehensive regression & security tests:**
- `tests/test_d1_s1_health.py` — Health checks, standardized error envelopes
- `tests/test_d1_s2_seed.py` — 2,400 flats, 28 towers, exact sample ground truth
- `tests/test_d1_s3_auth.py` — OTP verification, replay prevention, IDOR denial, family permissions
- `tests/test_d1_s4_billing.py` — Principal calculation, 5-day grace period, multiple unpaid bill aggregation, duplicate bill prevention
- `tests/test_d1_s5_payments.py` — Cross-flat idempotency key replay prevention, zero data leakage, strict outcome enum validation (`SUCCESS`, `PENDING`, `FAILED`, `EXPIRED`), zero side-effects on non-success, receipt access control
- `tests/test_d1_s7_integration.py` — End-to-end Day 1 resident journey (Swati overdue payment, Neeraj paid verification, Aamir partial payment, Committee aggregate scoping, Family permission enforcement)

### Run Frontend Production Build & Typecheck
```bash
cd frontend
npm run build
```

---

## 6. Financial Logic & Legal Reference

- **Statutory Authority:** Maharashtra Co-operative Societies Act, 1960 and Model Bye-Law No. 67.
- **Grace Period:** 5 calendar days following the due date (15th of the month; grace window closes on the 20th). No late interest accrues during grace.
- **Overdue Interest:** Calculated at simple interest of 18.00% per annum on principal dues after the grace window expires. Marked explicitly as illustrative demo rule.
- **Zero-Penny Rounding:** All monetary figures use two-decimal numeric representation (`NUMERIC(14,2)` and `Decimal`).

---

## 7. Data Protection & Security Controls

1. **Payment Idempotency:** SHA-256 request payload fingerprinting bound to authenticated user, flat, bill, and currency. Key collision across different users yields generic HTTP 409 without leaking transaction references or PII.
2. **Strict Outcome Validation:** Server-side `PaymentOutcomeEnum` rejects unknown/invalid outcomes (`TYPO_SUCCESS`, `UNKNOWN`, null) with HTTP 422 before reaching transaction state machine.
3. **Role & Committee Scoping:** Management Committee members are restricted to aggregate metrics (`GET /api/v1/billing/committee/aggregate`) and receive HTTP 403 when requesting individual flat drill-downs.
4. **Accessible PWA:** Mobile viewport permits pinch-to-zoom (`user-scalable=no` removed). Static shell precached via service worker while bypassing all financial API routes.
