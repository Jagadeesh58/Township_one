"""
Township One — Database Engine & Connection Pool Configuration.

Provides thread-safe connection pooling, transaction lifecycle management,
and session dependency factories for SQLite and PostgreSQL engines.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings


def get_engine(custom_url: str = None):
    url = custom_url
    if not url:
        is_test = os.environ.get("TOWNSHIP_ENV") == "test"
        url = settings.TEST_DATABASE_URL if is_test else settings.DATABASE_URL

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True
    )


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
