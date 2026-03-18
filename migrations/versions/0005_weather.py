"""weather_cache table

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weather_cache",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("location_key", sa.String(64), nullable=False, unique=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", JSONB, nullable=False, server_default="{}"),
        sa.Column("temperature_celsius", sa.Float(), nullable=True),
        sa.Column("feels_like_celsius", sa.Float(), nullable=True),
        sa.Column("humidity_percent", sa.Integer(), nullable=True),
        sa.Column("condition", sa.String(64), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("wind_speed_ms", sa.Float(), nullable=True),
        sa.Column("icon_code", sa.String(16), nullable=True),
    )
    op.create_index("ix_weather_cache_location_key", "weather_cache", ["location_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_weather_cache_location_key", "weather_cache")
    op.drop_table("weather_cache")
