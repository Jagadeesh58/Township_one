# Database and Seed Data

## Database configuration

PostgreSQL is the intended shared database. SQLite is used for selected local tests. Configure `DATABASE_URL` and `TEST_DATABASE_URL` before running Alembic or tests.

The included Compose service starts a local PostgreSQL 15 instance with development credentials. Change all defaults before using an externally reachable database.

## Migrations

Run migrations from the repository root:

```bash
alembic upgrade head
alembic check
```

The migration chain includes the gate-device registry and visitor photo identity fields used by offline synchronization. Review the migration chain before applying it to any database containing important data.

## One seed entry point

Use only:

```bash
python -m seed.seed_data --mode safe
```

Safe mode is intended to be idempotent. Re-running it must not increase the reference counts or duplicate records.

For a disposable local demo database only:

```bash
python -m seed.seed_data --mode reset-demo --confirm-local-demo
```

Do not run reset mode against a shared or production database.

## Reference dataset

- 28 towers.
- 2,400 flats.
- 180 staff members.
- Four gates.
- Synthetic owners, tenants, family members and staff.
- Sample billing snapshot dated `2026-11-06`.
- Synthetic payment and bank rows.
- Complaint, visitor, notice and amenity demonstration records.

## Financial examples

| Flat | Principal | Paid | Outstanding | Overdue |
|---|---:|---:|---:|---:|
| T07-1203 | ₹7,475.00 | ₹7,475.00 | ₹0.00 | 0 days |
| T12-0408 | ₹6,370.00 | ₹0.00 | ₹6,370.00 | 47 days |
| T21-1601 | ₹10,660.00 | ₹5,000.00 | ₹5,660.00 | 18 days |

The principal uses the supplied rate of ₹6.50 per square foot per month. Late fees and grace-period values are demo assumptions pending society approval.
