# TOWNSHIP ONE — DEPLOYMENT & OPERATIONS GUIDE

**Repository URL:** https://github.com/Jagadeesh58/Township_one.git  

---

## 1. System Architecture
- **Backend:** FastAPI (Python 3.11+), SQLAlchemy 2.0 ORM, Alembic migrations.
- **Frontend:** React 19, TypeScript, Vite, Service Worker PWA.
- **Database:** SQLite (local dev/tests) or PostgreSQL 15+ (production via `psycopg`).
- **Storage:** Local or volume-mounted secure directory for private photo attachments.
- **AI / Classification:** Groq API client with local scikit-learn TF-IDF + MultinomialNB offline fallback.

---

## 2. Environment Variables (.env)
```bash
APP_NAME=Township One
APP_ENV=development # Set to "production" in production environments
DEBUG=True          # Set to False in production
PORT=8000
SECRET_KEY=<set-in-host-env>
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=postgresql+psycopg://township:CHANGE_ME@localhost:5432/township_one
TEST_DATABASE_URL=sqlite:///./township_one_test.db
DEMO_AS_OF_DATE=2026-11-06T00:00:00Z

# AI Classification (Groq API + Local Fallback)
GROQ_API_KEY=
GROQ_MODEL_ID=llama-3.3-70b-versatile

# Private Photo Storage
STORAGE_DIR=private_storage
```

---

## 3. Production Hardening Checklist
- [x] Set `APP_ENV=production` and `DEBUG=False`.
- [x] Configure strong 32+ character `SECRET_KEY`. The backend startup guard will hard-abort if a default/weak secret is used in production.
- [x] Verify database URL separation (`DATABASE_URL` vs `TEST_DATABASE_URL`).
- [x] Configure `STORAGE_DIR` pointing to a protected, non-public directory outside the web root.
- [x] Set optional `GROQ_API_KEY` for online AI classification (if omitted or rate-limited, system automatically uses trained local MultinomialNB fallback).
- [x] Run database migrations:
  ```bash
  alembic upgrade head
  ```
- [x] Build frontend assets:
  ```bash
  cd frontend
  npm ci
  npm run build
  ```
- [x] Serve backend via production ASGI server (Uvicorn / Gunicorn with Uvicorn workers).
