# Repository Baseline Audit Report

## Audit Summary

- Execution Date: 2026-11-09
- Python Version: 3.11.9
- Node Version: 20+
- Database Engine: PostgreSQL (Target), SQLite (Local Test Isolation)
- Git Branch: master

## Code Quality and Static Analysis

### Python Linting (Ruff)
- Total Findings: 1,023
- Categories:
  - Import sorting (I001): 278
  - Unused imports (F401): 84
  - Pyupgrade modern typing idioms (UP006, UP035, UP017): 364
  - Blank lines, whitespace, formatting (W293, E302, E305): 297
- Automatically fixable via `ruff check --fix` and `ruff format`: 726+

### Python Type Checking (Mypy)
- Total Errors: 477 across 21 files
- Root Cause: Legacy SQLAlchemy `Column` definitions in `backend/app/models/entities.py` generating type incompatibilities across API routes and service layers expecting typed model instances.
- Remediation Plan: Transition to modern SQLAlchemy 2.0 `Mapped[...]` and `mapped_column(...)` constructs with strict optionality.

## Test Verification

### Backend Automated Test Suite (Pytest)
- Tests Executed: 164 total (161 passed, 3 skipped due to PostgreSQL-specific concurrency requirements)
- Execution Duration: ~276 seconds
- Total Backend Code Statements: 4,171
- Total Statements Missed: 505
- Baseline Coverage: 88%

#### Coverage Distribution
| Module | Statements | Missing | Coverage |
| :--- | :--- | :--- | :--- |
| `backend/app/api/bank.py` | 94 | 67 | 29% |
| `backend/app/api/notifications.py` | 33 | 16 | 52% |
| `backend/app/services/billing.py` | 92 | 37 | 60% |
| `backend/app/api/amenities.py` | 81 | 22 | 73% |
| `backend/app/ml/duplicates.py` | 54 | 14 | 74% |
| `backend/app/ml/classifier.py` | 120 | 28 | 77% |
| `backend/app/services/bank_matching.py` | 464 | 85 | 82% |
| `backend/app/api/visitors.py` | 205 | 37 | 82% |
| `backend/app/services/payments.py` | 98 | 13 | 87% |
| `backend/app/services/amenity_service.py` | 109 | 13 | 88% |
| `backend/app/services/visitor_service.py` | 223 | 21 | 91% |
| `backend/app/services/committee_service.py` | 165 | 11 | 93% |
| `backend/app/services/complaints.py` | 76 | 1 | 99% |
| `backend/app/models/entities.py` | 635 | 0 | 100% |

### Frontend Automated Test Suite (Vitest)
- Test Files: 7 files passed
- Tests Executed: 41 passed, 0 failed
- TypeScript Compilation (`tsc --noEmit`): 0 errors
- Production Build (`npm run build`): Clean distribution output in `frontend/dist/`

## Database Migrations Audit

### Alembic Check Status
- Initial Status: Drift detected
- Drift Findings:
  1. Table `revoked_tokens` present in models but missing from migration chain.
  2. Column `payments.created_at` present in models but missing from migration chain.
  3. Column nullability/type adjustments needed between SQLite autogenerate inspection and schema definitions.
- Required Action: Add corrective migration revision and synchronize model column definitions so `alembic check` passes without pending operations.
