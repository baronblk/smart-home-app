"""
Device group service — business logic for organizing devices into groups.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.groups.models import DeviceGroup, DeviceGroupMember
from app.groups.repository import DeviceGroupRepository
from app.groups.schemas import DeviceGroupCreate, DeviceGroupUpdate


class DeviceGroupService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DeviceGroupRepository(session)

    async def list_groups(self) -> Sequence[DeviceGroup]:
        return await self._repo.get_all()

    async def get_group(self, group_id: uuid.UUID) -> DeviceGroup:
        group = await self._repo.get_by_id(group_id)
        if group is None:
            raise NotFoundError(f"Group {group_id} not found.")
        return group

    async def create_group(
        self, data: DeviceGroupCreate, created_by: uuid.UUID | None = None
    ) -> DeviceGroup:
        group = DeviceGroup(
            name=data.name,
            icon=data.icon,
            color=data.color,
            display_order=data.display_order,
            created_by=created_by,
        )
        return await self._repo.create(group)

    async def update_group(self, group_id: uuid.UUID, data: DeviceGroupUpdate) -> DeviceGroup:
        group = await self.get_group(group_id)
        if data.name is not None:
            group.name = data.name
        if data.icon is not None:
            group.icon = data.icon
        if data.color is not None:
            group.color = data.color
        if data.display_order is not None:
            group.display_order = data.display_order
        return await self._repo.update(group)

    async def delete_group(self, group_id: uuid.UUID) -> None:
        group = await self.get_group(group_id)
        await self._repo.delete(group)

    async def add_device_to_group(
        self, group_id: uuid.UUID, device_id: uuid.UUID, display_order: int = 0
    ) -> None:
        # Verify group exists
        await self.get_group(group_id)
        try:
            member = DeviceGroupMember(
                group_id=group_id,
                device_id=device_id,
                display_order=display_order,
            )
            await self._repo.add_member(member)
        except Exception as exc:
            raise ConflictError("Device is already in this group.") from exc

    async def remove_device_from_group(self, group_id: uuid.UUID, device_id: uuid.UUID) -> None:
        removed = await self._repo.remove_member(group_id, device_id)
        if not removed:
            raise NotFoundError("Device not found in this group.")
