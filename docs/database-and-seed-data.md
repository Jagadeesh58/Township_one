# Township One — Database & Seed Data Architecture

## 1. Scope & Township Entity Dimensions

The seed dataset accurately instantiates the full physical, operational, and residential scope of **Company A, Pune** as detailed in the project brief:

- **28 Residential Towers:** Coded `T01` through `T28`. Towers T01–T08 feature 20 floors (80 flats each); towers T09–T28 feature 25 floors (100 flats each).
- **2,400 Residential Flats:** Numbered systematically (e.g., `T07-1203` represents Tower 7, Floor 12, Unit 03).
- **180 Operational Staff Members:** Spread across Housekeeping, Security, Facility Engineering, Electrical, Plumbing, and Helpdesk.
- **4 Multi-Lane Security Gates:**
  1. Gate 1 — North Main Boulevard (Visitor & Resident Lane)
  2. Gate 2 — South Expressway Access (Fast-Tag Resident Lane)
  3. Gate 3 — East Service & Commercial Goods Delivery Gate
  4. Gate 4 — West Pedestrian & School Bus Terminal Gate

---

## 2. Reviewer Sample Flats & Exact Overdue Metrics

All sample data is calibrated against the reference baseline timestamp **`DEMO_AS_OF_DATE = 2026-11-06T00:00:00Z`**:

| Persona | Flat Number | Resident / Role | Unit Specs | Due Date | Overdue Days | Financial Status |
|---|---|---|---|---|---|---|
| **Neeraj Kulkarni** | `T07-1203` | Owner (`9876543210`) | 1,150 sq ft (2 BHK) | `2026-11-15` | 0 days | **Fully Paid:** Principal ₹7,475.00 settled in full on 2026-11-03. Balance: ₹0.00. |
| **Swati Joshi** | `T12-0408` | Tenant (`9876543211`) | 980 sq ft (2 BHK) | `2026-09-20` | **Exactly 47 days** | **Unpaid / Overdue:** Principal ₹6,370.00 completely unpaid. Open water leakage complaint. |
| **Aamir Shaikh** | `T21-1601` | Owner (`9876543212`) | 1,640 sq ft (3 BHK) | `2026-10-19` | **Exactly 18 days** | **Partially Paid:** Principal ₹10,660.00, ₹5,000.00 paid on 2026-10-18, Remaining Balance: ₹5,660.00. |
| **Ananya Kulkarni** | `T07-1203` | Family (`9876543213`) | 1,150 sq ft (2 BHK) | — | — | **Restricted Role:** Can view billing summary, but `can_pay_bills = False`. |

### Overdue Math Verification
- Swati Joshi (`T12-0408`):
  $$\text{Overdue Days} = 2026\text{-}11\text{-}06 - 2026\text{-}09\text{-}20 = 47\text{ days}$$
- Aamir Shaikh (`T21-1601`):
  $$\text{Overdue Days} = 2026\text{-}11\text{-}06 - 2026\text{-}10\text{-}19 = 18\text{ days}$$

---

## 3. Incident Correlation: Tower 7 Lift Incidents

To test operational triage and deduplication, the seed data creates **10 distinct synthetic resident profiles** across Tower 7 who independently reported the same mechanical lift breakdown:
- **Primary Incident:** `CMP-2026-1002` ("Tower 7 Passenger Lift 2 Jerking and Halting Between Floors 10-12").
- **Linked Duplicate Reports:** 9 additional complaints lodged by 9 separate verified flat residents in Tower 7.
- **SLA Invariant:** Linked duplicate reports maintain independent ticket tracking and resident SLA updates; they are never silently auto-closed.

---

## 4. Seeder Safety & Execution Modes

The seed script (`seed/seed_data.py`) implements a fail-closed safety policy to prevent catastrophic data loss:

```bash
# Mode 1: Safe Non-Destructive Seed (Default)
# Idempotent check: if 2,400 flats exist, preserves all database records.
# If database is partially seeded, refuses to run and aborts.
py -3.11 seed/seed_data.py --mode safe

# Mode 2: Clean Demo Database Reset
# Destructive recreation: requires explicit confirmation flag
# Strictly prohibited if targeting a remote or cloud database URL
py -3.11 seed/seed_data.py --mode reset-demo --confirm-local-demo
```
