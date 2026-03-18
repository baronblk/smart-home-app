"""
Database utility functions.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_db_health(session: AsyncSession) -> bool:
    """Return True if the database is reachable."""
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
