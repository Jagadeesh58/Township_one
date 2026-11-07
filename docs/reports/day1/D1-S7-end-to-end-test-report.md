# D1-S7 End-to-End Test Report — Integration and Day 1 Verification

**Date:** 2026-11-07  
**Session:** D1-S7  
**Runner:** Pytest 8.4.2 / Python 3.11.9  
**Target:** `tests/test_d1_s7_integration.py` and Full Regression Suite  

---

## 1. Execution Summary
- **Total Test Suites:** 6
- **Total Tests:** 44
- **Passed:** 44
- **Failed:** 0
- **Pass Rate:** 100.0%
- **Duration:** 16.91s
- **Status:** PASS

---

## 2. End-to-End Resident Journey Results

| Step | Operation | Actor / Context | Observed Result | Invariant Verified |
|---|---|---|---|---|
| 1 | Phone OTP Request & Verify | Swati Joshi (9876543211) | 200 OK, JWT issued with T12-0408 TENANT membership | Authentication & Flat Membership |
| 2 | Billing Summary Query | T12-0408 | 200 OK, 980 sqft, ₹6,370.00 current due, overdue >40 days | Area Calculation & Overdue Tracking |
| 3 | Simulated Checkout (FAILED) | T12-0408, ₹6,370.00 | 200 OK, status=FAILED, receipt=null, dues remain ₹6,370.00 | Failed Payment Zero Side-Effect |
| 4 | Simulated Checkout (SUCCESS) | T12-0408, ₹6,370.00, key=IDEM-001 | 200 OK, status=SUCCESS, receipt issued, dues drop to ₹0.00 | Atomic Payment Allocation |
| 5 | Flat Ledger Inspection | T12-0408 | 200 OK, DEBIT ₹6,370 + CREDIT ₹6,370 -> Balance ₹0.00 | Dual-Entry Ledger Reconciliation |
| 6 | Retry on Paid Bill | T12-0408, ₹1,000.00 | 400 Bad Request ("already fully paid") | Duplicate Payment Prevention |
| 7 | Persona Verification | Neeraj Kulkarni (T07-1203) | 200 OK, 1,150 sqft, ₹7,475 billed, ₹7,475 paid, balance ₹0.00 | Reviewer Persona 1 (Paid) |
| 8 | Persona Verification | Aamir Shaikh (T21-1601) | 200 OK, 1,640 sqft, ₹10,660 billed, ₹5,000 paid, balance ₹5,660.00 | Reviewer Persona 2 (Partial) |
| 9 | Committee Boundary Check | Vikram Sardesai (9876543250) | Aggregate 200 OK; Individual flat drilldown 403 Forbidden | Committee Role Scoping |
| 10 | Family Member Permissions | Ananya Kulkarni (9876543213) | Billing Summary 200 OK; Payment Checkout 403 Forbidden | Fine-Grained Permissions |

---

## 3. Full Regression Suite Log
```text
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
