"""
Database engine and session factory.

Uses SQLAlchemy's async engine with asyncpg as the driver.
The session factory is created once at module import time and
reused for the lifetime of the application.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Async engine — one instance per application process
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=not settings.is_production,  # Log SQL in development
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory — yields AsyncSession instances
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
