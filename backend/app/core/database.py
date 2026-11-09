"""
Township One — Database Engine & Connection Pool Configuration.

Provides thread-safe connection pooling, transaction lifecycle management,
and session dependency factories for SQLite and PostgreSQL engines.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


def get_engine(custom_url: str | None = None):
    url = custom_url
    if not url:
        is_test = os.environ.get("TOWNSHIP_ENV") == "test"
        url = settings.TEST_DATABASE_URL if is_test else settings.DATABASE_URL

    # If default PostgreSQL URL is configured but not reachable on localhost during dev, fall back to SQLite
    if url.startswith("postgresql") and not os.environ.get("DATABASE_URL") and not os.environ.get("TEST_DATABASE_URL"):
        try:
            temp_eng = create_engine(url, connect_args={"connect_timeout": 1}, pool_pre_ping=True)
            with temp_eng.connect():
                pass
            temp_eng.dispose()
        except Exception:
            is_test = os.environ.get("TOWNSHIP_ENV") == "test"
            url = "sqlite:///./township_one_test.db" if is_test else "sqlite:///./township_one.db"

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
