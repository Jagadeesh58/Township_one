# Payment Safety and Precision Test Evidence

## Executed local test command

```bash
TOWNSHIP_ENV=test pytest tests/test_payments.py tests/test_payment_concurrency.py tests/test_money_precision.py -rs -q
```

Observed result in this checkout:

```text
17 passed, 3 skipped, 6 warnings in 1.95s
```

The three skipped tests require PostgreSQL row locks:

- `tests/test_payments.py:427`
- `tests/test_payment_concurrency.py:189`
- `tests/test_payment_concurrency.py:260`

The skipped tests are not counted as passing concurrency evidence. Run the same test files with `PG_DATABASE_URL` and `TEST_DATABASE_URL` pointing to a disposable PostgreSQL test database before relying on concurrent allocation behaviour.

## Covered behaviours

The executed SQLite tests cover request validation, idempotency behaviour, payment outcome handling and Decimal precision. The PostgreSQL-only row-lock tests cover concurrency scenarios but were not executed in this environment.

## Boundaries

- Payments are simulated; no real funds are transferred.
- SQLite does not establish PostgreSQL row-lock behaviour.
- The report does not claim measured production throughput or load-test results.
