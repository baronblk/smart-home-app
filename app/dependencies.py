"""
Shared FastAPI dependency providers.

Provider-level and database-level dependencies are centralised here.
Domain-specific dependencies (e.g. get_current_user) live in their
respective modules and import from here.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for the duration of a request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
