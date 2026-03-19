"""
Device group management endpoints.

GET    /api/v1/groups              — list all groups with members
POST   /api/v1/groups              — create a new group
GET    /api/v1/groups/{id}         — get group details
PUT    /api/v1/groups/{id}         — update group name/icon/color/order
DELETE /api/v1/groups/{id}         — delete a group (keeps devices)
POST   /api/v1/groups/{id}/members — add a device to a group
DELETE /api/v1/groups/{id}/members/{device_id} — remove device from group
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.groups.schemas import (
    AddMemberRequest,
    DeviceGroupCreate,
    DeviceGroupRead,
    DeviceGroupUpdate,
)
from app.groups.service import DeviceGroupService
from app.users.models import User

router = APIRouter()


def _get_service(session: AsyncSession = Depends(get_db)) -> DeviceGroupService:
    return DeviceGroupService(session)


@router.get("", response_model=list[DeviceGroupRead])
async def list_groups(
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: DeviceGroupService = Depends(_get_service),
) -> list[Any]:
    return list(await service.list_groups())


@router.post("", response_model=DeviceGroupRead, status_code=201)
async def create_group(
    data: DeviceGroupCreate,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceGroupService = Depends(_get_service),
) -> Any:
    return await service.create_group(data, created_by=current_user.id)


@router.get("/{group_id}", response_model=DeviceGroupRead)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: DeviceGroupService = Depends(_get_service),
) -> Any:
    return await service.get_group(group_id)


@router.put("/{group_id}", response_model=DeviceGroupRead)
async def update_group(
    group_id: uuid.UUID,
    data: DeviceGroupUpdate,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceGroupService = Depends(_get_service),
) -> Any:
    return await service.update_group(group_id, data)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.ADMIN)),
    service: DeviceGroupService = Depends(_get_service),
) -> None:
    await service.delete_group(group_id)


@router.post("/{group_id}/members", status_code=201)
async def add_member(
    group_id: uuid.UUID,
    data: AddMemberRequest,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceGroupService = Depends(_get_service),
) -> dict[str, str]:
    await service.add_device_to_group(group_id, data.device_id, data.display_order)
    return {"status": "added"}


@router.delete("/{group_id}/members/{device_id}", status_code=204)
async def remove_member(
    group_id: uuid.UUID,
    device_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.USER)),
    service: DeviceGroupService = Depends(_get_service),
) -> None:
    await service.remove_device_from_group(group_id, device_id)
