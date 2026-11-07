# TOWNSHIP ONE — SESSION TRACEABILITY MATRIX

**Project:** Township One (Challenge Brief 2)  
**Location:** Company A Township, Pune  
**Standard Session Prefix:** `D1-Sx` (Day 1, Sessions 1 through 7)  

---

## 1. Traceability Matrix

| Session ID | Session Name | Core Responsibility | Implemented Source Files | Test Suite File | Session Documentation | Detailed Test Report |
|---|---|---|---|---|---|---|
| **D1-S1** | Foundation and environment | Repository, dependencies, configuration, database setup, migrations and CI | `backend/app/core/config.py`, `backend/app/core/database.py`, `migrations/env.py`, `alembic.ini` | `tests/test_d1_s1_health.py` | `docs/day-1/D1-S1-foundation-and-environment.md` | `docs/reports/day1/D1-S1-test-report.md` |
| **D1-S2** | Database and township seed | 28 towers, 2,400 flats, 180 staff, 4 gates, reviewer sample data, lift incident | `backend/app/models/entities.py`, `seed/seed_data.py` | `tests/test_d1_s2_seed.py` | `docs/day-1/D1-S2-database-and-township-seed.md` | `docs/reports/day1/D1-S2-seed-validation-report.md` |
| **D1-S3** | Authentication and permissions | OTP challenges, replay block, rate limits, JWT with JTI, persistent revocation, RBAC | `backend/app/core/security.py`, `backend/app/api/auth.py`, `backend/app/models/entities.py` | `tests/test_d1_s3_auth.py` | `docs/day-1/D1-S3-authentication-and-permissions.md` | `docs/reports/day1/D1-S3-security-test-report.md` |
| **D1-S4** | Maintenance billing and ledger | Bill generation, area/rate calculations, late fees, grace period, flat balances | `backend/app/services/billing.py`, `backend/app/api/billing.py`, `backend/app/schemas/billing.py` | `tests/test_d1_s4_billing.py` | `docs/day-1/D1-S4-maintenance-billing-and-ledger.md` | `docs/reports/day1/D1-S4-financial-test-report.md` |
| **D1-S5** | Test payments and receipts | Checkout, cryptographic idempotency, strict outcomes, allocation and receipts | `backend/app/services/payments.py`, `backend/app/api/payments.py`, `backend/app/schemas/payments.py` | `tests/test_d1_s5_payments.py` | `docs/day-1/D1-S5-test-payments-and-receipts.md` | `docs/reports/day1/D1-S5-payment-test-report.md` |
| **D1-S6** | Resident interface and PWA | Resident home, billing, payment UI, icons, offline shell, error states | `frontend/src/api/client.ts`, `frontend/src/components/DuesCard.tsx`, `frontend/src/components/PaymentModal.tsx`, `frontend/public/sw.js` | Frontend Vite Build (`npm run build`) | `docs/day-1/D1-S6-resident-interface-and-pwa.md` | `docs/reports/day1/D1-S6-frontend-pwa-test-report.md` |
| **D1-S7** | Integration and Day 1 verification | End-to-end testing, security regression, seed verification and Day 1 sign-off | `tests/test_d1_s7_integration.py`, `tests/conftest.py` | Full Pytest Suite (`tests/`) | `docs/day-1/D1-S7-integration-and-day1-verification.md` | `docs/reports/day1/D1-S7-end-to-end-test-report.md` |

---

## 2. Commit Traceability

| Commit SHA | Session | Commit Message Summary |
|---|---|---|
| `402a347` | D1-S1 | `fix(D1-S1): environment, dynamic db url, and production secrets guard` |
| `da41532` | D1-S2 | `fix(D1-S2): fail-closed seed reset policy and 10 distinct lift reporters` |
| `e49d31b` | D1-S3 | `fix(D1-S3): strengthen authentication, token revocation and role-based permissions` |
| `39a78a2` | D1-S4 | `fix(D1-S4): correct billing, grace period and ledger calculations` |
| `89afb3f` | D1-S5 | `fix(D1-S5): secure payment idempotency and transaction concurrency` |
| `580e9f5` | D1-S6 | `fix(D1-S6): fix PWA asset caching, multi-bill selection and resident financial handling` |
| `57aebd6` | D1-S7 | `test(D1-S7): add full Day 1 regression and acceptance coverage` |
