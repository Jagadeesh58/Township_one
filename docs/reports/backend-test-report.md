# Backend Test Evidence

The latest backend run executed every collected test with the following command:

```bash
TOWNSHIP_ENV=test python -m pytest -q -rs -p no:ddtrace -p no:cov
```

Observed pytest summary:

```text
199 passed, 3 skipped, 22 warnings in 29.82s
```

All executed assertions passed. The three skipped tests require PostgreSQL row locks:

- `tests/test_payment_concurrency.py:189`
- `tests/test_payment_concurrency.py:260`
- `tests/test_payments.py:427`

The execution wrapper timed out while waiting for the pytest process to exit after it printed the complete summary. No test failure was reported, but a clean exit code still needs to be confirmed on CI or a normal local shell. Coverage collection also failed to finish shutdown in this environment, so no current coverage percentage is claimed. The prior 90.00% measurement was captured before the final Cloudinary adapter and its new tests and is intentionally not reused here.

The fresh-install database worker passed earlier in this build: migrations reached head, `alembic check` reported no schema drift, and safe seeding ran twice without duplicate records. The seeded dataset has 28 towers, 2,400 flats, 180 staff and four gates. PostgreSQL row-lock behaviour itself remains unverified until the PostgreSQL service job is run.

Full command outputs and individual gate states are recorded in `docs/reports/summary.json`. A blocked or skipped check is not described as a pass.
