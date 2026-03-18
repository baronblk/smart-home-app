#!/bin/bash
# ============================================================
# db_reset.sh — Drop, recreate, migrate, and seed the database
# WARNING: This destroys all data. Use for development only.
# ============================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

echo "==> WARNING: This will DROP and RECREATE the database."
read -r -p "    Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "==> Aborted."
    exit 0
fi

echo "==> Dropping and recreating database: ${POSTGRES_DB}..."
docker-compose exec db psql -U "${POSTGRES_USER}" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker-compose exec db psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${POSTGRES_DB};"
docker-compose exec db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /docker-entrypoint-initdb.d/init.sql

echo "==> Running Alembic migrations..."
docker-compose exec app alembic upgrade head

echo "==> Running seed scripts..."
docker-compose exec app python seeds/run_seeds.py

echo "==> Database reset complete."
