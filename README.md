# Township One — Gated Township Resident & Operations Platform

**Client:** Company A, Pune  
**Township Context:** 2,400 apartments across 28 towers, 180 on-site staff, 4 gates, managing ₹22–26 crore annual maintenance budget.  
**Scope Authority:** Challenge Brief Part C: Brief 2 (Gated township's resident app for maintenance, complaints and visitors).

---

## Architecture Overview

Township One is structured as a robust, mobile-first PWA backed by a high-performance RESTful API:
- **Frontend:** React + TypeScript + Vite (Installable PWA with offline capabilities, trilingual support for English, Marathi, Hindi).
- **Backend:** FastAPI + SQLAlchemy + Pydantic (Modular, stateless, server-side authorization).
- **Database:** PostgreSQL in production / SQLite for zero-setup local development, with strict schema constraints and `NUMERIC(14,2)` currency precision.
- **Security:** Session-based / HttpOnly bearer auth, IDOR protection, cross-flat access denial, strict data minimization under DPDP Act 2023.

---

## Project Structure

```text
Township_one/
├── backend/            # FastAPI backend service
│   └── app/
│       ├── api/        # REST endpoints (health, auth, billing, complaints, etc.)
│       ├── core/       # Config, database engine, security primitives
│       ├── models/     # SQLAlchemy database entities
│       ├── schemas/    # Pydantic request/response validation schemas
│       └── services/   # Business logic (billing rules, payments, ledger)
├── frontend/           # React + TypeScript + Vite mobile-first PWA
│   └── src/
│       ├── api/        # Typed API clients
│       ├── components/ # Reusable UI components
│       ├── i18n/       # Trilingual strings (EN, MR, HI)
│       └── pages/      # Resident home, billing, complaints, helpdesk
├── seed/               # Deterministic seed generator for 28 towers & 2,400 flats
├── tests/              # Automated unit, integration, and security test suite
├── docs/               # Traceability matrix, screen map, and assumptions register
└── .env.example        # Configuration template (no secrets committed)
```

---

## Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Run backend directly with uvicorn
py -3.11 -m uvicorn backend.app.main:app --reload --port 8000
```
Backend runs at `http://localhost:8000` (Swagger docs at `/docs`).

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

### 3. Run Automated Tests
```bash
py -3.11 -m pytest tests/ -v
```
