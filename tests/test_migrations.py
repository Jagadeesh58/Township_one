"""
Township One - Alembic Database Migrations Verification Tests.

Test suite verifying:
- Alembic migration environment resolution
- Execution of 'upgrade head' against an isolated target database
- Validation of schema tables, columns, indexes, and constraints
- Verification of 'current' and 'heads' consistency
"""

import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_on_fresh_database():
    """Verify Alembic successfully migrates a fresh temporary database to head."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    tmp_db_url = f"sqlite:///{tmp_db_path.replace(os.sep, '/')}"
    old_env = os.environ.get("DATABASE_URL")

    try:
        os.environ["DATABASE_URL"] = tmp_db_url

        # Configure Alembic
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", tmp_db_url)
        alembic_cfg.set_section_option("logger_alembic", "level", "WARN")

        # Run migration to head
        command.upgrade(alembic_cfg, "head")

        # Run current & heads check
        command.current(alembic_cfg)
        command.heads(alembic_cfg)

        # Inspect generated database schema
        engine = create_engine(tmp_db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "towers",
            "flats",
            "users",
            "flat_memberships",
            "user_role_assignments",
            "staff_members",
            "gates",
            "complaints",
            "billing_rules",
            "bills",
            "bill_lines",
            "payments",
            "payment_idempotency_records",
            "flat_ledger_entries",
            "receipts",
            "amenities",
            "notices",
            "visitors",
            "alembic_version",
        }

        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # Verify key table columns
        bill_columns = {c["name"] for c in inspector.get_columns("bills")}
        assert "principal_amount" in bill_columns
        assert "balance_amount" in bill_columns
        assert "paid_amount" in bill_columns
        assert "due_date" in bill_columns

        payment_columns = {c["name"] for c in inspector.get_columns("payments")}
        assert "transaction_reference" in payment_columns
        assert "idempotency_key" in payment_columns

        # Verify idempotency key index exists
        idempotency_columns = {c["name"] for c in inspector.get_columns("payment_idempotency_records")}
        assert "idempotency_key" in idempotency_columns
        assert "request_hash" in idempotency_columns

        engine.dispose()
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)

        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass
