# Brief 2 Traceability Matrix

This matrix maps every requirement from Part C: Brief 2 (Gated Township Resident App for Company A, Pune) to its Day and Session implementation.

| ID | Requirement / Constraint | Plan Session | Status (Day 1) | Notes & Verification Target |
|---|---|---|---|---|
| B2-01 | Resident installable web app (PWA) | D1-S6 | Day 1 Core | Installable manifest, service worker static cache, mobile-first design |
| B2-02 | OTP login linked to flat | D1-S3 | Day 1 Core | Secure OTP challenge, bounded attempts, rate limiting, flat binding |
| B2-03 | Family and tenant members | D1-S3 | Day 1 Core | FlatMembership roles (Owner, Tenant, Family), server-side permission checks |
| B2-04 | Notices | D1-S6 / D3-S5 | Day 1 Seed & UI | Notice models, read receipts, home screen alerts |
| B2-05 | Maintenance billing by flat area & rate (₹6.50/sq ft) | D1-S4 | Day 1 Core | Exact math for sample flats: T07-1203, T12-0408, T21-1601 |
| B2-06 | Late fees per society bye-laws | D1-S4 | Day 1 Core | Versioned configurable billing rule, demo assumption labelled |
| B2-07 | Online payment in test mode | D1-S5 | Day 1 Core | Simulated checkout with SUCCESS, PENDING, FAILED, EXPIRED states |
| B2-08 | Bank statement matching | D2-S1, D2-S2 | Day 2 Hard Part | CSV ingestion, exact match criteria, Accounts review queue |
| B2-09 | Receipts | D1-S5 | Day 1 Core | Auto-generated receipt after validated SUCCESS payment, reconciled |
| B2-10 | Ledger per flat | D1-S4 | Day 1 Core | Per-flat running statement with debits, credits, adjustments |
| B2-11 | Complaints with category & photo | D2-S3 | Day 2 Core | Category selection, private attachment URL, incident details |
| B2-12 | Auto-assignment & response timer | D2-S4 | Day 2 Core | Deterministic skill/shift assignment, SLA clock |
| B2-13 | Status updates & closure rating | D2-S3 | Day 2 Core | Audit timeline, 1-5 star resident rating on resolution |
| B2-14 | Gate visitor management & photos | D3-S1, D3-S2 | Day 3 | Guard tablet entry, resident push approval, offline queue |
| B2-15 | Pre-approved guest codes | D3-S3 | Day 3 | Secure bounded-use digital entry codes |
| B2-16 | Amenity booking (slots, rules, fees) | D3-S4 | Day 3 | Clubhouse & court booking with strict concurrency locking |
| B2-17 | Committee dashboard & monthly report | D3-S6 | Day 3 Core | Collections, dues ageing, complaint metrics, exportable |
| B2-18 | DPDP Act 2023 compliance (90-day photo deletion) | D2-S7, D3-S8 | Day 2 / Day 3 | Scheduled HMAC retention runner, gate privacy notice |
| B2-19 | 2-tap rule from resident home | D1-S6 | Day 1 Core | Quick actions for dues, payment, complaint, visitors |
| B2-20 | Trilingual support (EN, MR, HI) | D1-S6 | Day 1 Core | Complete i18n localization for all core user journeys |
| B2-21 | 2,400 flats / 28 towers / 180 staff / 4 gates | D1-S2 | Day 1 Seed | Synthetic deterministic seed matching township specification |
