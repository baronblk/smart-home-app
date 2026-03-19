"""Add device groups and favorites.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Device groups table
    op.create_table(
        "device_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Group members (many-to-many)
    op.create_table(
        "device_group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("device_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("group_id", "device_id", name="uq_group_device"),
    )
    op.create_index("ix_device_group_members_group_id", "device_group_members", ["group_id"])
    op.create_index("ix_device_group_members_device_id", "device_group_members", ["device_id"])

    # Add favorites and ordering to devices
    op.add_column("devices", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("devices", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("devices", "display_order")
    op.drop_column("devices", "is_favorite")
    op.drop_table("device_group_members")
    op.drop_table("device_groups")
