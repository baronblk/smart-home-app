"""
Integration tests for authentication API endpoints.

Uses an in-memory SQLite test database via the MockProvider.
Full test DB setup is completed in Phase 2 conftest expansion.
"""
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Smoke test: health endpoint always returns 200."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
