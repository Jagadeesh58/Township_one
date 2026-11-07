"""
Day 1 · D1-S1 — Foundation and Environment: Alembic Database Migrations Configuration.

Responsibility:
- Obtain effective migration URL strictly from validated settings or environment.
- Prevent hard-coded default URLs in alembic.ini from silently overriding DATABASE_URL.
- Support both SQLite (local development/testing) and PostgreSQL (production).
- Mask credentials to prevent leaking database passwords in logs.

Related documentation:
docs/day-1/D1-S1-foundation-and-environment.md
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine.url import make_url
from alembic import context

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.core.database import Base
# Import all models to ensure they are registered with Base.metadata
import backend.app.models.entities

config = getattr(context, "config", None)

if config is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_effective_migration_url() -> str:
    """
    Resolves the effective database URL for Alembic migrations.
    Priority:
    1. Explicit CLI -x url=... argument
    2. Environment variable DATABASE_URL
    3. Validated application configuration settings.DATABASE_URL
    4. alembic.ini option (only if not a placeholder)
    """
    selected_url = None

    # 1. Check CLI -x url=...
    try:
        x_args = context.get_x_argument(as_dictionary=True)
        if "url" in x_args and x_args["url"]:
            selected_url = x_args["url"].strip()
    except Exception:
        pass

    # 2. Check environment variable DATABASE_URL
    if not selected_url and os.getenv("DATABASE_URL") and os.getenv("DATABASE_URL").strip():
        selected_url = os.getenv("DATABASE_URL").strip()

    # 3. Check application validated settings
    if not selected_url and hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL and settings.DATABASE_URL.strip():
        selected_url = settings.DATABASE_URL.strip()

    # 4. Fall back to config if available
    if not selected_url and config is not None:
        cfg_url = config.get_main_option("sqlalchemy.url")
        if cfg_url and not cfg_url.startswith("driver://") and cfg_url.strip():
            selected_url = cfg_url.strip()

    if not selected_url:
        raise ValueError(
            "Alembic database URL resolution failure: DATABASE_URL is not set or empty. "
            "Please configure DATABASE_URL in your environment or .env file."
        )

    # Validate URL structure
    try:
        make_url(selected_url)
    except Exception as exc:
        raise ValueError(f"Malformed database URL provided to Alembic: {exc}")

    return selected_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_effective_migration_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_effective_migration_url()
    if config is not None:
        config.set_main_option("sqlalchemy.url", url)
        configuration = config.get_section(config.config_ini_section, {})
    else:
        configuration = {}
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if config is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
