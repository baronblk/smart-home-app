#!/bin/bash
# ============================================================
# run_tests.sh — Run full test suite with coverage report
# ============================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Running tests with coverage..."
pytest \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    "$@"

echo ""
echo "==> Coverage report written to htmlcov/index.html"
