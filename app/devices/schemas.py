"""
Pydantic schemas for the Device domain API.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceRead(BaseModel):
    id: uuid.UUID
    ain: str
    name: str
    device_type: str
    capabilities: list[str]
    location: str | None
    is_active: bool
    is_favorite: bool
    display_order: int
    last_seen: datetime | None
    firmware_version: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    is_active: bool | None = None
    is_favorite: bool | None = None
    display_order: int | None = None


class DeviceStateRead(BaseModel):
    ain: str
    is_on: bool | None
    temperature_celsius: float | None
    target_temperature: float | None
    power_watts: float | None
    energy_wh: float | None
    brightness_level: int | None
    last_updated: datetime

    model_config = {"from_attributes": True}


class DeviceWithStateRead(DeviceRead):
    state: DeviceStateRead | None = None


class SetSwitchRequest(BaseModel):
    on: bool


class SetTemperatureRequest(BaseModel):
    celsius: float = Field(..., ge=8.0, le=28.0, description="Target temperature (8-28°C)")


class SetBrightnessRequest(BaseModel):
    level: int = Field(..., ge=0, le=255, description="Brightness level (0=off, 255=max)")


class DeviceSnapshotRead(BaseModel):
    """Snapshot data point for charts and history."""

    recorded_at: datetime
    is_on: bool | None
    temperature_celsius: float | None
    target_temperature: float | None
    power_watts: float | None
    energy_wh: float | None
    brightness_level: int | None

    model_config = {"from_attributes": True}


class DiscoveryResult(BaseModel):
    discovered: int
    added: int
    updated: int
    deactivated: int
