# Database Migration and Seed Evidence

## Executed fresh-database check

The release verifier creates a temporary SQLite database, runs `alembic upgrade head`, runs `alembic check`, executes the canonical safe seed twice and compares the resulting data with the reference snapshot.

Observed result from the most recent direct database-check worker:

```text
No new upgrade operations detected.
{"status": "PASS", "migration": "alembic upgrade head", "schema_parity": "alembic check reported no new upgrade operations", "seed_runs": 2, "counts": {"towers": 28, "flats": 2400, "staff": 180, "gates": 4}, "ground_truth": {"T07-1203": {"outstanding": "0.00", "overdue_days": 0}, "T12-0408": {"outstanding": "6370.00", "overdue_days": 47}, "T21-1601": {"outstanding": "5660.00", "overdue_days": 18}}}
```

The current head revision is the highest revision in `migrations/versions/`. The migration path above was verified on SQLite in this environment. PostgreSQL migration and constraint behaviour must also be checked by the PostgreSQL CI job or a local PostgreSQL run.

## Canonical seed command

```bash
python -m seed.seed_data --mode safe
```

The same command is used by the Makefile, README, deployment guide and release verifier. Safe mode preserves an already-consistent seeded database. The reset mode is for a disposable local demo database only.

## Scope of this evidence

This report records the SQLite migration and seed check only. It does not claim that PostgreSQL migration, row-lock behaviour or hosted deployment was exercised here.
