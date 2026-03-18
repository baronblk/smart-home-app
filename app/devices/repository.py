"""
Device repository — database queries for the Device domain.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import Device, DeviceStateSnapshot


class DeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        result = await self._session.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()

    async def get_by_ain(self, ain: str) -> Device | None:
        result = await self._session.execute(select(Device).where(Device.ain == ain))
        return result.scalar_one_or_none()

    async def get_all(self, include_inactive: bool = False, limit: int = 200) -> Sequence[Device]:
        query = select(Device)
        if not include_inactive:
            query = query.where(Device.is_active == True)  # noqa: E712
        query = query.order_by(Device.name).limit(limit)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def upsert(self, device: Device) -> Device:
        """Insert or update based on AIN."""
        existing = await self.get_by_ain(device.ain)
        if existing is None:
            self._session.add(device)
            await self._session.flush()
            await self._session.refresh(device)
            return device
        else:
            existing.name = device.name
            existing.device_type = device.device_type
            existing.capabilities = device.capabilities
            existing.firmware_version = device.firmware_version
            existing.last_seen = device.last_seen
            existing.is_active = True
            await self._session.flush()
            await self._session.refresh(existing)
            return existing

    async def update(self, device: Device) -> Device:
        await self._session.flush()
        await self._session.refresh(device)
        return device

    async def deactivate_missing(self, active_ains: list[str]) -> int:
        """Mark devices not in active_ains as inactive. Returns count."""
        result = await self._session.execute(
            select(Device).where(
                Device.ain.notin_(active_ains),
                Device.is_active == True,  # noqa: E712
            )
        )
        devices = result.scalars().all()
        for d in devices:
            d.is_active = False
        await self._session.flush()
        return len(devices)

    async def save_snapshot(self, snapshot: DeviceStateSnapshot) -> None:
        self._session.add(snapshot)
        await self._session.flush()

    async def get_latest_snapshot(self, ain: str) -> DeviceStateSnapshot | None:
        result = await self._session.execute(
            select(DeviceStateSnapshot)
            .where(DeviceStateSnapshot.ain == ain)
            .order_by(DeviceStateSnapshot.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshots(
        self, ain: str, since: datetime | None = None, limit: int = 100
    ) -> Sequence[DeviceStateSnapshot]:
        query = (
            select(DeviceStateSnapshot)
            .where(DeviceStateSnapshot.ain == ain)
            .order_by(DeviceStateSnapshot.recorded_at.desc())
            .limit(limit)
        )
        if since is not None:
            query = query.where(DeviceStateSnapshot.recorded_at >= since)
        result = await self._session.execute(query)
        return result.scalars().all()
