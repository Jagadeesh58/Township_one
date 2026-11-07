# D1-S1 Test Report — Foundation and Environment

**Date:** 2026-11-07  
**Session:** D1-S1  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s1_health.py`  

---

## 1. Execution Summary
- **Total Tests:** 6
- **Passed:** 6
- **Failed:** 0
- **Duration:** 3.42s
- **Status:** PASS

---

## 2. Test Cases Executed

| Test Function | Verification Purpose | Result |
|---|---|---|
| `test_health_check_endpoint` | Root health endpoint `/health` returns `{status: "ok"}` | PASSED |
| `test_api_prefix_health_endpoint` | Versioned prefix `/api/v1/health` returns `{status: "ok"}` | PASSED |
| `test_404_error_format` | Undefined endpoints return structured error envelope `{error: {code, message}}` | PASSED |
| `test_database_url_separation` | Validates `TEST_DATABASE_URL` is separate from `DATABASE_URL` | PASSED |
| `test_production_guard_rejects_default_secret` | Production mode raises RuntimeError on default secret | PASSED |
| `test_alembic_url_resolution_dynamic` | Alembic env resolves dynamic URL without config hardcoding | PASSED |

---

## 3. Command & Output
```bash
py -3.11 -m pytest tests/test_d1_s1_health.py -v
```
```text
tests/test_d1_s1_health.py::test_health_check_endpoint PASSED            [ 16%]
tests/test_d1_s1_health.py::test_api_prefix_health_endpoint PASSED       [ 33%]
tests/test_d1_s1_health.py::test_404_error_format PASSED                 [ 50%]
tests/test_d1_s1_health.py::test_database_url_separation PASSED          [ 66%]
tests/test_d1_s1_health.py::test_production_guard_rejects_default_secret PASSED [ 83%]
tests/test_d1_s1_health.py::test_alembic_url_resolution_dynamic PASSED   [100%]
======================== 6 passed, 1 warning in 3.42s =========================
```
