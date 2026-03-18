#!/bin/bash
# ============================================================
# smart-home-app — Container entrypoint
# Runs database migrations before starting the application.
# If migrations fail, the container exits with non-zero status
# to prevent the app from starting against a broken schema.
# ============================================================
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}"
