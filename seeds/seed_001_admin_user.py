"""
Seed 001 — Create default admin user.

Idempotent: skips creation if an admin already exists.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.auth.password import hash_password
from app.auth.rbac import Role
from app.config import settings
from app.db.session import async_session_factory
from app.users.models import User


async def seed() -> None:
    async with async_session_factory() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.role == Role.ADMIN).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            print("  [skip] admin user already exists")
            return

        admin = User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role=Role.ADMIN,
            full_name="Administrator",
        )
        session.add(admin)
        await session.commit()
        print(f"  [ok] created admin: {settings.admin_email}")
        print(f"       password:      {settings.admin_password}")


if __name__ == "__main__":
    asyncio.run(seed())
