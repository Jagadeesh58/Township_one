# Testing and Validation

Use the exact output from commands in `docs/reports/summary.json`. Do not type test counts or coverage values into this document.

## Backend tests

```bash
python -m pytest -rs
```

For coverage:

```bash
python -m pytest -rs --cov=backend/app --cov-report=term --cov-fail-under=90
```

The SQLite suite exercises application behaviour and portable database constraints. Tests requiring PostgreSQL locking must be run with `PG_DATABASE_URL` and `TEST_DATABASE_URL` configured for a disposable PostgreSQL database.

## Migration and seed checks

```bash
alembic upgrade head
alembic check
python -m seed.seed_data --mode safe
python -m seed.seed_data --mode safe
```

The seed command must be repeatable. It must preserve the 28-tower, 2,400-flat, 180-staff and four-gate reference counts and the three published balance examples.

## Frontend checks

Node must satisfy the package-lock engine requirement (Node 22.22.2 or later in the Node 22 line, or Node 24.15 or later).

```bash
cd frontend
npm ci
npx tsc --noEmit
npm test
npm run build
```

The IndexedDB queue tests use `fake-indexeddb`. A browser-level test should additionally exercise real reload, offline capture, reconnect upload and acknowledgement behaviour before claiming browser verification.

## Bank reconciliation tests

`tests/test_bank_matching.py` uses synthetic transaction fixtures to exercise exact evidence, ambiguity, duplicates and review routing. PostgreSQL uniqueness and concurrency assertions require a PostgreSQL test database.

## Release verifier

```bash
python scripts/verify_release.py
```

The verifier writes `docs/reports/summary.json`. A missing executable, failing command or timeout is recorded as a non-passing status and causes a non-zero exit code.

## Evidence boundaries

- A test file proves only the assertions that it executes.
- SQLite does not prove PostgreSQL row-level lock behaviour.
- TypeScript compilation does not prove browser interaction.
- A locally scheduled command does not prove a hosted scheduler is deployed.
- A screenshot does not prove that a backend action or external integration succeeded.
