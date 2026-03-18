"""
Scheduler service — CRUD for schedules and automation rules.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.scheduler.engine import scheduler
from app.scheduler.models import AutomationRule, Schedule
from app.scheduler.repository import AutomationRuleRepository, ScheduleRepository
from app.scheduler.schemas import (
    AutomationRuleCreate,
    AutomationRuleUpdate,
    ScheduleCreate,
    ScheduleUpdate,
)


class SchedulerService:
    def __init__(self, session: AsyncSession) -> None:
        self._schedule_repo = ScheduleRepository(session)
        self._rule_repo = AutomationRuleRepository(session)

    # ------------------------------------------------------------------
    # Schedules
    # ------------------------------------------------------------------

    async def create_schedule(
        self, data: ScheduleCreate, created_by: uuid.UUID | None = None
    ) -> Schedule:
        schedule = Schedule(
            name=data.name,
            description=data.description,
            trigger_type=data.trigger_type,
            trigger_config=data.trigger_config,
            action_type=data.action_type,
            action_config=data.action_config,
            is_enabled=data.is_enabled,
            created_by=created_by,
        )
        result = await self._schedule_repo.create(schedule)
        if data.is_enabled:
            self._register_apscheduler_job(result)
        return result

    async def list_schedules(self) -> Sequence[Schedule]:
        return await self._schedule_repo.get_all()

    async def get_schedule(self, schedule_id: uuid.UUID) -> Schedule:
        s = await self._schedule_repo.get_by_id(schedule_id)
        if s is None:
            raise NotFoundError(f"Schedule {schedule_id} not found.")
        return s

    async def update_schedule(self, schedule_id: uuid.UUID, data: ScheduleUpdate) -> Schedule:
        schedule = await self.get_schedule(schedule_id)
        if data.name is not None:
            schedule.name = data.name
        if data.description is not None:
            schedule.description = data.description
        if data.trigger_config is not None:
            schedule.trigger_config = data.trigger_config
        if data.action_config is not None:
            schedule.action_config = data.action_config
        if data.is_enabled is not None:
            schedule.is_enabled = data.is_enabled

        result = await self._schedule_repo.update(schedule)
        self._sync_apscheduler_job(result)
        return result

    async def delete_schedule(self, schedule_id: uuid.UUID) -> None:
        schedule = await self.get_schedule(schedule_id)
        job_id = f"schedule_{schedule_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        await self._schedule_repo.delete(schedule)

    # ------------------------------------------------------------------
    # Automation Rules
    # ------------------------------------------------------------------

    async def create_rule(
        self, data: AutomationRuleCreate, created_by: uuid.UUID | None = None
    ) -> AutomationRule:
        rule = AutomationRule(
            name=data.name,
            description=data.description,
            trigger_type=data.trigger_type,
            trigger_config=data.trigger_config,
            condition_config=data.condition_config,
            action_type=data.action_type,
            action_config=data.action_config,
            is_enabled=data.is_enabled,
            created_by=created_by,
        )
        return await self._rule_repo.create(rule)

    async def list_rules(self) -> Sequence[AutomationRule]:
        return await self._rule_repo.get_all()

    async def get_rule(self, rule_id: uuid.UUID) -> AutomationRule:
        r = await self._rule_repo.get_by_id(rule_id)
        if r is None:
            raise NotFoundError(f"Automation rule {rule_id} not found.")
        return r

    async def update_rule(self, rule_id: uuid.UUID, data: AutomationRuleUpdate) -> AutomationRule:
        rule = await self.get_rule(rule_id)
        if data.name is not None:
            rule.name = data.name
        if data.description is not None:
            rule.description = data.description
        if data.trigger_config is not None:
            rule.trigger_config = data.trigger_config
        if data.condition_config is not None:
            rule.condition_config = data.condition_config
        if data.action_config is not None:
            rule.action_config = data.action_config
        if data.is_enabled is not None:
            rule.is_enabled = data.is_enabled
        return await self._rule_repo.update(rule)

    async def delete_rule(self, rule_id: uuid.UUID) -> None:
        rule = await self.get_rule(rule_id)
        await self._rule_repo.delete(rule)

    # ------------------------------------------------------------------
    # APScheduler integration for time-based schedules
    # ------------------------------------------------------------------

    def _register_apscheduler_job(self, schedule: Schedule) -> None:
        """Register a Schedule as an APScheduler job."""
        from app.dependencies import get_provider
        from app.scheduler.tasks import _execute_action

        job_id = f"schedule_{schedule.id}"
        action_config = schedule.action_config

        async def job_func() -> None:
            from datetime import datetime

            from app.db.session import async_session_factory
            from app.scheduler.repository import ScheduleRepository

            provider = get_provider()
            await _execute_action(action_config, provider)

            # Update last_triggered timestamp
            async with async_session_factory() as session:
                repo = ScheduleRepository(session)
                s = await repo.get_by_id(schedule.id)
                if s is not None:
                    s.last_triggered = datetime.now(UTC)
                await session.commit()

        trigger = self._build_trigger(schedule.trigger_type, schedule.trigger_config)
        if trigger is None:
            return

        scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            max_instances=1,
        )

    def _sync_apscheduler_job(self, schedule: Schedule) -> None:
        """Update or remove the APScheduler job based on is_enabled."""
        job_id = f"schedule_{schedule.id}"
        if schedule.is_enabled:
            self._register_apscheduler_job(schedule)
        else:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

    @staticmethod
    def _build_trigger(trigger_type: str, config: dict[str, Any]) -> Any:
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.date import DateTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        if trigger_type == "cron":
            return CronTrigger(**config)
        elif trigger_type == "interval":
            return IntervalTrigger(**config)
        elif trigger_type == "date":
            return DateTrigger(**config)
        return None
