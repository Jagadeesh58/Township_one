# TOWNSHIP ONE — DEPLOYMENT & OPERATIONS GUIDE

**Repository URL:** https://github.com/Jagadeesh58/Township_one.git

---

## 1. System Architecture Overview

**Township One** is an integrated resident portal and community operations system engineered for large residential communities (modeled on a reference community with 2,400 flats, 28 towers, 180 staff members, and 4 gates in Pune).

- **Backend:** FastAPI (Python 3.11+), SQLAlchemy 2.0 ORM, and Alembic database migrations.
- **Frontend:** React 19 + TypeScript + Vite Progressive Web Application (PWA) with multilingual localization (English, Marathi, Hindi) and offline cache capabilities.
- **Database:** PostgreSQL 15+ (production via `psycopg` v3 with row-level `SELECT ... FOR UPDATE` locking) or SQLite (local development and test suite).
- **Authentication:** Passwordless phone OTP with salted SHA-256 challenge records, HttpOnly SameSite=Lax session cookies, and double-submit CSRF protection.
- **Visitor Gate Management:** Cryptographic ECDSA P-256 offline token verification, visitor photo storage with Pillow EXIF stripping, signed streaming, and 90-day retention purging.
- **Amenity Management:** Slot booking with capacity reservation, idempotency enforcement, flat daily booking limits, and closure management.
- **Community Notices:** Append-only revision tracking, tower scoping, and trilingual language fallback ("Shown in English").
- **Committee Governance:** Dues ageing breakdown (0-30, 31-60, 61-90, 90+ days), complaint turnaround metrics, ReportLab PDF and CSV aggregate exports.
- **AI / Classification:** Groq API client with local scikit-learn TF-IDF + MultinomialNB offline fallback trained on multilingual data.

---

## 2. Environment Variables

The application is configured using the following environment variable names (set in the host environment or a secure `.env` file; no secret values are committed to git):

- `APP_NAME`: Application display name.
- `APP_ENV`: Deployment environment (`development`, `staging`, or `production`).
- `DEBUG`: Boolean flag (`true` or `false`). Set to `false` in production.
- `PORT`: HTTP server listen port.
- `API_PREFIX`: REST API root route prefix (e.g. `/api/v1`).
- `ALLOWED_ORIGINS`: Comma-separated or JSON list of permitted CORS origins.
- `SECRET_KEY`: High-entropy cryptographic secret (minimum 32 characters) for signing session cookies and HMAC tokens.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Session token expiration duration in minutes.
- `DATABASE_URL`: Primary database connection string (PostgreSQL in production, SQLite in local development).
- `TEST_DATABASE_URL`: Test database connection string.
- `DEMO_AS_OF_DATE`: Reference timestamp used for demo calculations and interest accruals.
- `SMS_PROVIDER_API_KEY`: API key for SMS gateway provider (in production; development logs OTP to console).
- `OTP_EXPIRY_SECONDS`: Lifespan of generated OTP challenges in seconds.
- `MAINTENANCE_RATE_PER_SQFT`: Monthly maintenance charge rate per square foot.
- `DEFAULT_GRACE_PERIOD_DAYS`: Number of grace period days following billing due date before interest accrues.
- `DEMO_LATE_FEE_PERCENTAGE_PA`: Annualized simple interest rate percentage for overdue balances.
- `GROQ_API_KEY`: API key for Groq LLM service (optional; offline local model fallback is used if omitted or unavailable).
- `GROQ_MODEL_ID`: Model identifier for Groq API (e.g. `llama-3.3-70b-versatile`).
- `STORAGE_DIR`: Filesystem path to secure directory for private photo attachments.

---

## 3. Local Run Steps

### 1. Prerequisites
- Python 3.11+
- Node.js v20+ and npm v10+
- Git

### 2. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\Activate.ps1

# Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed synthetic reference data (28 towers, 2,400 flats, 180 staff, 4 gates)
python -m seed.seed_data

# Start backend development server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd frontend

# Install frontend dependencies
npm ci

# Run frontend tests
npm test

# Build frontend bundle
npm run build

# Start frontend development server
npm run dev
```

---

## 4. How It Is Deployed (Production Architecture)

### 1. Database Tier (PostgreSQL 15+)
- Provision PostgreSQL 15+ instance with connection pooling.
- Execute migrations using Alembic:
  ```bash
  alembic upgrade head
  ```
- Ensure row-level locking (`SELECT ... FOR UPDATE`) is permitted on the database user.

### 2. Backend Service (FastAPI via Gunicorn / Uvicorn)
- Run the ASGI application with multi-worker process management:
  ```bash
  gunicorn backend.app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/township-one/access.log \
    --error-logfile /var/log/township-one/error.log
  ```
- Protect application startup with checks (valid `SECRET_KEY`, `APP_ENV=production`, `DEBUG=false`).

### 3. Periodic Background Jobs (Cron)
- Configure automated visitor photo 90-day retention purge daily:
  ```bash
  0 2 * * * /path/to/venv/bin/python -m backend.app.jobs.purge_visitor_photos >> /var/log/township-one/photo-purge.log 2>&1
  ```

### 4. Frontend Static Hosting & Reverse Proxy (Nginx)
- Build the frontend bundle: `npm run build` in `frontend/`.
- Serve static files from `frontend/dist/`.
- Route `/api/` traffic to the backend ASGI server.
- Sample Nginx configuration:
```nginx
server {
    listen 80;
    server_name township.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name township.example.com;

    ssl_certificate /etc/letsencrypt/live/township.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/township.example.com/privkey.pem;

    root /var/www/township-one/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /sw.js {
        add_header Cache-Control "no-cache";
        expires 0;
    }
}
```

### 5. Health Probes & Monitoring
- **Liveness:** `GET /health` — Verifies application process is running.
- **Readiness:** `GET /health/ready` — Verifies database connection and query response.

---

## 5. Reviewer Personas & Demo Logins (Reference Date: `2026-11-06`)

| Persona | Phone | Demo OTP | Role / Flat | State |
|---|---|---|---|---|
| **Neeraj Kulkarni** | `9876543210` | `123456` | Owner, Flat T07-1203 | 1,150 sq ft, settled dues (₹7,475.00 paid), ₹0.00 outstanding |
| **Swati Joshi** | `9876543211` | `123456` | Tenant, Flat T12-0408 | 980 sq ft, 47 days overdue (due 2026-09-20), ₹6,370.00 outstanding |
| **Aamir Shaikh** | `9876543212` | `123456` | Owner, Flat T21-1601 | 1,640 sq ft, 18 days overdue (due 2026-10-19), ₹5,660.00 outstanding |
| **Ananya Kulkarni** | `9876543213` | `123456` | Family Member, Flat T07-1203 | Can view dues summary, cannot execute payments |
| **Priya Sharma** | `9876543214` | `123456` | Owner, Flat T03-0201 | 1,150 sq ft, routine maintenance account |
| **Ramesh Patil** | `9876543220` | `123456` | Help Desk Staff | Authorized for complaints queue, triage, and incident linking |
| **Suresh Shinde** | `9876543230` | `123456` | Security Guard | Gate access, visitor arrivals, gate admissions, offline sync, guest pass checks |
| **Anita Deshmukh** | `9876543240` | `123456` | Accounts Staff | Authorized for bank statement imports, review queue, and ledger posting |
| **Vikram Sardesai** | `9876543250` | `123456` | Committee Member | Authorized for aggregate governance dashboard, dues ageing, SLA metrics, PDF/CSV report exports |
| **System Admin** | `9876543200` | `123456` | Administrator | Full administrative authority across all modules |
