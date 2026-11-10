import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, get_db
from backend.app.main import app
from seed.seed_data import seed_database

# STRICT DATABASE SEPARATION (Requirement 3.A)
# Ensure test database URL is completely separate from the application/demo database.
if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
    raise RuntimeError(
        f"FATAL SAFETY ABORT: TEST_DATABASE_URL ({settings.TEST_DATABASE_URL}) "
        f"cannot equal application DATABASE_URL ({settings.DATABASE_URL})! "
        "Refusing to run tests against the demo database."
    )

if "township_one.db" in settings.TEST_DATABASE_URL and not settings.TEST_DATABASE_URL.endswith("township_one_test.db"):
    raise RuntimeError(
        f"FATAL SAFETY ABORT: TEST_DATABASE_URL ({settings.TEST_DATABASE_URL}) "
        "cannot target the reviewer demo database 'township_one.db'."
    )

# Force test environment flag
os.environ["TOWNSHIP_ENV"] = "test"

# Dedicated Test Engine
test_db_url = settings.TEST_DATABASE_URL
if test_db_url.startswith("postgresql") and not os.environ.get("TEST_DATABASE_URL"):
    try:
        temp_engine = create_engine(test_db_url, connect_args={"connect_timeout": 1}, pool_pre_ping=True)
        with temp_engine.connect():
            pass
        temp_engine.dispose()
    except Exception:
        test_db_url = "sqlite:///./township_one_test.db"

test_engine = create_engine(
    test_db_url,
    connect_args={"check_same_thread": False} if test_db_url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

if test_db_url.startswith("sqlite"):
    @event.listens_for(test_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        """Make SQLite test runs enforce the same declared foreign keys as PostgreSQL."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Rebind global SessionLocal to test_engine during tests
SessionLocal.configure(bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Wire dependency override across all FastAPI routes during test runs
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def reset_test_db_per_module():
    """Seeds the test database before each test module to ensure clean isolation without touching demo db."""
    seed_database(target_engine=test_engine, mode="reset-demo", confirm_local_demo=True)


@pytest.fixture(autouse=True)
def isolate_test_state():
    from backend.app.core.security import REVOKED_TOKENS

    REVOKED_TOKENS.clear()
    yield
    REVOKED_TOKENS.clear()
