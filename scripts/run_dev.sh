#!/bin/bash
# ============================================================
# run_dev.sh — Start development server with hot reload
# Requires: .venv activated or Python available in PATH
# ============================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env if it exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

echo "==> Starting development server (uvicorn --reload)..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level "${LOG_LEVEL:-debug}"
