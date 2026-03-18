#!/bin/bash
# ============================================================
# dev_setup.sh — Local development environment setup
# Creates a Python virtualenv, installs dependencies,
# and copies .env.example to .env if .env does not exist.
# ============================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Setting up development environment..."

# Create virtualenv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "==> Creating Python virtualenv (.venv)..."
    python3.12 -m venv .venv
fi

# Activate virtualenv
source .venv/bin/activate

# Upgrade pip
echo "==> Upgrading pip..."
pip install --upgrade pip

# Install dev dependencies
echo "==> Installing dependencies..."
pip install -r requirements-dev.txt

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "==> Copying .env.example to .env..."
    cp .env.example .env
    echo "    IMPORTANT: Edit .env and fill in your credentials before starting the app."
else
    echo "==> .env already exists, skipping copy."
fi

echo ""
echo "==> Setup complete!"
echo "    Activate virtualenv: source .venv/bin/activate"
echo "    Start development server: ./scripts/run_dev.sh"
