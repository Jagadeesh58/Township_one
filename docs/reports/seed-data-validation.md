# Seed Data Integrity & Persona Validation Report

**Seeding Engine:** `seed/seed_data.py`  
**Reference Timeline Date:** `2026-11-06T00:00:00Z` (`DEMO_AS_OF_DATE`)  
**Test Suite:** `tests/test_seed.py` (100% Passed)  

---

## 1. Physical & Operational Entity Counts

| Entity Type | Required Specification | Database Count | Verification Result |
|---|---|---|---|
| **Residential Towers** | 28 towers (`T01`–`T28`) | 28 | **MATCH (100%)** |
| **Residential Flats** | 2,400 flats | 2,400 | **MATCH (100%)** |
| **Operations Staff** | 180 on-site personnel | 180 | **MATCH (100%)** |
| **Security Gates** | 4 multi-lane entry gates | 4 | **MATCH (100%)** |

---

## 2. Reviewer Sample Flat Audit

### Flat T07-1203 — Neeraj Kulkarni (Owner)
- **Area:** 1,150.00 sq ft
- **Tariff:** ₹6.50 / sq ft
- **Principal Maintenance:** ₹7,475.00
- **Paid Amount:** ₹7,475.00 (settled on 2026-11-03)
- **Balance:** ₹0.00 (Bill Status: `PAID`)
- **Overdue Days:** 0 days

### Flat T12-0408 — Swati Joshi (Tenant)
- **Area:** 980.00 sq ft
- **Tariff:** ₹6.50 / sq ft
- **Principal Maintenance:** ₹6,370.00
- **Due Date:** `2026-09-20`
- **Reference Date:** `2026-11-06`
- **Overdue Days:** Exactly 47 days ($2026\text{-}11\text{-}06 - 2026\text{-}09\text{-}20 = 47\text{ days}$)
- **Paid Amount:** ₹0.00
- **Balance:** ₹6,370.00 (Bill Status: `OVERDUE`)
- **Open Complaint:** 1 high-urgency water supply leak ticket

### Flat T21-1601 — Aamir Shaikh (Owner)
- **Area:** 1,640.00 sq ft
- **Tariff:** ₹6.50 / sq ft
- **Principal Maintenance:** ₹10,660.00
- **Due Date:** `2026-10-19`
- **Reference Date:** `2026-11-06`
- **Overdue Days:** Exactly 18 days ($2026\text{-}11\text{-}06 - 2026\text{-}10\text{-}19 = 18\text{ days}$)
- **Paid Amount:** ₹5,000.00 (partially settled on 2026-10-18)
- **Balance:** ₹5,660.00 (Bill Status: `PARTIALLY_PAID`)

---

## 3. Incident Correlation Audit

- **Primary Lift Breakdown:** `CMP-2026-1002` (Tower 7 Lift 2 mechanical jerk).
- **Linked Duplicate Reports:** 9 additional complaint tickets.
- **Deduplication Invariant:**
  - 10 distinct reporter user IDs.
  - 10 distinct flats across Tower 7.
  - All linked tickets remain open and SLA-tracked; zero silent closures.
