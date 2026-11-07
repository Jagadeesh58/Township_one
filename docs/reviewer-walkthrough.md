# TOWNSHIP ONE — REVIEWER DEMO WALKTHROUGH

Welcome to Township One. Follow this structured walkthrough to inspect and verify all Day 1 capabilities.

---

## 1. Quick Start Commands

### Backend API Server
```bash
# In project root:
py -3.11 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Frontend Development Server
```bash
# In frontend/:
cd frontend
npm run dev
```
Web App UI: [http://localhost:5173](http://localhost:5173)

---

## 2. Reviewer Test Personas

| Persona Name | Role | Phone Number | Demo OTP | Flat Number | Area & Status |
|---|---|---|---|---|---|
| **Neeraj Kulkarni** | Owner | `9876543210` | `123456` | T07-1203 | 1,150 sq ft — Fully Paid (₹0 Due) |
| **Swati Joshi** | Tenant | `9876543211` | `123456` | T12-0408 | 980 sq ft — Overdue >40 days (₹6,370 Due) |
| **Aamir Shaikh** | Owner | `9876543212` | `123456` | T21-1601 | 1,640 sq ft — Partially Paid (₹5,660 Due) |
| **Ananya Kulkarni** | Family | `9876543213` | `123456` | T07-1203 | Family Member (Cannot Pay Bills) |
| **Vikram Sardesai** | Committee | `9876543250` | `123456` | Aggregate | Management Committee (Aggregate Only) |
| **Suresh Shinde** | Guard | `9876543230` | `123456` | Gate 1 | Gate Security Guard (No Billing Access) |

---

## 3. Step-by-Step Walkthrough Guide

### Scenario 1: Tenant Dues Payment (2-Tap Action)
1. Open [http://localhost:5173](http://localhost:5173).
2. Enter phone: `9876543211` (Swati Joshi).
3. Enter OTP: `123456`.
4. Observe Home Screen:
   - Notice the orange Dues Card: `₹6,370.00` with `40+ days overdue` badge.
   - Note the formula: `980 sq ft @ ₹6.50/sq ft/month`.
5. Tap **"Pay Now"** (Tap 1).
6. In the Checkout Modal:
   - Select Outcome: `FAILED` -> Click **"Confirm Payment"** -> Notice error banner and dues remain intact at ₹6,370.00.
   - Select Outcome: `SUCCESS` -> Click **"Confirm Payment"** (Tap 2).
7. Notice official Receipt Modal pop up with `REC-202611-...` and transaction reference.
8. Close receipt and switch to **"Ledger"** tab: see credit posted and balance drop to ₹0.00.

### Scenario 2: Security & IDOR Enforcement
1. Login as Ananya Kulkarni (`9876543213`):
   - Notice dues can be viewed, but payment attempt is blocked with 403 Forbidden ("membership does not permit bill payment").
2. Login as Vikram Sardesai (`9876543250`):
   - In Swagger docs, hit `/api/v1/billing/committee/aggregate`: 200 OK with total billed, collected, and collection efficiency.
   - Hit `/api/v1/billing/flats/{swati_flat_id}/summary`: 403 Forbidden ("Committee members can only access aggregate reports").

---

## 4. Run Automated Tests
```bash
py -3.11 -m pytest tests/ -v
```
All 44 automated tests will execute and pass in under 20 seconds.
