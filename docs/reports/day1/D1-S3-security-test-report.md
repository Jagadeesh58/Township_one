# D1-S3 Security Test Report — Authentication and Permissions

**Date:** 2026-11-07  
**Session:** D1-S3  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s3_auth.py`  

---

## 1. Execution Summary
- **Total Tests:** 14
- **Passed:** 14
- **Failed:** 0
- **Duration:** 6.66s
- **Status:** PASS

---

## 2. Security Test Cases Executed

| Test Function | Security Verification Purpose | Result |
|---|---|---|
| `test_request_otp_success` | Valid phone returns OTP challenge and expiry | PASSED |
| `test_request_otp_nonexistent_user` | Unregistered phone returns 404 cleanly | PASSED |
| `test_verify_otp_valid` | Valid OTP returns signed JWT with user profile and flats | PASSED |
| `test_verify_otp_invalid` | Incorrect OTP returns 401 Unauthorized | PASSED |
| `test_verify_otp_replay_prevented` | Single-use OTP: second verification attempt fails (400) | PASSED |
| `test_verify_otp_rate_limiting` | Max 3 invalid verification attempts triggers 429 lockout | PASSED |
| `test_logout_and_revocation` | `/auth/logout` revokes JWT; subsequent access returns 401 | PASSED |
| `test_cross_flat_access_idor_denied` | Resident cannot access another resident's flat (403) | PASSED |
| `test_committee_individual_flat_access_strictly_denied` | Committee denied individual flat summaries (403); aggregate allowed (200) | PASSED |
| `test_family_member_permission_enforcement` | Family member can read dues (200) but payment is blocked (403) | PASSED |
| `test_guard_access_to_finance_denied` | Security guard is strictly denied flat finance endpoints (403) | PASSED |
| `test_demo_hint_hidden_in_production` | `demo_hint` completely omitted when `APP_ENV=production` | PASSED |
| `test_otp_request_rate_limiting` | Max 5 OTP requests per 10 min window triggers 429 | PASSED |
| `test_database_persisted_revoked_token` | Revoked token recorded in database table `revoked_tokens` | PASSED |

---

## 3. Command & Output
```bash
py -3.11 -m pytest tests/test_d1_s3_auth.py -v
```
```text
tests/test_d1_s3_auth.py::test_request_otp_success PASSED                [  7%]
tests/test_d1_s3_auth.py::test_request_otp_nonexistent_user PASSED       [ 14%]
tests/test_d1_s3_auth.py::test_verify_otp_valid PASSED                   [ 21%]
tests/test_d1_s3_auth.py::test_verify_otp_invalid PASSED                 [ 28%]
tests/test_d1_s3_auth.py::test_verify_otp_replay_prevented PASSED        [ 35%]
tests/test_d1_s3_auth.py::test_verify_otp_rate_limiting PASSED           [ 42%]
tests/test_d1_s3_auth.py::test_logout_and_revocation PASSED              [ 50%]
tests/test_d1_s3_auth.py::test_cross_flat_access_idor_denied PASSED      [ 57%]
tests/test_d1_s3_auth.py::test_committee_individual_flat_access_strictly_denied PASSED [ 64%]
tests/test_d1_s3_auth.py::test_family_member_permission_enforcement PASSED [ 71%]
tests/test_d1_s3_auth.py::test_guard_access_to_finance_denied PASSED     [ 78%]
tests/test_d1_s3_auth.py::test_demo_hint_hidden_in_production PASSED     [ 85%]
tests/test_d1_s3_auth.py::test_otp_request_rate_limiting PASSED          [ 92%]
tests/test_d1_s3_auth.py::test_database_persisted_revoked_token PASSED   [100%]
======================== 14 passed in 6.66s ========================
```
