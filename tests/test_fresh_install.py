"""
Township One - Fresh Database Installation and Seed Ground-Truth Verification.

Validates the full lifecycle on a clean database:
1. Executes Alembic migrations to head.
2. Asserts zero schema drift via Alembic autogenerate check.
3. Executes canonical seed command.
4. Asserts exact township entity counts (28 towers, 2,400 flats, 180 staff, 4 gates).
5. Asserts the 3 ground-truth flat balances and overdue math against DEMO_AS_OF_DATE:
   - T07-1203: Paid in full (balance 0.00).
   - T12-0408: Unpaid (balance 6,370.00, 47 days overdue as of 2026-11-06).
   - T21-1601: Partially paid (balance 5,660.00, 18 days overdue as of 2026-11-06).
"""

import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models.entities import Bill, Flat, Gate, StaffMember, Tower
from seed.seed_data import seed_database


def test_fresh_database_migration_seed_and_ground_truth_invariants():
    """Verify fresh install from scratch: migrations + seed + ground-truth balances."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite:///{db_path.replace(os.sep, '/')}"
    old_env = os.environ.get("DATABASE_URL")
    engine = None

    try:
        os.environ["DATABASE_URL"] = db_url

        # 1. Run migrations to head
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")

        # 2. Assert zero schema drift
        command.check(alembic_cfg)

        # 3. Seed twice to prove the single safe command is idempotent.
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        seed_database(target_engine=engine, mode="safe")
        seed_database(target_engine=engine, mode="safe")

        # 4. Assert township entity counts remain unchanged.
        with Session(engine) as session:
            towers_count = len(session.scalars(select(Tower.id)).all())
            flats_count = len(session.scalars(select(Flat.id)).all())
            staff_count = len(session.scalars(select(StaffMember.id)).all())
            gates_count = len(session.scalars(select(Gate.id)).all())

            assert towers_count == 28, f"Expected 28 towers, found {towers_count}"
            assert flats_count == 2400, f"Expected 2,400 flats, found {flats_count}"
            assert staff_count == 180, f"Expected 180 staff members, found {staff_count}"
            assert gates_count == 4, f"Expected 4 gates, found {gates_count}"

            # 5. Assert ground-truth balances and overdue calculations
            # Flat 1: T07-1203 (Paid in full)
            flat1 = session.scalar(select(Flat).where(Flat.flat_number == "T07-1203"))
            assert flat1 is not None
            bill1 = session.scalar(select(Bill).where(Bill.flat_id == flat1.id))
            assert bill1 is not None
            assert bill1.principal_amount == Decimal("7475.00")
            assert bill1.paid_amount == Decimal("7475.00")
            assert bill1.balance_amount == Decimal("0.00")
            assert bill1.status == "PAID"

            # Flat 2: T12-0408 (Unpaid, exactly 47 days overdue as of 2026-11-06)
            flat2 = session.scalar(select(Flat).where(Flat.flat_number == "T12-0408"))
            assert flat2 is not None
            bill2 = session.scalar(select(Bill).where(Bill.flat_id == flat2.id))
            assert bill2 is not None
            assert bill2.principal_amount == Decimal("6370.00")
            assert bill2.paid_amount == Decimal("0.00")
            assert bill2.balance_amount == Decimal("6370.00")
            assert bill2.status == "OVERDUE"
            assert bill2.due_date.strftime("%Y-%m-%d") == "2026-09-20"
            overdue_days_flat2 = (datetime(2026, 11, 6) - bill2.due_date.replace(tzinfo=None)).days
            assert overdue_days_flat2 == 47

            # Flat 3: T21-1601 (Partially paid ₹5,000, balance ₹5,660, 18 days overdue)
            flat3 = session.scalar(select(Flat).where(Flat.flat_number == "T21-1601"))
            assert flat3 is not None
            bill3 = session.scalar(select(Bill).where(Bill.flat_id == flat3.id))
            assert bill3 is not None
            assert bill3.principal_amount == Decimal("10660.00")
            assert bill3.paid_amount == Decimal("5000.00")
            assert bill3.balance_amount == Decimal("5660.00")
            assert bill3.status == "PARTIALLY_PAID"
            assert bill3.due_date.strftime("%Y-%m-%d") == "2026-10-19"
            overdue_days_flat3 = (datetime(2026, 11, 6) - bill3.due_date.replace(tzinfo=None)).days
            assert overdue_days_flat3 == 18

            # The release runner consumes this measured record only when this
            # test passes; it does not duplicate seed logic or hard-code results.
            report_path = os.environ.get("TOWNSHIP_RELEASE_REPORT_PATH")
            if report_path:
                Path(report_path).write_text(
                    json.dumps(
                        {
                            "counts": {
                                "towers": towers_count,
                                "flats": flats_count,
                                "staff": staff_count,
                                "gates": gates_count,
                            },
                            "ground_truth": {
                                "T07-1203": {"outstanding": f"{bill1.balance_amount:.2f}", "overdue_days": 0},
                                "T12-0408": {
                                    "outstanding": f"{bill2.balance_amount:.2f}",
                                    "overdue_days": overdue_days_flat2,
                                },
                                "T21-1601": {
                                    "outstanding": f"{bill3.balance_amount:.2f}",
                                    "overdue_days": overdue_days_flat3,
                                },
                            },
                            "seed_runs": 2,
                            "migration": "alembic upgrade head",
                            "schema_parity": "alembic check reported no new upgrade operations",
                        },
                        sort_keys=True,
                    ),
                    encoding="utf-8",
                )

    finally:
        if engine is not None:
            engine.dispose()
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
