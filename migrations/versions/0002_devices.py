"""devices and device_state_snapshots tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ain", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(32), nullable=False),
        sa.Column("capabilities", JSONB, nullable=False, server_default="[]"),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmware_version", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_devices_id", "devices", ["id"])
    op.create_index("ix_devices_ain", "devices", ["ain"], unique=True)

    op.create_table(
        "device_state_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), nullable=False),
        sa.Column("ain", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_on", sa.Boolean(), nullable=True),
        sa.Column("temperature_celsius", sa.Float(), nullable=True),
        sa.Column("target_temperature", sa.Float(), nullable=True),
        sa.Column("power_watts", sa.Float(), nullable=True),
        sa.Column("energy_wh", sa.Float(), nullable=True),
        sa.Column("brightness_level", sa.Integer(), nullable=True),
    )
    op.create_index("ix_device_state_snapshots_id", "device_state_snapshots", ["id"])
    op.create_index("ix_device_state_snapshots_device_id", "device_state_snapshots", ["device_id"])
    op.create_index("ix_device_state_snapshots_ain", "device_state_snapshots", ["ain"])
    op.create_index(
        "ix_device_state_snapshots_recorded_at",
        "device_state_snapshots",
        ["recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_device_state_snapshots_recorded_at", "device_state_snapshots")
    op.drop_index("ix_device_state_snapshots_ain", "device_state_snapshots")
    op.drop_index("ix_device_state_snapshots_device_id", "device_state_snapshots")
    op.drop_index("ix_device_state_snapshots_id", "device_state_snapshots")
    op.drop_table("device_state_snapshots")
    op.drop_index("ix_devices_ain", "devices")
    op.drop_index("ix_devices_id", "devices")
    op.drop_table("devices")
