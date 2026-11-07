# Alembic Database Migration Validation Report

**Migration Engine:** Alembic 1.14.1  
**Target Dialects:** SQLite (development / test) & PostgreSQL (production)  
**Latest Revision:** `c0c7c862d0b3` (`initial_schema_v1`)  
**Test Suite:** `tests/test_migrations.py` (100% Passed)  

---

## 1. Dynamic Migration URL Resolution

The migration configuration in `migrations/env.py` resolves the target database URL dynamically using strict priority rules:
1. CLI parameter `-x url=<custom_url>`
2. Environment variable `DATABASE_URL`
3. Programmatic configuration (`config.get_main_option("sqlalchemy.url")`) when set to a valid non-placeholder URL
4. Application configuration (`settings.DATABASE_URL`)

Placeholder defaults in `alembic.ini` (e.g., `driver://user:pass@localhost/dbname`) are explicitly ignored, preventing hard-coded fallback corruption.

---

## 2. Fresh Database Migration Verification

The automated test `test_alembic_upgrade_head_on_fresh_database` validates:
1. Creation of a fresh, isolated temporary SQLite database file.
2. Invocation of `alembic.command.upgrade(alembic_cfg, "head")`.
3. Validation that `alembic_version` is stamped with revision `c0c7c862d0b3`.
4. Execution of `command.current` and `command.heads` confirming zero revision drift.
5. Introspection of all schema tables, columns, indexes, and unique constraints.

---

## 3. Verified Schema Entities

Introspection confirms all 19 schema tables are generated with exact column types, foreign keys, and indexes:
- `towers` (indexed code)
- `flats` (indexed flat_number, FK tower_id)
- `users` (indexed phone)
- `flat_memberships` (FK flat_id, FK user_id)
- `user_role_assignments` (FK user_id)
- `staff_members` (unique staff_code, FK user_id)
- `gates` (unique gate_number)
- `billing_rules`
- `bills` (composite unique flat_id + period_month + period_year, FK flat_id, FK billing_rule_id)
- `bill_lines` (FK bill_id)
- `payments` (unique transaction_reference, unique receipt_number, indexed idempotency_key, FK bill_id, FK flat_id, FK payer_user_id)
- `payment_idempotency_records` (unique idempotency_key, FK bill_id, FK flat_id, FK user_id, FK payment_id)
- `flat_ledger_entries` (FK flat_id)
- `receipts` (unique receipt_number, FK payment_id)
- `complaints` (unique ticket_number, FK flat_id, FK user_id, FK assigned_staff_id, FK duplicate_of_id)
- `amenities`
- `notices` (FK target_tower_id)
- `visitors` (FK gate_id, FK flat_id, FK approved_by_user_id)
- `alembic_version`
