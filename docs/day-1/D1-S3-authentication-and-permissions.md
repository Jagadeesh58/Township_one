# D1-S3 — Authentication and Permissions

**Day:** Day 1  
**Session ID:** D1-S3  
**Session Name:** Authentication and permissions  
**Responsibility:** OTP, sessions, flat memberships, family/tenant and roles  

---

## 1. Objective
Implement robust authentication and authorization controls: rate-limited phone OTP login, single-use OTP replay prevention, cryptographically signed JWT tokens with unique JTI claims, persistent server-side token revocation across process restarts, and strict role-based access control preventing IDOR and unauthorized staff/committee inspection of individual flat finances.

---

## 2. Files Created or Modified
- `backend/app/models/entities.py` — Added `RevokedToken` model with fields `id`, `token_jti`, `user_id`, `revoked_at`, and `expires_at`.
- `backend/app/core/security.py` — Added JTI to JWT tokens, persistent revocation in SQLite/PostgreSQL `revoked_tokens` table, request-rate limiting (max 5 requests / 10 minutes), and strict IDOR/RBAC rules in `verify_flat_access()`.
- `backend/app/api/auth.py` — Production guard omitting `demo_hint` when `APP_ENV=production`, rate limit enforcement, and persistent token revocation on `/auth/logout`.
- `tests/test_d1_s3_auth.py` — Comprehensive 14-test suite validating OTP flow, replay prevention, rate limiting, token revocation, production guards, and role permissions.

---

## 3. Implementation Completed
1. **Rate-Limited OTP Challenges:**
   - Enforced maximum of 5 OTP request challenges per 10-minute sliding window per phone number.
   - Enforced maximum of 3 invalid OTP verification attempts before lockout.
   - OTP codes are strictly single-use; subsequent verification attempts return HTTP 400.
2. **Production Safety Guards:**
   - In development/demo, responses contain `demo_hint: "Demo OTP is 123456"`.
   - When `APP_ENV=production`, `demo_hint` is completely omitted.
3. **Cryptographic JWTs & Token Revocation:**
   - Each issued token contains a unique `jti` (UUID v4) claim and expiration timestamp.
   - On logout, `revoke_token_persisted()` records the `jti` in memory and persists to the `revoked_tokens` table.
   - `get_current_user` rejects any token matching a revoked JTI with HTTP 401 Unauthorized.
4. **Strict Server-Side RBAC & IDOR Boundaries:**
   - Residents cannot access other flats' billing or payment records (HTTP 403 Forbidden).
   - Family members without `can_pay_bills=True` can view billing summaries but are barred from checkout (HTTP 403 Forbidden).
   - Committee members can view township aggregate reports (`/api/v1/billing/committee/aggregate`) but are strictly forbidden from viewing individual flat summaries (`/api/v1/billing/flats/{id}/summary`) with message: `"Access denied: Committee members can only access aggregate reports, not individual flat records."`.
   - Gate Security Guards attempting to view flat financial summaries are denied with message: `"Access denied: Gate security staff do not have access to billing or payment records."`.

---

## 4. API Endpoints
- `POST /api/v1/auth/otp/request` — Initiates phone OTP challenge (rate-limited).
- `POST /api/v1/auth/otp/verify` — Validates OTP, issues JWT with unique JTI.
- `GET /api/v1/auth/me` — Returns authenticated user profile, roles, and linked flat memberships.
- `POST /api/v1/auth/logout` — Revokes JWT token persistently.

---

## 5. Tests Executed and Results
Command:
```bash
py -3.11 -m pytest tests/test_d1_s3_auth.py -v
```
Output:
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

---

## 6. Acceptance Criteria
- [x] OTP replay prevented (HTTP 400).
- [x] OTP rate limiting enforced (HTTP 429).
- [x] Revoked tokens rejected across restarts (HTTP 401).
- [x] Committee & Guards strictly blocked from individual resident finance (HTTP 403).
- [x] Family member fine-grained permissions enforced.

---

## 7. Remaining Defects or Limitations
- SMS gateway integration in demo environment uses simulated delivery; real SMS adapter scheduled for production deployment.
