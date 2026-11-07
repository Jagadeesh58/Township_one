# Township One — Reviewer Demonstration Walkthrough

Welcome to the Township One demonstration guide. Follow this structured walkthrough to inspect and verify all features, security controls, and accounting workflows.

---

## 1. Quick Start Commands

### Backend API Server
```bash
# In project root:
py -3.11 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive OpenAPI / Swagger documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Frontend Development Server
```bash
# In frontend/:
cd frontend
npm run dev
```
Resident Portal Web Application: [http://localhost:5173](http://localhost:5173)

---

## 2. Reviewer Test Personas

The demonstration database is pre-seeded with verified personas (Demo OTP in development/test: `123456`):

| Persona Name | Role | Mobile Number | Demo OTP | Flat Number | Unit Details & Financial Status |
|---|---|---|---|---|---|
| **Neeraj Kulkarni** | Owner | `9876543210` | `123456` | T07-1203 | 1,150 sq ft (2 BHK) — Fully Paid (₹0.00 Due) |
| **Swati Joshi** | Tenant | `9876543211` | `123456` | T12-0408 | 980 sq ft (2 BHK) — Exactly 47 days overdue (₹6,370.00 Due) |
| **Aamir Shaikh** | Owner | `9876543212` | `123456` | T21-1601 | 1,640 sq ft (3 BHK) — Exactly 18 days overdue (₹5,660.00 Due) |
| **Ananya Kulkarni** | Family Member | `9876543213` | `123456` | T07-1203 | View permitted, bill payment blocked |
| **Vikram Sardesai** | Management Committee | `9876543250` | `123456` | Township | Aggregate reports authorized; individual flats blocked |
| **Suresh Shinde** | Security Guard | `9876543230` | `123456` | Gate 1 | Gate pass operations; financial records blocked |

---

## 3. Step-by-Step Walkthrough Guide

### Scenario 1: Tenant Dues Payment (2-Tap Action & Payment State Machine)
1. Open the resident web application at [http://localhost:5173](http://localhost:5173).
2. Enter mobile number: `9876543211` (Swati Joshi).
3. Enter 6-digit OTP: `123456` (or use the Quick Reviewer Demo Sign-In buttons).
4. Inspect the Resident Home Dashboard:
   - Notice the prominent Dues Card displaying `₹6,370.00` with the `47 days overdue` badge.
   - Note the transparent formula breakdown: `980 sq ft @ ₹6.50/sq ft/month`.
5. Tap **"Pay Now"** (Tap 1) to open the Checkout Modal:
   - Review the multi-bill breakdown and due amount.
   - Select Outcome: `FAILED` -> Click **"Complete Test Payment"** -> Notice payment failure banner and dues remain intact at ₹6,370.00.
   - Select Outcome: `SUCCESS` -> Click **"Complete Test Payment"** (Tap 2).
6. Observe the official Payment Receipt Modal appear immediately:
   - Displays receipt number (e.g. `REC-202611-XXXXX`), transaction reference, resident name, and flat number.
7. Close the receipt modal and switch to the **"Ledger"** tab:
   - Observe the running flat ledger statement. The initial DEBIT of ₹6,370.00 is balanced by a CREDIT of ₹6,370.00, bringing the net balance to ₹0.00.

### Scenario 2: Permission Scoping & IDOR Enforcement
1. **Family Member Payment Restriction:**
   - Sign in as Ananya Kulkarni (`9876543213`).
   - Notice that while billing statements can be inspected, executing a checkout payment is blocked with HTTP 403 Forbidden ("membership does not permit bill payment").
2. **Management Committee Privacy Protection:**
   - Sign in as Vikram Sardesai (`9876543250`).
   - Query `/api/v1/billing/committee/aggregate`: HTTP 200 OK with total billed, collected, and collection efficiency across 2,400 flats.
   - Query `/api/v1/billing/flats/{swati_flat_id}/summary`: HTTP 403 Forbidden ("Committee members can only access aggregate reports").

---

## 4. Automated Verification Commands

Execute the test suites to independently verify all assertions:

```bash
# Run backend pytest suite (57 tests)
py -3.11 -m pytest tests/ -v

# Run frontend vitest suite (11 tests)
cd frontend
npm test

# Verify production frontend build
npm run build
```
