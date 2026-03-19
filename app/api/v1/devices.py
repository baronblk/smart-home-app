"""
Device management endpoints.

GET  /api/v1/devices               — list all devices
POST /api/v1/devices/discover      — run device discovery + sync to DB
GET  /api/v1/devices/{ain}/state   — get live device state from provider
PATCH /api/v1/devices/{id}         — update device label/location
POST /api/v1/devices/{ain}/on      — turn device on
POST /api/v1/devices/{ain}/off     — turn device off
PUT  /api/v1/devices/{ain}/temperature — set thermostat target temperature
PUT  /api/v1/devices/{ain}/brightness  — set dimmer brightness level
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db, get_provider
from app.devices.schemas import (
    DeviceRead,
    DeviceSnapshotRead,
    DeviceStateRead,
    DeviceUpdate,
    DiscoveryResult,
    SetBrightnessRequest,
    SetTemperatureRequest,
)
from app.devices.service import DeviceService
from app.providers.base import BaseProvider
from app.users.models import User

router = APIRouter()


def _get_service(
    session: AsyncSession = Depends(get_db),
    provider: BaseProvider = Depends(get_provider),
) -> DeviceService:
    return DeviceService(session, provider)


@router.get("", response_model=list[DeviceRead])
async def list_devices(
    include_inactive: bool = False,
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: DeviceService = Depends(_get_service),
) -> list[Any]:
    return list(await service.list_devices(include_inactive=include_inactive))


@router.post("/discover", response_model=DiscoveryResult)
async def discover_devices(
    current_user: User = Depends(require_role(Role.ADMIN)),
    service: DeviceService = Depends(_get_service),
) -> DiscoveryResult:
    """Trigger FRITZ!Box device discovery and sync results to the database."""
    return await service.discover_and_sync()


@router.get("/{ain}/state", response_model=DeviceStateRead)
async def get_device_state(
    ain: str,
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: DeviceService = Depends(_get_service),
) -> object:
    state = await service.get_live_state(ain)
    return state


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: uuid.UUID,
    data: DeviceUpdate,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceService = Depends(_get_service),
) -> object:
    return await service.update_device(device_id, data)


@router.post("/{ain}/on", status_code=204)
async def turn_on(
    ain: str,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceService = Depends(_get_service),
) -> None:
    await service.turn_on(ain)


@router.post("/{ain}/off", status_code=204)
async def turn_off(
    ain: str,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceService = Depends(_get_service),
) -> None:
    await service.turn_off(ain)


@router.put("/{ain}/temperature", status_code=204)
async def set_temperature(
    ain: str,
    data: SetTemperatureRequest,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceService = Depends(_get_service),
) -> None:
    await service.set_temperature(ain, data.celsius)


@router.put("/{ain}/brightness", status_code=204)
async def set_brightness(
    ain: str,
    data: SetBrightnessRequest,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceService = Depends(_get_service),
) -> None:
    await service.set_brightness(ain, data.level)


@router.get("/{ain}/snapshots", response_model=list[DeviceSnapshotRead])
async def get_device_snapshots(
    ain: str,
    period: str = "24h",
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: DeviceService = Depends(_get_service),
) -> list[Any]:
    """Get historical state snapshots for charts. Periods: 24h, 7d, 30d."""
    snapshots = await service.get_device_snapshots(ain, period)
    return list(snapshots)
