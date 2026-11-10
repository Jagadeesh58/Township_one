#!/bin/sh
set -eu

# Apply only forward Alembic migrations. Never drop or recreate a hosted database.
alembic upgrade head

# The remote seed path is doubly opt-in and safe-mode only. It refuses partial datasets.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  if [ "${ALLOW_REMOTE_DEMO_SEED:-false}" = "true" ]; then
    python -m seed.seed_data --mode safe --allow-remote-demo-seed
  else
    python -m seed.seed_data --mode safe
  fi
fi

exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
