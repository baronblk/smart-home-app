"""Deactivate FRITZ!Box virtual group devices (Schaltgruppen) stored as real devices.

Background:
  FritzHomeAutomation.get_homeautomation_devices() returns BOTH physical
  FRITZ!DECT devices (numeric AINs like "12345 678901") AND FRITZ!Box
  virtual switch groups / Schaltgruppen (AINs starting with "grp", e.g.
  "grp97E48000"). Both were stored as Device records in earlier versions,
  causing the same device name to appear twice in the UI: once in its
  assigned group and once in the ungrouped section.

What this migration does:
  1. Deactivates (is_active = false) all Device rows whose AIN starts with
     "grp" (case-insensitive) — i.e. FRITZ!Box virtual switch groups only.
     Native FRITZ!DECT devices (numeric AINs) and third-party gateway devices
     (hex/alphanumeric AINs like "Z28DBA7FFFE6000D0") are NOT affected.
  2. Logs how many rows were affected.
  3. Does NOT delete rows — existing FK references in device_state_snapshots
     and (less likely) device_group_members are preserved.

Safe to run multiple times (idempotent).

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-20
"""

from alembic import op
from sqlalchemy import text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Count virtual-group devices before deactivating
    before = conn.execute(
        text(
            """
            SELECT COUNT(*) FROM devices
            WHERE lower(ain) LIKE 'grp%'
              AND is_active = true
            """
        )
    ).scalar()

    if before and before > 0:
        conn.execute(
            text(
                """
                UPDATE devices
                SET is_active = false
                WHERE lower(ain) LIKE 'grp%'
                """
            )
        )
        print(f"  [0007] Deactivated {before} FRITZ!Box virtual group device(s).")
    else:
        print("  [0007] No virtual group devices found — nothing to deactivate.")


def downgrade() -> None:
    # Re-activate the previously deactivated virtual-group devices.
    # In practice this is rarely needed; the physical devices are what matters.
    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE devices
            SET is_active = true
            WHERE lower(ain) LIKE 'grp%'
            """
        )
    )
