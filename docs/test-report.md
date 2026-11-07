# TOWNSHIP ONE — MASTER TEST REPORT

**Project:** Township One  
**Date:** November 7, 2026  
**Environment:** Windows / Python 3.11.9 / Pytest 8.4.2 / Node 24.16.0 / Vite 6.4.5  
**Result:** 44 / 44 Automated Tests PASSED (100%)  

---

## 1. Test Suite Summary

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.4.2, pluggy-1.6.0 -- C:\Users\Jagadeesh\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
hypothesis profile 'default'
rootdir: C:\Township_one
configfile: pyproject.toml
plugins: anyio-4.13.0, hypothesis-6.170.14, asyncio-0.26.0, cov-7.1.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 44 items

tests/test_d1_s1_health.py::test_health_check_endpoint PASSED            [  2%]
tests/test_d1_s1_health.py::test_api_prefix_health_endpoint PASSED       [  4%]
tests/test_d1_s1_health.py::test_404_error_format PASSED                 [  6%]
tests/test_d1_s1_health.py::test_database_url_separation PASSED          [  9%]
tests/test_d1_s1_health.py::test_production_guard_rejects_default_secret PASSED [ 11%]
tests/test_d1_s1_health.py::test_alembic_url_resolution_dynamic PASSED   [ 13%]
tests/test_d1_s2_seed.py::test_seed_entity_counts PASSED                 [ 15%]
tests/test_d1_s2_seed.py::test_sample_flat_t07_1203_exact_values PASSED  [ 18%]
tests/test_d1_s2_seed.py::test_sample_flat_t12_0408_exact_values PASSED  [ 20%]
tests/test_d1_s2_seed.py::test_sample_flat_t21_1601_exact_values PASSED  [ 22%]
tests/test_d1_s2_seed.py::test_family_member_permission_boundaries PASSED [ 25%]
tests/test_d1_s2_seed.py::test_ten_linked_lift_complaints_with_distinct_reporters PASSED [ 27%]
tests/test_d1_s2_seed.py::test_reviewer_role_assignments PASSED          [ 29%]
tests/test_d1_s2_seed.py::test_seed_safety_rejects_unconfirmed_destructive_reset PASSED [ 31%]
tests/test_d1_s2_seed.py::test_seed_safety_rejects_remote_database_urls PASSED [ 34%]
tests/test_d1_s3_auth.py::test_request_otp_success PASSED                [ 36%]
tests/test_d1_s3_auth.py::test_request_otp_nonexistent_user PASSED       [ 38%]
tests/test_d1_s3_auth.py::test_verify_otp_valid PASSED                   [ 40%]
tests/test_d1_s3_auth.py::test_verify_otp_invalid PASSED                 [ 43%]
tests/test_d1_s3_auth.py::test_verify_otp_replay_prevented PASSED        [ 45%]
tests/test_d1_s3_auth.py::test_verify_otp_rate_limiting PASSED           [ 47%]
tests/test_d1_s3_auth.py::test_logout_and_revocation PASSED              [ 50%]
tests/test_d1_s3_auth.py::test_cross_flat_access_idor_denied PASSED      [ 52%]
tests/test_d1_s3_auth.py::test_committee_individual_flat_access_strictly_denied PASSED [ 54%]
tests/test_d1_s3_auth.py::test_family_member_permission_enforcement PASSED [ 56%]
tests/test_d1_s3_auth.py::test_guard_access_to_finance_denied PASSED     [ 59%]
tests/test_d1_s3_auth.py::test_demo_hint_hidden_in_production PASSED     [ 61%]
tests/test_d1_s3_auth.py::test_otp_request_rate_limiting PASSED          [ 63%]
tests/test_d1_s3_auth.py::test_database_persisted_revoked_token PASSED   [ 65%]
tests/test_d1_s4_billing.py::test_principal_calculation_exact PASSED     [ 68%]
tests/test_d1_s4_billing.py::test_demo_late_fee_boundaries PASSED        [ 70%]
tests/test_d1_s4_billing.py::test_grace_period_enforcement PASSED        [ 72%]
tests/test_d1_s4_billing.py::test_billing_summary_aggregates_multiple_unpaid_bills PASSED [ 75%]
tests/test_d1_s4_billing.py::test_billing_cross_flat_idor_denied PASSED  [ 77%]
tests/test_d1_s4_billing.py::test_duplicate_bill_generation_rejected PASSED [ 79%]
tests/test_d1_s5_payments.py::test_pay_already_paid_bill_rejected PASSED [ 81%]
tests/test_d1_s5_payments.py::test_invalid_payment_outcomes_rejected PASSED [ 84%]
tests/test_d1_s5_payments.py::test_payment_failure_pending_expired_leaves_dues_intact PASSED [ 86%]
tests/test_d1_s5_payments.py::test_cross_flat_idempotency_key_replay_and_leakage_prevention PASSED [ 88%]
tests/test_d1_s5_payments.py::test_idempotency_key_payload_divergence_returns_409 PASSED [ 90%]
tests/test_d1_s5_payments.py::test_cross_resident_receipt_and_payment_access_denied PASSED [ 93%]
tests/test_d1_s5_payments.py::test_family_member_without_pay_permission_blocked PASSED [ 95%]
tests/test_d1_s5_payments.py::test_payment_exceeding_balance_rejected PASSED [ 97%]
tests/test_d1_s7_integration.py::test_full_day1_resident_billing_and_payment_journey PASSED [100%]

======================= 44 passed, 2 warnings in 16.91s =======================
```

---

## 2. Frontend Production Build Verification
```text
vite v6.4.5 building for production...
transforming...
✓ 39 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.80 kB │ gzip:  0.44 kB
dist/assets/index-CxXMJiAj.css    0.58 kB │ gzip:  0.39 kB
dist/assets/index-BtSFoCh6.js   265.17 kB │ gzip: 79.48 kB
✓ built in 7.14s
```
