"""
Seed runner — executes all seed scripts in order.

Usage:
    python seeds/run_seeds.py

Seeds are idempotent (safe to run multiple times).
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def run_all() -> None:
    print("==> Running seed scripts...")

    from seeds.seed_001_admin_user import seed as seed_001
    await seed_001()

    print("==> All seeds complete.")


if __name__ == "__main__":
    asyncio.run(run_all())
