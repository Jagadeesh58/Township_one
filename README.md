# Township One

**Gated township resident and operations platform** · Company A, Pune · Brief 2

Repository: https://github.com/Jagadeesh58/Township_one

Township One consolidates the high-frequency tasks of a 2,400-home gated community: maintenance dues, test payments, complaint tracking, visitor approvals, notices and amenity bookings. Role-specific workspaces support accounts reconciliation, help-desk triage, guard operations and committee oversight.

## Product surface

| Workspace | What works in the prototype |
|---|---|
| Resident | OTP demo login, flat-linked bills and ledger, simulated payment and receipt, complaints, visitor approvals, guest pre-approvals, notices and amenity booking. |
| Accounts | CSV statement preview/import, evidence-based matching, duplicate checks and a review queue. Ambiguous rows are held; AI never posts a payment. |
| Help desk | Assigned complaint queue, category/urgency suggestions, status history, response timers, manual correction and safety escalation. |
| Gate guard | Gate-scoped visitor check-in, resident approval, photo capture, pre-approved guest verification and offline queue/reconnect sync. |
| Committee | Collection/dues ageing and complaint timing summaries, plus notice editing and publication. |

The interface supports English, Marathi and Hindi. The resident experience is mobile-first; guard controls are deliberately large and high-contrast.

## Why this is more than a UI demo

- Financial calculations use `Decimal`; payments are simulated and idempotent. The bank matcher uses amount, reference, UPI and flat/bill evidence, then routes uncertain rows to Accounts review.
- Complaint category and urgency are suggested by a local TF-IDF / Multinomial Naive Bayes model. Deterministic emergency phrase rules escalate safety events independently of model output. Staff can correct a category; duplicates are linked, not silently closed.
- Visitor access is role-, flat-, gate- and device-scoped. Offline visit records and image Blobs queue in IndexedDB and sync on reconnection.
- Visitor and complaint images are validated and re-encoded to strip metadata. They are stored privately and served through application routes; hosted deployments use Cloudinary authenticated assets, read only through authorized application routes.
- Visitor-photo retention is calculated from capture time plus 90 days. A token-protected API operation and scheduled GitHub Actions workflow are included for hosted cleanup.
- The hosted container applies Alembic migrations and optionally performs a guarded, non-destructive demo seed. Remote destructive reset is rejected.

## Architecture

- **Frontend:** React 19, TypeScript, Vite and installable PWA.
- **API:** FastAPI, Pydantic and SQLAlchemy 2.0.
- **Database:** PostgreSQL for shared deployment; SQLite is used only for portable test runs.
- **Migrations:** Alembic.
- **AI:** local scikit-learn classifier by default; optional server-side Groq adapter when a current free quota is available. No external AI key is required for the baseline workflow.
- **Storage:** local private adapter in development; Cloudinary authenticated private assets in the hosted profile (a $0 Free plan with no credit card required).

The hosted profile serves the compiled frontend and API from a single Render Docker service, so the browser uses same-origin `/api/v1` requests rather than a separately deployed frontend.

## Local quick start

Prerequisites: Python 3.11+, Node.js 22.22.2+ or 24.15+, npm, Docker Engine with Compose, and Git.

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # Windows PowerShell: .venv\\Scripts\\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   ```

2. Install backend and frontend dependencies:

   ```bash
   python -m pip install -r requirements.txt
   cd frontend && npm ci && cd ..
   ```

3. Start PostgreSQL, migrate and seed the synthetic dataset:

   ```bash
   docker compose up -d db
   alembic upgrade head
   python -m seed.seed_data --mode safe
   ```

4. Start FastAPI and Vite together:

   ```bash
   python scripts/dev.py
   ```

Open `http://127.0.0.1:5173`. API documentation: `http://127.0.0.1:8000/docs`; health/readiness: `http://127.0.0.1:8000/health`.

Copy `.env.example` to `.env` for local overrides. Never commit `.env` or real personal/financial data. Local DB credentials and the demo OTP are for development only.

## Free hosted reviewer deployment

The repo includes `Dockerfile`, `entrypoint.sh`, `requirements-runtime.txt`, `.dockerignore` and `render.yaml` for a free-tier **demo** profile:

| Component | Free option | Responsibility |
|---|---|---|
| Web app + API | Render Free Docker web service | One origin; serves built React app and FastAPI. It sleeps after inactivity and can have a cold start. |
| PostgreSQL | Neon Free | Shared relational database and migrations. Free plan has account-level compute/storage/egress limits. |
| Private photos | Cloudinary Free | Authenticated assets; signed access remains behind application routes. Free plan is $0 and does not require a credit card; usage is limited by monthly credits. |
| Retention scheduler | GitHub Actions (public repository) | Daily call to the token-protected 90-day visitor-photo purge endpoint. |
| Complaint AI | Local scikit-learn model | No external model API or API key required. |

Follow [`deployment.md`](deployment.md) to create the free resources, add secrets and deploy. This is a reviewer/demo setup, not a production SLA. Free plans can sleep, throttle, change quotas or introduce cold starts; monitor limits and disable resources you no longer need. No app URL is claimed until the owner completes provider setup.

## Demo data and reviewer accounts

The seed represents 28 towers, 2,400 flats, 180 staff and four gates. The financial snapshot date is **6 November 2026**. The maintenance principal rate is ₹6.50 per sq ft per month. The due-date, grace-period and late-interest configuration remains illustrative and must be approved against the society's bye-laws before real billing.

| Flat | Resident | Outstanding | Overdue |
|---|---|---:|---:|
| T07-1203 | Neeraj Kulkarni | ₹0.00 | 0 days |
| T12-0408 | Swati Joshi (tenant) | ₹6,370.00 | 47 days |
| T21-1601 | Aamir Shaikh | ₹5,660.00 | 18 days |

For a demo environment, set `DEMO_OTP_CODE=123456` and use one of the synthetic reviewer identities documented in [`deployment.md`](deployment.md). Do not expose fixed OTP login in a real resident service.

## Verification

<!-- verification-summary:start -->
| Check | Result | Measured evidence |
|---|---|---|
| `postgresql_migrations` | **BLOCKED** | Set PG_MIGRATION_DATABASE_URL to a disposable PostgreSQL database; no PostgreSQL server was available for this run. |
| `ruff_check` | **BLOCKED** | Run this quality command in the configured development/CI environment; this verifier does not invoke additional tool processes before the full test run. |
| `ruff_format` | **BLOCKED** | Run this quality command in the configured development/CI environment; this verifier does not invoke additional tool processes before the full test run. |
| `mypy` | **BLOCKED** | Run this quality command in the configured development/CI environment; this verifier does not invoke additional tool processes before the full test run. |
| `frontend_typescript` | **PASS** | TypeScript compiler passed (v24.16.0). |
| `frontend_tests` | **PASS** | npm notice run township-one-frontend@1.0.0 test npm notice run vitest run [90mstderr[2m \| src/__tests__/residentHome.test.tsx[2m > [22m[2mResidentHomePage UI Integration & Sta |
| `frontend_build` | **PASS** | npm notice run township-one-frontend@1.0.0 build npm notice run tsc --noEmit && vite build  |
| `postgresql_backend_tests` | **BLOCKED** | Set PG_DATABASE_URL and TEST_DATABASE_URL to a dedicated PostgreSQL test database. The three row-lock tests are not verified by SQLite. |
| `backend_tests` | **PASS** | 203 passed, 3 skipped, 14 warnings in 467.05s (0:07:47) |
| `database_seed_and_ground_truth` | **PASS** | flats: 2400, gates: 4, staff: 180, towers: 28 |
| `backend_coverage` | **PASS** | 203 passed, 3 skipped, 14 warnings in 467.05s (0:07:47); coverage 90.01% |
| `wording_scan` | **PASS** | 0 finding(s). |

Overall result: **FAIL**
<!-- verification-summary:end -->

The authoritative command output is recorded in `docs/reports/summary.json` and the generated evidence table in `TDD.docx`. A blocked or skipped check is not described as a pass. In particular, SQLite cannot verify PostgreSQL row locks and a local Node 22.16 environment is below the package's supported Node engine. Run the Docker frontend build with its Node 24.15 stage and run the PostgreSQL workflow before treating those checks as complete.

Useful commands:

```bash
python -m pytest -rs
python scripts/verify_release.py
```

Frontend checks (with a supported Node version and `npm ci`):

```bash
cd frontend
npx tsc --noEmit
npm test
npm run build
```

## Known limits and scope boundaries

- The payment flow is simulated; it does not collect money. SMS/OTP delivery is simulated in demo; there is no live SMS transport.
- Bank reconciliation uses a synthetic CSV adapter, not a live bank feed. Tally remains outside the application.
- The local AI model uses synthetic training examples; production accuracy has not been established. Groq is optional, quota-limited and not required.
- The Cloudinary and Neon accounts, Render service and GitHub secrets must be created by the repository owner. Provider free quotas are finite and can change; no live host URL or real provider operation is claimed in this source archive.
- Render's local filesystem is ephemeral; hosted photo storage must stay on authenticated Cloudinary assets. The scheduled action must be enabled and monitored. Browser-side PWA queue expiry cannot execute while a device is powered off.
- PostgreSQL row-lock/concurrency behaviour, browser PWA offline/reconnect behaviour, load and security under real traffic require dedicated hosted verification.
- Actual bye-law billing parameters, DPDP notices/retention procedures, gate signage and resident-facing privacy processes require client review before production use.

## Assignment scope exclusions

No general accounting/Tally replacement, CCTV or boom-barrier hardware integration, classifieds/marketplace, live bank integration, real payment gateway, or production SMS/WhatsApp integration is claimed.
