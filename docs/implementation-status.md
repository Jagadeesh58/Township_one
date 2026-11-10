# Township One — Implementation Status

Repository: https://github.com/Jagadeesh58/Township_one.git

This document maps the Brief 2 scope to the current source tree. A code path or screen is not, by itself, proof that an end-to-end workflow has passed. Executed results are recorded in `docs/reports/summary.json` when the release verifier has run.

## Brief 2 requirement map

| Requirement | Implementation location | Evidence / limitation |
|---|---|---|
| Resident installable web application | `frontend/`, PWA manifest and service worker | Installable shell; browser installation must be checked in a supported browser. |
| OTP login and flat membership | `backend/app/api/auth.py`, `backend/app/core/security.py`, membership models | Development/demo OTP is simulated; no real SMS transport is implemented. |
| Family and tenant access | `FlatMembership`, resident API authorization | Verify role/member permission tests and cross-flat denial. |
| Notices | `backend/app/api/notices.py`, `frontend/src/pages/ResidentNoticesPage.tsx`, `CommitteeNoticeEditor.tsx` | Revision-aware read tracking, audience scoping and English/Hindi/Marathi content; browser UI tests must be run with supported Node dependencies. |
| Area-based billing | Billing services and `Bill`/`BillingRule` models | Rate in the reference seed is ₹6.50/sq ft/month. Late-fee settings are illustrative pending federation approval. |
| Test payment, receipts and flat ledger | `backend/app/services/payments.py`, payment API and resident billing UI | Simulated payment only; no real gateway collection. |
| Bank CSV matching | `backend/app/services/bank_matching.py`, bank APIs and Accounts UI | Synthetic canonical CSV only. Ambiguous rows must be held for Accounts review. Run corpus and PostgreSQL tests for current measured outcome. |
| Complaint categories and photos | Complaint API, service and resident UI | Private local photo storage and server authorization. Complaint-photo retention policy is separate from visitor-photo retention. |
| Automatic complaint assignment and response timer | Complaint service and Help Desk UI | Verify with `tests/test_complaints.py` and API workflow tests. |
| AI category and urgency suggestions | `backend/app/ml/`, classifier service and provider adapter | Groq requires server-side configuration; local model uses synthetic training data. No operational accuracy claim is made. |
| Human correction and emergency rules | Classification decision and safety-event services | Deterministic safety matching must remain independent of AI output. Verify regression tests. |
| Duplicate complaint linking | Similarity service and incident-group models | Staff confirms links; individual complaints remain open and independently tracked. |
| Visitor entry and resident approval | Visitor API/service and `GuardGateTerminal.tsx` | Online lifecycle is covered by visitor tests. Server checks guard gate scope and active resident membership. |
| Pre-approved guest credentials | Visitor service and ECDSA P-256 signing key | Configure a stable `SIGNING_KEY` or `SIGNING_KEY_FILE` to retain credential validity across restarts. |
| Offline gate capture | `frontend/src/lib/gateQueue.ts`, guard page, visitor multipart sync endpoint | IndexedDB stores the actual photo Blob and metadata; upload validates hash and device/gate anchor. Browser reload/reconnect tests require a supported frontend environment. Offline entries are not approved on the disconnected device. During synchronization, the server validates any signed pre-approval credential; entries without a valid pre-approval remain awaiting resident approval. |
| Visitor-photo retention | `purge_visitor_photos` service, token-protected operations endpoint and `.github/workflows/visitor-photo-retention.yml` | Original capture time drives the 90-day rule. The daily workflow is configured in source; owner-managed Render/GitHub secrets and a real hosted run are still required. A stopped PWA cannot run its local expiry sweep. |
| Amenity booking | Amenity API/service and booking page | Slot/capacity tests exist; PostgreSQL row-lock behaviour requires PostgreSQL execution. |
| Committee reporting | Committee API and dashboard | Aggregates and exports are present; PostgreSQL and browser verification must be run independently. |
| English, Marathi and Hindi | `frontend/src/i18n/translations.ts` and notice content fields | Translation completeness is covered by the frontend suite; visual review at 320px requires browser execution. |

## Reference sample data

Seed reference date: `2026-11-06`.

| Flat | Outstanding | Overdue |
|---|---:|---:|
| T07-1203 | ₹0.00 | 0 days |
| T12-0408 | ₹6,370.00 | 47 days |
| T21-1601 | ₹5,660.00 | 18 days |

The seed includes 28 towers, 2,400 flats, 180 staff and four gates. These are synthetic demo records, not live community data.

## Known limitations

- Payment and SMS are not connected to live external providers.
- The production SMS adapter deliberately fails closed until a real gateway transport is added.
- Bank CSV data is synthetic; no bank API is connected.
- Late-fee and grace-period settings are illustrative and require society approval.
- AI training data is synthetic; production performance is not established.
- Development uses private local storage; the hosted adapter uses Cloudinary authenticated assets and application-mediated reads. No live Cloudinary account or real object lifecycle has been exercised in this environment.
- The daily GitHub Actions retention workflow and token-protected endpoint are present in source, but the repository secrets, deployed service and scheduled execution have not yet been configured or verified.
- PWA local expiry work cannot run while the browser is closed or the tablet is powered off.
- PostgreSQL-only concurrency guarantees require execution against PostgreSQL.
- Load testing has not been measured in this environment.
- The frontend verification status depends on installing dependencies under the Node version supported by `frontend/package-lock.json`.
