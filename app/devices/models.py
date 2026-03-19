"""
Device SQLAlchemy models.

Device: persists discovered devices with their metadata.
DeviceStateSnapshot: time-series cache of device states (used by dashboard + history).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Device(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persisted device record.

    The 'ain' is the primary business identifier (FRITZ!Box AIN).
    'id' (UUID) is used for internal relations and API paths.

    Real-time state is NOT stored here — it is fetched from the provider
    on demand (or from the DeviceStateSnapshot cache).
    """

    __tablename__ = "devices"

    ain: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Stored as JSONB list of capability strings, e.g. ["SWITCH", "POWER_METER"]
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # User-defined label for location/room
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Whether the device is tracked/active in the app
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Last time the device was seen online via discovery
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Firmware version from last discovery
    firmware_version: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    # Dashboard favorites and ordering
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    def __repr__(self) -> str:
        return f"<Device ain={self.ain} name={self.name} type={self.device_type}>"


class DeviceStateSnapshot(Base, UUIDPrimaryKeyMixin):
    """
    Point-in-time device state snapshot.

    Written by the background poll_all_devices job every 60 seconds.
    Used for: dashboard display (latest), and history charts.
    NOT used for real-time device control.
    """

    __tablename__ = "device_state_snapshots"

    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    ain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    is_on: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_watts: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_level: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<DeviceStateSnapshot ain={self.ain} at={self.recorded_at}>"
