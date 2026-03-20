"""
Device service — business logic for the Device domain.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import device_state_cache
from app.devices.models import Device, DeviceStateSnapshot
from app.devices.repository import DeviceRepository
from app.devices.schemas import DeviceUpdate, DiscoveryResult
from app.exceptions import NotFoundError
from app.providers.base import BaseProvider, DeviceCapability, DeviceState


class DeviceService:
    def __init__(self, session: AsyncSession, provider: BaseProvider) -> None:
        self._repo = DeviceRepository(session)
        self._provider = provider

    async def discover_and_sync(self) -> DiscoveryResult:
        """
        Run device discovery and sync results to the database.

        - New devices are created.
        - Existing devices are updated (name, capabilities, firmware).
        - Devices no longer returned by discovery are deactivated.
        """
        devices_info = await self._provider.discover_devices()

        added = 0
        updated = 0

        for info in devices_info:
            existing = await self._repo.get_by_ain(info.ain)
            caps = _capabilities_to_list(info.capabilities)
            now = datetime.now(UTC)

            device = Device(
                ain=info.ain,
                name=info.name,
                device_type=str(info.device_type),
                capabilities=caps,
                firmware_version=info.firmware_version,
                last_seen=now if info.is_present else None,
            )

            if existing is None:
                await self._repo.upsert(device)
                added += 1
            else:
                await self._repo.upsert(device)
                updated += 1

        active_ains = [d.ain for d in devices_info]
        deactivated = await self._repo.deactivate_missing(active_ains)

        return DiscoveryResult(
            discovered=len(devices_info),
            added=added,
            updated=updated,
            deactivated=deactivated,
        )

    async def list_devices(self, include_inactive: bool = False) -> Sequence[Device]:
        return await self._repo.get_all(include_inactive=include_inactive)

    async def get_device(self, device_id: uuid.UUID) -> Device:
        device = await self._repo.get_by_id(device_id)
        if device is None:
            raise NotFoundError(f"Device {device_id} not found.")
        return device

    async def get_device_by_ain(self, ain: str) -> Device:
        device = await self._repo.get_by_ain(ain)
        if device is None:
            raise NotFoundError(f"Device with AIN '{ain}' not found.")
        return device

    async def get_live_state(self, ain: str) -> DeviceState:
        """Return device state — from cache (TTL 10 s) or live FRITZ!Box call."""
        return await device_state_cache.get_or_fetch(
            key=f"state:{ain}",
            ttl=10.0,
            fetch=lambda: self._provider.get_device_state(ain),
        )

    async def update_device(self, device_id: uuid.UUID, data: DeviceUpdate) -> Device:
        device = await self.get_device(device_id)
        if data.name is not None:
            device.name = data.name
        if data.location is not None:
            device.location = data.location
        if data.is_active is not None:
            device.is_active = data.is_active
        if data.is_favorite is not None:
            device.is_favorite = data.is_favorite
        if data.display_order is not None:
            device.display_order = data.display_order
        return await self._repo.update(device)

    async def turn_on(self, ain: str) -> None:
        await self._provider.set_switch(ain, on=True)
        device_state_cache.invalidate(f"state:{ain}")

    async def turn_off(self, ain: str) -> None:
        await self._provider.set_switch(ain, on=False)
        device_state_cache.invalidate(f"state:{ain}")

    async def set_temperature(self, ain: str, celsius: float) -> None:
        await self._provider.set_temperature(ain, celsius)
        device_state_cache.invalidate(f"state:{ain}")

    async def set_brightness(self, ain: str, level: int) -> None:
        await self._provider.set_dimmer(ain, level)
        device_state_cache.invalidate(f"state:{ain}")

    async def get_device_snapshots(
        self, ain: str, period: str = "24h"
    ) -> list[DeviceStateSnapshot]:
        """Get historical snapshots for chart rendering (downsampled to ≤250 points)."""
        period_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = period_map.get(period, timedelta(hours=24))
        since = datetime.now(UTC) - delta
        raw = list(await self._repo.get_snapshots_for_chart(ain, since))
        return _downsample(raw)

    async def get_latest_snapshot(self, ain: str) -> DeviceStateSnapshot | None:
        """Get the most recent snapshot for a device."""
        return await self._repo.get_latest_snapshot(ain)

    async def poll_and_snapshot_all(self) -> int:
        """
        Fetch state for all active devices and write snapshots to DB.
        Called by the APScheduler background job every 60 seconds.
        Returns the number of snapshots written.
        """
        devices = await self._repo.get_all(include_inactive=False)
        count = 0
        now = datetime.now(UTC)

        for device in devices:
            try:
                state = await self._provider.get_device_state(device.ain)
                device_state_cache.set(f"state:{device.ain}", state, ttl=65.0)
                snapshot = DeviceStateSnapshot(
                    device_id=device.id,
                    ain=device.ain,
                    recorded_at=now,
                    is_on=state.is_on,
                    temperature_celsius=state.temperature_celsius,
                    target_temperature=state.target_temperature,
                    power_watts=state.power_watts,
                    energy_wh=state.energy_wh,
                    brightness_level=state.brightness_level,
                )
                await self._repo.save_snapshot(snapshot)
                count += 1
            except Exception:
                # Device may be offline — continue polling others
                pass

        return count


def _downsample(
    data: list[DeviceStateSnapshot], max_points: int = 250
) -> list[DeviceStateSnapshot]:
    """Reduce snapshot list to at most *max_points* evenly-spaced entries."""
    if len(data) <= max_points:
        return data
    step = len(data) / max_points
    return [data[int(i * step)] for i in range(max_points)]


def _capabilities_to_list(capabilities: DeviceCapability) -> list[str]:
    """Convert DeviceCapability flags to a JSON-serializable list of strings."""
    result: list[str] = []
    for cap in DeviceCapability:
        if cap in capabilities and cap.name is not None:
            result.append(cap.name)
    return result
