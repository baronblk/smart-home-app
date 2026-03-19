"""
Device group repository — database queries for groups and membership.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.groups.models import DeviceGroup, DeviceGroupMember


class DeviceGroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> Sequence[DeviceGroup]:
        result = await self._session.execute(
            select(DeviceGroup)
            .options(selectinload(DeviceGroup.members))
            .order_by(DeviceGroup.display_order, DeviceGroup.name)
        )
        return result.scalars().all()

    async def get_by_id(self, group_id: uuid.UUID) -> DeviceGroup | None:
        result = await self._session.execute(
            select(DeviceGroup)
            .options(selectinload(DeviceGroup.members))
            .where(DeviceGroup.id == group_id)
        )
        return result.scalar_one_or_none()

    async def create(self, group: DeviceGroup) -> DeviceGroup:
        self._session.add(group)
        await self._session.flush()
        await self._session.refresh(group, attribute_names=["members"])
        return group

    async def update(self, group: DeviceGroup) -> DeviceGroup:
        await self._session.flush()
        await self._session.refresh(group, attribute_names=["members"])
        return group

    async def delete(self, group: DeviceGroup) -> None:
        await self._session.delete(group)
        await self._session.flush()

    async def add_member(self, member: DeviceGroupMember) -> None:
        self._session.add(member)
        await self._session.flush()

    async def remove_member(self, group_id: uuid.UUID, device_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(DeviceGroupMember).where(
                DeviceGroupMember.group_id == group_id,
                DeviceGroupMember.device_id == device_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await self._session.delete(member)
        await self._session.flush()
        return True

    async def get_groups_for_device(self, device_id: uuid.UUID) -> Sequence[DeviceGroup]:
        result = await self._session.execute(
            select(DeviceGroup)
            .join(DeviceGroupMember)
            .where(DeviceGroupMember.device_id == device_id)
            .options(selectinload(DeviceGroup.members))
            .order_by(DeviceGroup.display_order)
        )
        return result.scalars().all()
