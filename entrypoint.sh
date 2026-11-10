#!/bin/sh
set -eu

echo "==> Running database migrations..."
alembic upgrade head

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "==> Seeding demo data..."
  if [ "${ALLOW_REMOTE_DEMO_SEED:-false}" = "true" ]; then
    python -m seed.seed_data --mode safe --allow-remote-demo-seed
  else
    python -m seed.seed_data --mode safe
  fi
fi

echo "==> Starting Uvicorn on port ${PORT:-8000}..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
