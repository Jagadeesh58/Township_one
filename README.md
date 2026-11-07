# TOWNSHIP ONE — Gated Township Resident & Operations Platform

**Client:** Company A, Pune  
**Township Context:** 2,400 residential flats across 28 towers, 180 on-site staff, 4 multi-lane access gates, managing ₹22–26 crore annual maintenance budget.  
**Scope Authority:** Challenge Brief Part C: Brief 2 (Gated township resident app for maintenance, complaints, and visitors).  

---

## 1. System Overview

Township One is an enterprise-grade resident experience and community operations platform engineered for large-scale gated communities. The platform provides secure resident authentication, spatial township modeling, maintenance dues calculation with transparent breakdown, simulated test payment processing with cryptographic idempotency, dual-entry accounting ledgers, and a mobile-first Progressive Web App (PWA).

### Architecture Highlights
- **Backend API:** FastAPI (Python 3.11), SQLAlchemy 2.0 ORM, Pydantic v2, and Alembic schema migrations.
- **Frontend PWA:** React 19, TypeScript, Vite 6, Service Worker offline caching (with strict `/api/*` network-only bypass), trilingual native localization (English, Marathi, Hindi).
- **Financial Precision:** Strict decimal arithmetic using Python `Decimal` (`ROUND_HALF_UP`) ensuring zero binary floating-point drift across all billing and ledger calculations.
- **Payment Idempotency:** Cryptographic request fingerprinting, mandatory client idempotency keys (minimum 8 chars), dialect-aware row-level locking (`with_for_update`), and generic conflict responses preventing cross-resident data leakage.
- **Role-Based Access Control:** Strict server-side permission enforcement. Committee members access aggregate township metrics while being strictly blocked from individual flat drill-downs; security guards are restricted to gate operations with zero financial access; family members have view permissions while bill payment is blocked.

---

## 2. Professional Documentation Hierarchy

Comprehensive architecture specifications, data schemas, security models, and verification reports are maintained in the [`docs/`](docs/) directory:

| Document | Description |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | High-level system architecture, component topology, and technology stack. |
| [`docs/data-model.md`](docs/data-model.md) | Entity-relationship diagrams, schema tables, constraints, and data dictionaries. |
| [`docs/database-and-seed-data.md`](docs/database-and-seed-data.md) | 2,400 flats, 28 towers, 180 staff, 4 gates, and ground truth sample personas. |
| [`docs/authentication-and-access-control.md`](docs/authentication-and-access-control.md) | Salted SHA-256 OTP authentication, persistent JWT revocation, and RBAC matrix. |
| [`docs/maintenance-billing.md`](docs/maintenance-billing.md) | Area-rate billing (₹6.50/sq ft), grace period boundaries, leap year support, and ledger bookkeeping. |
| [`docs/payments-and-receipts.md`](docs/payments-and-receipts.md) | Idempotency locking, state machine retry lifecycle, test payment modes, and vouchers. |
| [`docs/resident-experience-and-pwa.md`](docs/resident-experience-and-pwa.md) | 2-tap payment CTA, multi-bill selection, service worker caching, and trilingual i18n. |
| [`docs/security-and-privacy.md`](docs/security-and-privacy.md) | Production configuration guards, IDOR prevention, brute-force defenses, and DPDP Act 2023 alignment. |
| [`docs/testing-and-validation.md`](docs/testing-and-validation.md) | Verification engine methodology, test suite topology, and test execution evidence. |
| [`docs/assumptions-and-open-decisions.md`](docs/assumptions-and-open-decisions.md) | Domain assumptions register, late fee legal notice, and architectural roadmap. |
| [`docs/implementation-status.md`](docs/implementation-status.md) | Requirement completion matrix, verified persona checklist, and future phase boundaries. |
| [`docs/reviewer-walkthrough.md`](docs/reviewer-walkthrough.md) | Step-by-step evaluation guide and demonstration scenarios. |
| [`docs/deployment.md`](docs/deployment.md) | Production deployment guide, environment variables, and operations checklist. |

### Technical Verification Reports
- [`docs/reports/backend-test-report.md`](docs/reports/backend-test-report.md) — 57/57 Automated backend tests passing.
- [`docs/reports/migration-validation.md`](docs/reports/migration-validation.md) — Alembic schema migration and revision verification.
- [`docs/reports/seed-data-validation.md`](docs/reports/seed-data-validation.md) — Database entity counts and overdue math validation.
- [`docs/reports/frontend-validation.md`](docs/reports/frontend-validation.md) — Vitest frontend test report and production asset build metrics.
- [`docs/reports/payment-safety-validation.md`](docs/reports/payment-safety-validation.md) — Idempotency replay matrix, concurrency benchmarks, and precision tests.

---

## 3. Reviewer Test Personas & Test Credentials

The local demonstration database (`township_one.db`) is pre-seeded with test accounts. In development and testing environments, OTP verification uses the demo OTP `123456`:

| Persona / Role | Name | Phone Number | Demo OTP | Scope | Permitted Access | Blocked Access |
|---|---|---|---|---|---|---|
| **Resident (Tenant)** | Swati Joshi | `9876543211` | `123456` | T12-0408 (980 sq ft) | View bills, pay ₹6,370 overdue dues, test checkout, lodge complaints | Other flats' records (403), committee reports (403), gate logs (403) |
| **Resident (Owner)** | Neeraj Kulkarni | `9876543210` | `123456` | T07-1203 (1,150 sq ft) | View bills (₹7,475 paid, ₹0 due), receipts, flat ledger statement | Other flats' finances (403), duplicate payment on paid bill (400) |
| **Family Member** | Ananya Kulkarni | `9876543213` | `123456` | T07-1203 | View flat billing summary & complaints (`can_pay_bills = False`) | Initiating payments / checkout (403) |
| **Resident (Owner)** | Aamir Shaikh | `9876543212` | `123456` | T21-1601 (1,640 sq ft) | View ₹5,660 balance (₹5,000 paid of ₹10,660), pay dues | Other flats' records (403) |
| **Help Desk** | Ramesh Patil | `9876543220` | `123456` | Township Support | Complaint triage, assignment, status tracking, SLA monitoring | Financial postings (403), gate security photos |
| **Security Guard** | Suresh Shinde | `9876543230` | `123456` | Gate 1 | Visitor verification, entry/exit logging | Resident financial records (403), complaints (403) |
| **Accounts Staff** | Anita Deshmukh | `9876543240` | `123456` | Finance Office | Manual reconciliation, bill generation, ledger audit | Security gate photos, committee governance actions |
| **Committee Member**| Vikram Sardesai | `9876543250` | `123456` | Management Committee | Aggregate township collections, receivables, ageing metrics | **Strictly blocked from individual flat drill-down (403)** |

---

## 4. Ground Truth Sample Data (As of 2026-11-06)

Deterministic baseline date: `DEMO_AS_OF_DATE = 2026-11-06T00:00:00Z`.

1. **Flat T07-1203 (Neeraj Kulkarni):**
   - Area: 1,150 sq ft @ ₹6.50/sq ft = ₹7,475.00
   - Paid: ₹7,475.00 in full on 2026-11-03
   - Current Outstanding: ₹0.00
   - Overdue Days: 0
2. **Flat T12-0408 (Swati Joshi, Tenant):**
   - Area: 980 sq ft @ ₹6.50/sq ft = ₹6,370.00
   - Due Date: 2026-09-20 (Grace ended 2026-09-20)
   - Overdue Days: **Exactly 47 days** as of 2026-11-06 ($2026\text{-}11\text{-}06 - 2026\text{-}09\text{-}20 = 47\text{ days}$)
   - Paid: ₹0.00 | Current Outstanding: ₹6,370.00
   - Late Fee Notice: Illustrative demo calculation (18% p.a. simple interest) pending society federation approval (not an approved legal rate).
   - Complaints: 1 high-urgency active water leakage complaint.
3. **Flat T21-1601 (Aamir Shaikh):**
   - Area: 1,640 sq ft @ ₹6.50/sq ft = ₹10,660.00
   - Due Date: 2026-10-19 (Grace ended 2026-10-19)
   - Overdue Days: **Exactly 18 days** as of 2026-11-06 ($2026\text{-}11\text{-}06 - 2026\text{-}10\text{-}19 = 18\text{ days}$)
   - Paid: ₹5,000.00 on 2026-10-18 | Current Outstanding: ₹5,660.00
4. **Tower 7 Lift Incident (CMP-2026-1002):**
   - Primary ticket grouping 10 distinct lift complaints from 10 distinct flats across Tower 7.
   - All reports remain open and SLA-tracked until physical mechanical resolution.

---

## 5. Quick Start & Execution

### 5.1 Prerequisites
- Python 3.11+
- Node.js 18+ (Node 20+ recommended)
- Git

### 5.2 Backend Setup & Execution
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run safe database seed (non-destructive; skips if already seeded)
py -3.11 seed/seed_data.py --mode safe

# Start FastAPI server on port 8000
py -3.11 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5.3 Frontend Setup & Execution
```bash
# Navigate to frontend
cd frontend

# Install npm dependencies
npm install

# Run frontend development server
npm run dev
```
Resident Portal Application: [http://localhost:5173](http://localhost:5173)

### 5.4 Running Automated Verification
```bash
# Run backend pytest suite (57 tests)
py -3.11 -m pytest tests/ -v

# Run frontend vitest suite (11 tests)
cd frontend
npm test

# Build production frontend bundle
npm run build
```
