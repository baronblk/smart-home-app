"""
Automation rule management endpoints.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.scheduler.schemas import AutomationRuleCreate, AutomationRuleRead, AutomationRuleUpdate
from app.scheduler.service import SchedulerService
from app.users.models import User

router = APIRouter()


def _get_service(session: AsyncSession = Depends(get_db)) -> SchedulerService:
    return SchedulerService(session)


@router.get("", response_model=list[AutomationRuleRead])
async def list_rules(
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: SchedulerService = Depends(_get_service),
) -> list:
    return list(await service.list_rules())


@router.post("", response_model=AutomationRuleRead, status_code=201)
async def create_rule(
    data: AutomationRuleCreate,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.create_rule(data, created_by=current_user.id)


@router.get("/{rule_id}", response_model=AutomationRuleRead)
async def get_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.VIEWER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.get_rule(rule_id)


@router.put("/{rule_id}", response_model=AutomationRuleRead)
async def update_rule(
    rule_id: uuid.UUID,
    data: AutomationRuleUpdate,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> object:
    return await service.update_rule(rule_id, data)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.USER)),
    service: SchedulerService = Depends(_get_service),
) -> None:
    await service.delete_rule(rule_id)
