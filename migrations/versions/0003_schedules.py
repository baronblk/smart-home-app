"""schedules and automation_rules tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("action_type", sa.String(32), nullable=False, server_default="device_control"),
        sa.Column("action_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_triggered", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_schedules_id", "schedules", ["id"])

    op.create_table(
        "automation_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("condition_config", JSONB, nullable=True),
        sa.Column("action_type", sa.String(32), nullable=False, server_default="device_control"),
        sa.Column("action_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_triggered", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_automation_rules_id", "automation_rules", ["id"])


def downgrade() -> None:
    op.drop_index("ix_automation_rules_id", "automation_rules")
    op.drop_table("automation_rules")
    op.drop_index("ix_schedules_id", "schedules")
    op.drop_table("schedules")
