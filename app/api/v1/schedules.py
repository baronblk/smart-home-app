"""
Schedule management endpoints.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.scheduler.schemas import ScheduleCreate, ScheduleRead, ScheduleUpdate
from app.scheduler.service import SchedulerService
from app.users.models import User

router = APIRouter()


def _get_service(session: AsyncSession = Depends(get_db)) -> SchedulerService:
    return SchedulerService(session)


@router.get("", response_model=list[ScheduleRead])
async def list_schedules(
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: SchedulerService = Depends(_get_service),
) -> list:
    return list(await service.list_schedules())


@router.post("", response_model=ScheduleRead, status_code=201)
async def create_schedule(
    data: ScheduleCreate,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.create_schedule(data, created_by=current_user.id)


@router.get("/{schedule_id}", response_model=ScheduleRead)
async def get_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.get_schedule(schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    schedule_id: uuid.UUID,
    data: ScheduleUpdate,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.update_schedule(schedule_id, data)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> None:
    await service.delete_schedule(schedule_id)
