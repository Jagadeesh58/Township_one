# PostgreSQL Validation Status

PostgreSQL is not installed or running in the current execution environment. Docker and PostgreSQL server utilities are unavailable, so the PostgreSQL-specific tests could not be executed here.

The backend suite was executed against SQLite with foreign-key enforcement enabled:

```text
199 passed, 3 skipped, 22 warnings (all executed assertions passed; coverage report did not finalize in this environment)
```

The three skipped tests require PostgreSQL row locks:

- `tests/test_payment_concurrency.py:189`
- `tests/test_payment_concurrency.py:260`
- `tests/test_payments.py:427`

The emergency classifier actor field is now `VARCHAR(50)` in the SQLAlchemy model and has a forward Alembic migration. The migration test asserts the declared column length is 50. This addresses the known truncation defect at the model/schema level, but PostgreSQL execution is still required to prove the deployed dialect behaviour.

Test fixtures now delete dependent payment and bill records before their parents. SQLite foreign-key enforcement is enabled in the test engine, and the full SQLite suite passes with those constraints enabled.

Before relying on PostgreSQL payment concurrency or claiming the PostgreSQL test job is green, run the CI PostgreSQL service job and verify that all three row-lock tests execute (not skip) and pass.

## Cross-dialect defects addressed in the source

- The deterministic emergency classifier actor identifier is 21 characters. `classification_decisions.actor_type` was widened from `VARCHAR(20)` to `VARCHAR(50)` through a forward Alembic migration. The emergency complaint test asserts the stored identifier.
- The bank reconciliation fixture now removes dependent postings, rows, receipts, idempotency records, ledger entries and bill lines before deleting their parent payment/bill/import records.
- The bill-operation fixture removes bill lines before the bill.
- SQLite test connections now enable `PRAGMA foreign_keys=ON`, so the same declared foreign-key relationships are enforced during the local suite.

These changes address the reported schema-length and test-cleanup causes at source level. They are not a substitute for running the PostgreSQL service job: the three row-lock tests remain unverified in this environment.
