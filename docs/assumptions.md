# Township One - Assumptions & Limitations Register

Per assignment instructions: "Use only the information in the problem statement. Label every assumption in your TDD."

| Topic | Stated in Brief | Assumption / Prototype Treatment |
|---|---|---|
| Township Size | 2,400 flats in 28 towers, 180 staff, 4 gates | Seeded synthetic dataset matches these exact parameters. |
| Maintenance Rate | ₹6.50 per sq ft per month | Used for all principal maintenance calculations. |
| Maharashtra Bye-law Late Fees | Mentioned as "per society bye-laws under Maharashtra cooperative law" | Actual society rule not supplied. Prototype implements an illustrative demo rule (e.g. 18% p.a. simple interest after 15th of the month), labelled clearly as **DEMO ASSUMPTION PENDING FEDERATION APPROVAL**. |
| Bank Matching Format | "Matching payments from a bank CSV" | Canonical demo CSV format defined (`DEMO_BANK_CSV_V1`). Strict matching on amount + UTR + registered UPI; ambiguous rows go to Accounts review. |
| Payment Gateway & SMS | Mock payments and messages permitted | In-app simulated payment gateway with deterministic state triggers (SUCCESS, PENDING, FAILED, EXPIRED). Notifications logged in outbox. |
| DPDP Act 2023 Compliance | 90-day retention for visitor photos | Background/scheduled retention runner purges photos at original `capture_time + 90 days`. Gate notice displayed. |
| Offline Gate Architecture | "Gate tablets must keep working through network drops" | Client-side IndexedDB persists events & photos with SHA-256 validation. Sync is idempotent upon network restoration. |
