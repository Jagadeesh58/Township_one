# Township One — Assumptions & Limitations Register

Per assignment instructions: *"Use only the information in the problem statement. Label every assumption in your TDD."*

---

## 1. Regulatory & Bye-Law Assumptions

| Topic | Stated in Brief | Assumption / Prototype Treatment |
|---|---|---|
| **Township Scale** | 2,400 flats in 28 towers, 180 staff, 4 gates | Seeded synthetic dataset matches these exact parameters (T01-T28, 2400 flats, 180 staff members, 4 security gates). |
| **Maintenance Rate** | ₹6.50 per sq ft per month | Used for all principal maintenance calculations (`area_sqft * 6.50`). |
| **Maharashtra Society Bye-Laws Late Fees** | Mentioned as "per society bye-laws under Maharashtra cooperative law" | Bye-law formula text not fully specified in Brief. Prototype implements an illustrative demo rule: simple interest at 18.00% p.a. calculated daily on unpaid balance past the 5-day grace period (due on 15th, interest starting 21st). Clearly labelled in all UI and API responses as: **"DEMO ASSUMPTION PENDING SOCIETY FEDERATION APPROVAL"**. |
| **DPDP Act 2023 Compliance** | 90-day retention for visitor photos | Scheduled retention job marks photos for physical deletion at `capture_time + 90 days`. Gate notice displayed. |
| **Offline Gate Operations** | "Gate tablets must keep working through network drops" | Client-side IndexedDB persists events & photos with SHA-256 validation. Sync is idempotent upon network restoration. |

---

## 2. Infrastructure & Security Assumptions

| Topic | Stated in Brief | Assumption / Prototype Treatment |
|---|---|---|
| **SMS Gateway** | Mock payments and messages permitted | SMS delivery is simulated via in-app `demo_hint` in non-production environments (`APP_ENV != production`). In production mode, `demo_hint` is strictly suppressed. |
| **Payment Gateway** | Mock payments and messages permitted | In-app simulated payment gateway with deterministic state triggers (`SUCCESS`, `PENDING`, `FAILED`, `EXPIRED`). Payment attempts are cryptographically fingerprinted with SHA-256 and bound to authenticated principal, flat, bill, amount, currency, and payment method. |
| **Token Revocation** | Secure session management | Persistent database table `revoked_tokens` tracks revoked JWT `jti` claims across server restarts, backed by an in-memory set for low-latency lookups. |
| **Database Engines** | SQLite / PostgreSQL | Local zero-dependency SQLite for development, tests, and reviewer demonstration (`township_one.db` / `township_one_test.db`). Full PostgreSQL compatibility enabled via `psycopg` for production deployment. |
