"""Re-activate third-party gateway devices wrongly deactivated by migration 0007.

Background:
  Migration 0007 used `ain !~ '^[0-9 ]+$'` to identify virtual FRITZ!Box
  groups (Schaltgruppen), but this regex also matched third-party devices
  connected via FRITZ!Smart Gateway whose AINs are hex/alphanumeric (e.g.
  "Z28DBA7FFFE6000D0" for an IKEA TRETAKT Zigbee plug). Those devices were
  wrongly deactivated.

  The correct criterion for virtual groups is an AIN that starts with "grp"
  (case-insensitive). Migration 0007 has been corrected to use that pattern,
  but devices already deactivated in production need to be restored.

What this migration does:
  1. Re-activates (is_active = true) all Device rows whose AIN does NOT start
     with "grp" (case-insensitive) and whose AIN is non-empty, and which are
     currently marked is_active = false.
  2. Logs how many rows were re-activated.
  3. Downgrade is a no-op — we never want to re-deactivate real devices.

Safe to run multiple times (idempotent).

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-20
"""

from alembic import op
from sqlalchemy import text

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Count wrongly deactivated devices before restoring
    before = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM devices
            WHERE lower(ain) NOT LIKE 'grp%'
              AND ain != ''
              AND is_active = false
            """
        )
    ).scalar()

    if before and before > 0:
        conn.execute(
            text(
                """
                UPDATE devices
                SET is_active = true
                WHERE lower(ain) NOT LIKE 'grp%'
                  AND ain != ''
                  AND is_active = false
                """
            )
        )
        print(f"  [0008] Re-activated {before} wrongly deactivated third-party device(s).")
    else:
        print("  [0008] No wrongly deactivated devices found — nothing to restore.")


def downgrade() -> None:
    # No-op: we never want to re-deactivate real physical/gateway devices.
    print("  [0008] downgrade is a no-op — real devices are not re-deactivated.")
