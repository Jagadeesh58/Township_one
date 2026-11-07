# TOWNSHIP ONE — PRODUCTION DEPLOYMENT & OPERATIONS GUIDE

**Repository URL:** https://github.com/Jagadeesh58/Township_one.git  

---

## 1. System Architecture Overview

**Township One** is an enterprise-grade reliability runtime and resident portal designed for large residential communities (modeled on Company A, Pune: 2,400 flats, 28 towers, 180 staff, 4 access gates).

- **Backend Runtime:** Python 3.11+ ASGI application using FastAPI, SQLAlchemy 2.0 ORM, and Alembic database migrations.
- **Frontend Client:** React 19 + TypeScript + Vite Progressive Web Application (PWA) with multilingual i18n (English, Marathi, Hindi) and offline cache capabilities.
- **Database Architecture:**
  - Local Development & Testing: SQLite with WAL mode.
  - Production Deployment: PostgreSQL 15+ via high-performance `psycopg` (v3) with connection pooling and `SELECT ... FOR UPDATE` row-level concurrency locking.
- **Security & Authorization:** Salted SHA-256 OTP challenges with database persistence, HttpOnly SameSite=Lax session cookies, double-submit CSRF protection, PyJWT access tokens, server-side RBAC, and persistent token revocation via `revoked_tokens`.

---

## 2. Prerequisites & System Requirements

- **Python:** 3.11.0 or higher
- **Node.js:** v20.x or higher (LTS recommended), npm v10+
- **Database:** PostgreSQL 15+ (Production standard) or SQLite 3.35+ (Development fallback)
- **Memory & Storage:** 2 GB RAM minimum, 10 GB disk space

---

## 3. Environment Configuration (`.env`)

Configure environment variables via host environment or a secure `.env` file:

```bash
# Application Identity & Mode
APP_NAME=Township One
APP_ENV=production                # Options: development, staging, production
DEBUG=false                       # MUST be false in production

# Network & Server
PORT=8000
API_PREFIX=/api/v1
ALLOWED_ORIGINS=<set-in-host-env>

# Cryptographic Keys (MUST be strong high-entropy key >= 32 characters in production)
SECRET_KEY=<set-in-host-env>
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database URLs
DATABASE_URL=<set-in-host-env>
TEST_DATABASE_URL=<set-in-host-env>

# SMS Gateway Credentials (Required in production; system fails closed if omitted)
SMS_PROVIDER_API_KEY=<set-in-host-env>
OTP_EXPIRY_SECONDS=300

# Canonical Reference Snapshot Date
DEMO_AS_OF_DATE=2026-11-06T00:00:00Z

# Maintenance Billing Parameters
MAINTENANCE_RATE_PER_SQFT=6.50
DEFAULT_GRACE_PERIOD_DAYS=5
DEMO_LATE_FEE_PERCENTAGE_PA=18.00
```

---

## 4. Production Installation & Setup Steps

### Step 1: Clone and Prepare Python Environment
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\Activate.ps1

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Apply Database Migrations
```bash
alembic upgrade head
```

### Step 3: Seed Synthetic Reference Data (Optional for Demo / Staging)
```bash
# Safe mode: validates completeness or seeds fresh local DB without touching remote DBs
python scripts/seed.py --mode safe

# Reset demo mode (strictly local databases only; fails closed on remote hosts):
# python scripts/seed.py --mode reset-demo --confirm-local-demo
```

### Step 4: Build Frontend Assets
```bash
cd frontend
npm ci
npm test
npm run build
cd ..
```
Compiled production bundles are emitted to `frontend/dist/`.

---

## 5. Running the Application

### Running with Uvicorn (Development / Testing)
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running with Gunicorn / Multi-Worker Uvicorn (Production)
```bash
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/township-one/access.log \
  --error-logfile /var/log/township-one/error.log \
  --capture-output
```

---

## 6. Reverse Proxy Configuration (Nginx Example)

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

    # Frontend Single Page App & PWA
    root /var/www/township-one/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Endpoints Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Service Worker caching policy
    location = /sw.js {
        add_header Cache-Control "no-cache";
        expires 0;
    }
}
```

---

## 7. Health Checks & Monitoring

The backend exposes dedicated operational health probes:

- **Liveness Probe:** `GET /health` — Returns application status and version.
- **Readiness Probe:** `GET /health/ready` — Verifies live database connectivity and query response time.

```bash
curl -f http://localhost:8000/health
# Expected: {"status":"healthy","service":"township-one","version":"1.0.0"}

curl -f http://localhost:8000/health/ready
# Expected: {"status":"ready","database":"connected","response_time_ms":1.2}
```

---

## 8. Automated Verification

Before deploying any release, run the complete automated test suite:

```bash
# 1. Run Backend Pytest Suite
pytest tests/ -v

# 2. Run Frontend Vitest Suite
cd frontend
npm test

# 3. Verify Production Frontend Build
npm run build
```
