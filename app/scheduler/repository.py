"""
Scheduler repository — database queries for Schedule and AutomationRule.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler.models import AutomationRule, Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, schedule_id: uuid.UUID) -> Schedule | None:
        result = await self._session.execute(select(Schedule).where(Schedule.id == schedule_id))
        return result.scalar_one_or_none()

    async def get_all(self, enabled_only: bool = False) -> Sequence[Schedule]:
        query = select(Schedule).order_by(Schedule.name)
        if enabled_only:
            query = query.where(Schedule.is_enabled == True)  # noqa: E712
        result = await self._session.execute(query)
        return result.scalars().all()

    async def create(self, schedule: Schedule) -> Schedule:
        self._session.add(schedule)
        await self._session.flush()
        await self._session.refresh(schedule)
        return schedule

    async def update(self, schedule: Schedule) -> Schedule:
        await self._session.flush()
        await self._session.refresh(schedule)
        return schedule

    async def delete(self, schedule: Schedule) -> None:
        await self._session.delete(schedule)
        await self._session.flush()


class AutomationRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, rule_id: uuid.UUID) -> AutomationRule | None:
        result = await self._session.execute(
            select(AutomationRule).where(AutomationRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, enabled_only: bool = False) -> Sequence[AutomationRule]:
        query = select(AutomationRule).order_by(AutomationRule.name)
        if enabled_only:
            query = query.where(AutomationRule.is_enabled == True)  # noqa: E712
        result = await self._session.execute(query)
        return result.scalars().all()

    async def create(self, rule: AutomationRule) -> AutomationRule:
        self._session.add(rule)
        await self._session.flush()
        await self._session.refresh(rule)
        return rule

    async def update(self, rule: AutomationRule) -> AutomationRule:
        await self._session.flush()
        await self._session.refresh(rule)
        return rule

    async def delete(self, rule: AutomationRule) -> None:
        await self._session.delete(rule)
        await self._session.flush()
