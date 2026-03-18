"""
Alembic migration environment — async-aware configuration.

Uses the synchronous psycopg2 DSN (ALEMBIC_DATABASE_URL) for
running migrations, while the application itself uses asyncpg.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import all models so Alembic can detect schema changes
# (models register themselves on Base.metadata when imported)
from app.models.base import Base  # noqa: F401

# Import domain models so Alembic sees them in Base.metadata
from app.users.models import User  # noqa: F401
from app.devices.models import Device, DeviceStateSnapshot  # noqa: F401

from app.scheduler.models import AutomationRule, Schedule  # noqa: F401
from app.audit.models import AuditEvent  # noqa: F401
from app.weather.models import WeatherCache  # noqa: F401

# Alembic Config object, gives access to values in alembic.ini
config = context.config

# Set up logging from alembic.ini config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the synchronous DB URL from environment
database_url = os.environ.get("ALEMBIC_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
# Convert asyncpg URL to psycopg2 for synchronous Alembic use
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with an active DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
