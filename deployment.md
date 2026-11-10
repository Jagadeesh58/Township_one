# Township One — Deployment and Local Operations

Repository: https://github.com/Jagadeesh58/Township_one

This guide covers the local developer setup and a free-tier reviewer deployment. The hosted profile is prepared in source, but no public app URL is claimed until the repository owner creates and configures the external accounts. Use synthetic data only.

## 1. Free hosted architecture

| Service | Selected plan | Purpose |
|---|---|---|
| Render | Free Docker web service | One service serves the React build and FastAPI API from the same origin. |
| Neon | Free PostgreSQL | Shared database with TLS. Use the pooled connection URL when available. |
| Cloudinary | Free plan ($0, no credit card) | Authenticated private images; the app retrieves them through short-lived signed URLs and authorized application routes. |
| GitHub Actions | Free workflow for a public repository | Daily 90-day photo-retention call. |
| Complaint AI | Local scikit-learn classifier | No paid model API is needed. Groq is optional and should remain unset unless a current free quota is available. |

All selected services are configured on their $0/free allowances; no paid model, payment gateway, SMS API or paid database plan is required. Free plans are quota-bound, can sleep or throttle, and can change. Keep Render on Free, Neon on Free, and Cloudinary on its Free plan. Do not add a payment method or upgrade a provider plan. Render suspends free services instead of billing for certain over-limit usage when no payment method is attached; Neon Free suspends compute at the quota rather than billing overages. Cloudinary currently advertises a $0 Free plan without a credit card and a finite monthly credit allowance. Stop uploads if you approach the allowance rather than upgrading. The app still runs locally with private local storage. This is a challenge demo, not a production SLA or a guarantee that a provider will never change its free limits.

## 2. Create the free resources

### A. Neon PostgreSQL

1. Create a Neon account and a free project in a region close to Singapore/India.
2. Create a database for Township One and copy its **pooled** connection string.
3. Convert the URL prefix from `postgresql://` to `postgresql+psycopg://` and retain `sslmode=require`. Keep the username/password/host private.
4. Paste it into Render as `DATABASE_URL`. The container runs `alembic upgrade head` before starting the API.

Do not use the local Docker Compose credentials for a hosted database. Keep a separate disposable test database for PostgreSQL concurrency tests.

### B. Cloudinary Free private image store

1. Create a Cloudinary account using the Free plan. Its current published offer is **$0 and no credit card is required**.
2. From the product environment dashboard, copy the cloud name, API key and API secret. Keep the API secret private.
3. In Render, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` and `CLOUDINARY_API_SECRET`.
4. The Blueprint selects `STORAGE_BACKEND=cloudinary`. The app uploads images with Cloudinary delivery type `authenticated`; public delivery URLs are not used. Reads are performed server-side through short-lived signed download URLs, after the application's own authorization and HMAC checks.
5. Keep the Cloudinary account on Free. Monitor the monthly credit allowance and stop adding uploads when close to the limit. Do not add a payment method or upgrade for this assignment.

Cloudinary's Free offer currently includes 25 monthly credits. The credit model is shared across storage, delivery bandwidth and transformations, so this is a small-demo allowance, not unlimited image storage. No real account operation was executed during this build; the provider adapter is unit-tested with a mocked SDK.

### C. Render Blueprint

1. Push the public repository to GitHub after you have reviewed and committed the working tree yourself.
2. In Render, choose **New → Blueprint**, connect `Jagadeesh58/Township_one`, and select the repository's `render.yaml`.
3. The Blueprint creates one free Docker web service in Singapore. The Docker builder uses Node 24.15 for the frontend and Python 3.11 for the backend.
4. Add the required environment values listed below. Trigger deployment after all required variables are present.
5. Wait for Render's health check at `/health` to pass. The root URL should serve the frontend; `/docs` serves the API schema.

Render Free services spin down after 15 minutes without inbound traffic and the next request can take around a minute to wake up. The current Free allowance is up to 750 instance-hours per workspace per calendar month; a spun-down service does not consume those hours. The container filesystem is ephemeral, so do not change `STORAGE_BACKEND` to `local` in a hosted deployment. The chosen `cloudinary` adapter keeps visitor/complaint photos outside the container filesystem.

## 3. Required environment variables

`render.yaml` declares the public non-secret defaults and prompts for secret values. Set these in the Render dashboard:

| Variable | Required value / purpose |
|---|---|
| `DATABASE_URL` | Neon pooled PostgreSQL URL with `postgresql+psycopg://` driver and TLS. |
| `SECRET_KEY` | Random high-entropy authentication and signed-URL secret (32+ random characters). |
| `SIGNING_KEY` | Persistent ECDSA P-256 private key in PEM format for guest passes and device time anchors. |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary product-environment cloud name. |
| `CLOUDINARY_API_KEY` | Cloudinary API key. |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret; store only in Render secrets. |
| `RETENTION_JOB_TOKEN` | Long random secret shared with the GitHub Actions repository secret of the same name. |
| `DEMO_OTP_CODE` | Demo-only static OTP; the supplied value in the example is `123456`. |

The Blueprint sets `APP_ENV=demo`, `DEBUG=false`, `STORAGE_BACKEND=cloudinary`, `SEED_DEMO_DATA=true` and `ALLOW_REMOTE_DEMO_SEED=true`. These are intentional reviewer-demo settings. Do not use the fixed OTP or demo seeder in a real deployment.

Optional settings include `GROQ_API_KEY`, `GROQ_MODEL_ID` and `GROQ_TIMEOUT_SECONDS`. Leave `GROQ_API_KEY` empty for the strictest zero-API-cost setup: the local complaint classifier remains active and the AI triage workflow still works. If you choose Groq, create/use a Free-tier key only; do not upgrade the organization to the paid Developer tier. Groq Free is rate-limited and can return HTTP 429, which is handled by local fallback/human review. No external AI API is required for the core workflow.

### Generate the secrets locally

Generate `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate the persistent P-256 `SIGNING_KEY` PEM:

```bash
python -c "from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.primitives import serialization; k=ec.generate_private_key(ec.SECP256R1()); print(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode())"
```

Generate `RETENTION_JOB_TOKEN`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store the values only in Render's environment/secrets UI. Do not paste them into GitHub files, screenshots, issues or this deployment guide. `RETENTION_JOB_TOKEN` must be the same secret in Render and GitHub Actions.

## 4. Safe demo data seeding

The entrypoint runs forward-only Alembic migrations first. Demo seeding is explicitly gated by all of the following:

- `APP_ENV=demo`;
- `SEED_DEMO_DATA=true`;
- `ALLOW_REMOTE_DEMO_SEED=true`;
- the CLI's `--allow-remote-demo-seed` flag; and
- `--mode safe`, which does not drop or reset existing rows.

The safe seeder checks the expected 28 towers, 2,400 flats, 180 staff, four gates and supplied sample balances. It refuses to mutate a partially seeded remote database. **Remote destructive reset is always rejected.** If first deployment seeding is interrupted, inspect the database and resolve it manually rather than trying a reset against the hosted database.

For local development only:

```bash
python -m seed.seed_data --mode safe
```

The destructive reset command is restricted to an explicitly confirmed local demo database:

```bash
python -m seed.seed_data --mode reset-demo --confirm-local-demo
```

Never run the reset command against a shared database.

## 5. Reviewer demo accounts

Use `DEMO_OTP_CODE=123456` for the demo environment. The data is synthetic.

| Role | Phone | Intended access |
|---|---|---|
| Resident tenant — Swati Joshi | `9876543211` | Flat T12-0408 bills, complaints, visitors and notices |
| Help Desk — Ramesh Patil | `9876543220` | Complaint triage, assignment and staff notice operations |
| Guard — Suresh Shinde | `9876543230` | Gate-scoped visitor operations; seeded assignment is Gate 1 |
| Accounts — Anita Deshmukh | `9876543240` | Bank import and review workflow |
| Committee — Vikram Sardesai | `9876543250` | Aggregate committee report and notice editor |
| Admin — System Admin | `9876543200` | Restricted administrative/demo configuration |

The sample flats are `T07-1203` (₹0 outstanding), `T12-0408` (₹6,370 outstanding; 47 days overdue) and `T21-1601` (₹5,660 outstanding; 18 days overdue) at the brief's ₹6.50/sq-ft principal rate. Due date, grace period and interest remain illustrative.

## 6. Enable the visitor-photo retention workflow

Visitor photos must be removed after 90 days from original capture time. The repository includes a daily GitHub Actions workflow at `.github/workflows/visitor-photo-retention.yml`, which calls:

`POST /api/v1/ops/retention/visitor-photos`

The endpoint requires `X-Retention-Job-Token` and fails closed when the token is missing or incorrect.

In the GitHub repository settings, add two Actions repository secrets:

| Secret | Value |
|---|---|
| `TOWNSHIP_API_URL` | Render base URL, e.g. `https://township-one-demo.onrender.com` (no trailing slash). |
| `RETENTION_JOB_TOKEN` | The exact same long random value configured on Render. |

The workflow runs daily at 02:17 UTC (07:47 India time) and can also be started with **Actions → Visitor photo retention → Run workflow**. GitHub scheduled runs can be delayed; monitor the workflow history. The local operator command remains available:

```bash
python -m backend.app.jobs.purge_visitor_photos
```

The purge only records a deletion after the storage adapter confirms the operation. Keep the bucket private and monitor both the scheduled action and the provider usage dashboard.

## 7. Local setup

Prerequisites: Python 3.11+, Node.js 22.22.2+ or 24.15+, npm, Docker Engine and Compose.

```bash
python -m pip install -r requirements.txt
cd frontend && npm ci && cd ..
docker compose up -d db
alembic upgrade head
python -m seed.seed_data --mode safe
python scripts/dev.py
```

Open `http://127.0.0.1:5173`; API docs are at `http://127.0.0.1:8000/docs`. On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

## 8. Environment variables reference

| Variable | Purpose |
|---|---|
| `APP_NAME`, `APP_ENV`, `DEBUG`, `PORT`, `API_PREFIX` | Application runtime. |
| `SECRET_KEY`, `SIGNING_KEY`, `SIGNING_KEY_FILE` | Authentication and signed credentials. |
| `ALLOWED_ORIGINS` | CORS allowlist for local split-origin development. |
| `DATABASE_URL`, `TEST_DATABASE_URL` | Application and separate test databases. |
| `DEMO_AS_OF_DATE`, `DEMO_OTP_CODE`, `OTP_EXPIRY_SECONDS` | Frozen demo snapshot and demo authentication. |
| `SEED_DEMO_DATA`, `ALLOW_REMOTE_DEMO_SEED` | Entrypoint-controlled safe seeding. Remote seeding only works with the explicit CLI flag and demo environment. |
| `MAINTENANCE_RATE_PER_SQFT`, `DEFAULT_GRACE_PERIOD_DAYS`, `DEMO_LATE_FEE_PERCENTAGE_PA` | Illustrative billing rules. |
| `STORAGE_BACKEND`, `STORAGE_DIR` | Local or private object storage adapter. |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Cloudinary authenticated private image storage. |
| `R2_ACCOUNT_ID`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | Optional alternative Cloudflare R2 adapter; not selected by the free no-card profile. |
| `RETENTION_JOB_TOKEN` | Shared secret for scheduled retention endpoint. |
| `GROQ_API_KEY`, `GROQ_MODEL_ID`, `GROQ_TIMEOUT_SECONDS` | Optional complaint-classification provider. Not required. |
| `SMS_PROVIDER_API_KEY` | Reserved placeholder; no real SMS adapter is implemented. |

## 9. Verification

```bash
python -m compileall -q backend seed tests
python -m pytest -rs
python scripts/verify_release.py
```

Frontend checks require a supported Node version:

```bash
cd frontend
npx tsc --noEmit
npm test
npm run build
```

The Docker build provides the expected Node 24.15 frontend builder. PostgreSQL migration and concurrency tests must use a disposable PostgreSQL database; SQLite tests do not prove row-lock behaviour. The release report must preserve blocked/skipped states instead of treating them as passing.

## 10. Explicit limits

- The public app is a reviewer demo. Render Free sleeps after inactivity, may cold-start slowly and has ephemeral local storage. Cloudinary Free is required for hosted images in the no-card setup.
- Neon and Cloudinary Free have finite quotas. Neon suspends compute when the free allowance is exhausted; Cloudinary usage is limited by monthly credits. Monitor both and stop uploads/requests before exceeding the free allowance. Do not add a payment method or upgrade.
- Payment and SMS/OTP integrations are simulated. No real funds are collected and no SMS is delivered.
- No live bank integration, Tally, CCTV, boom barrier, WhatsApp or external payment gateway is included.
- A PWA cannot run local cleanup while closed/offline. Scheduled server-side cleanup runs when GitHub Actions successfully calls the endpoint; it still needs monitoring.
- This package does not claim production readiness, legal compliance certification, a real SMS provider or measured load capacity.


## 11. Free-tier source links (checked 9 November 2026)

- Render Free service limits, idle sleep, ephemeral filesystem and the 30-day expiry of Render Free Postgres: <https://render.com/docs/free>. This deployment deliberately uses Neon instead of Render Postgres because Render Free Postgres expires 30 days after creation.
- Neon Free plan limits: <https://neon.com/pricing> and <https://neon.com/blog/neon-free-plan-1-gb-per-project>. Use the live Neon console as the authoritative quota for the account.
- Cloudinary Free plan and no-credit-card signup: <https://cloudinary.com/pricing> and <https://cloudinary.com/documentation/billing_and_plans>.
- Cloudinary authenticated asset access and signed delivery: <https://cloudinary.com/documentation/control_access_to_media> and <https://cloudinary.com/documentation/image_upload_api_reference>.
- GitHub Actions public-repository minute policy: <https://github.com/pricing>.
- Groq rate limits and billing tiers (optional only): <https://console.groq.com/docs/rate-limits> and <https://console.groq.com/docs/billing-faqs>. Stay on the Free tier; Developer is usage-billed.

The provider webpages are mutable. The free-tier values above are a checked snapshot, not a price lock or an account-specific promise.
