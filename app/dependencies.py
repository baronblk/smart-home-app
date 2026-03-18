"""
Shared FastAPI dependency providers.

Provider-level and database-level dependencies are centralised here.
Domain-specific dependencies (e.g. get_current_user) live in their
respective modules and import from here.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import async_session_factory
from app.providers.base import BaseProvider


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for the duration of a request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_provider() -> BaseProvider:
    """
    Return the active device provider singleton.

    Selects MockProvider when FRITZ_MOCK_MODE=true (default for dev/test),
    FritzProvider otherwise.

    This is the ONLY place in the application that decides which provider
    implementation is active. Route handlers declare:
        provider: BaseProvider = Depends(get_provider)
    """
    if settings.fritz_mock_mode:
        from app.providers.mock.provider import MockProvider
        return MockProvider.get_instance()
    else:
        from app.providers.fritz.provider import FritzProvider
        return FritzProvider.get_instance()
