#!/usr/bin/env python3
"""
generate_secret.py — Generate a cryptographically secure SECRET_KEY.

Usage:
    python scripts/generate_secret.py
"""
import secrets

key = secrets.token_urlsafe(64)
print(f"SECRET_KEY={key}")
