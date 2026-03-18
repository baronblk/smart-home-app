"""
pytest fixtures — shared across all test modules.

Phase 1: minimal setup.
Phase 2+: add test DB engine, session, mock provider, test client.
"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
