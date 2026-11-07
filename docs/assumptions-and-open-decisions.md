# Township One — Assumptions & Open Architecture Decisions

## 1. Domain & Statutory Assumptions Register

Per project specifications, every design assumption is explicitly recorded, categorized, and tagged with its prototype implementation treatment:

| Topic | Stated in Brief | Assumption / Prototype Treatment | Validation Status |
|---|---|---|---|
| **Township Scale** | 2,400 flats in 28 towers, 180 staff, 4 gates | Seeded synthetic dataset matches these exact parameters (T01-T28, 2,400 flats, 180 staff, 4 gates). | **Verified** |
| **Maintenance Rate** | ₹6.50 per sq ft per month | Used for all principal maintenance calculations (`area_sqft * 6.50`). | **Verified** |
| **Maharashtra Society Late Fees** | Mentioned as "per society bye-laws under Maharashtra cooperative law" | Bye-law formula text not fully specified in Brief. Prototype implements an illustrative demo rule: simple interest at 18.00% p.a. calculated daily on unpaid balance past the 5-day grace period. Clearly labelled in UI, API, and schemas as: **"Illustrative demo calculation pending society federation approval (not an approved legal rate)"**. | **Documented & Configurable** |
| **Reference Snapshot Date** | Standardized demonstration timeline | Baseline date locked to `2026-11-06T00:00:00Z` (`DEMO_AS_OF_DATE`) across database, seed script, API responses, and test assertions. | **Verified** |
| **SMS Delivery** | Mock payments and messages permitted | In development and testing, OTP is provided in `demo_hint` (`123456`). In production mode, `demo_hint` is suppressed and random cryptographically secure OTPs are issued. | **Verified** |
| **Payment Gateway** | Mock payments and messages permitted | In-app simulated payment gateway with deterministic state triggers (`SUCCESS`, `PENDING`, `FAILED`, `EXPIRED`). Payment requests are cryptographically fingerprinted with SHA-256 and bound to authenticated principal, flat, bill, amount, currency, and method. Disabled in production. | **Verified** |
| **DPDP Act 2023 Compliance** | 90-day retention for visitor photos | Scheduled retention policy tags photos for physical deletion at `capture_time + 90 days`. Gate notice displayed. | **Architected** |

---

## 2. Open Technical Decisions & Future Enhancements

1. **Production SMS Provider Integration:**
   - *Current State:* Simulated OTP with cryptographic salt storage.
   - *Decision:* Integrate Twilio or MSG91 gateway in production via `SMS_PROVIDER_API_KEY`.
2. **Payment Gateway Webhooks:**
   - *Current State:* Client-initiated simulated checkout with row-level locking.
   - *Decision:* When integrating live Razorpay or Cashfree gateways, incorporate asynchronous webhook signature verification (`X-Razorpay-Signature`) and reconciliation queue.
3. **Automated Late Fee General Body Approval:**
   - *Current State:* Configurable interest rule engine with leap year support.
   - *Decision:* Provide a committee administration panel to adjust annual rate (e.g. 12% vs 18%) or switch between simple and compound interest upon society general body resolution.
