"""
Audit repository — APPEND-ONLY access to audit_events.

This repository intentionally exposes NO update or delete methods.
The audit log is immutable by design.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.audit.schemas import AuditEventFilter


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: AuditEvent) -> None:
        """Write a new audit event. This is the ONLY write operation."""
        self._session.add(event)
        await self._session.flush()

    async def query(
        self,
        filters: AuditEventFilter | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditEvent]:
        query = select(AuditEvent).order_by(AuditEvent.timestamp.desc())

        if filters:
            if filters.action:
                query = query.where(AuditEvent.action == filters.action)
            if filters.resource_type:
                query = query.where(AuditEvent.resource_type == filters.resource_type)
            if filters.actor_id:
                query = query.where(AuditEvent.actor_id == filters.actor_id)
            if filters.since:
                query = query.where(AuditEvent.timestamp >= filters.since)
            if filters.until:
                query = query.where(AuditEvent.timestamp <= filters.until)

        query = query.limit(limit).offset(offset)
        result = await self._session.execute(query)
        return result.scalars().all()

    async def count(self, filters: AuditEventFilter | None = None) -> int:
        from sqlalchemy import func
        from sqlalchemy import select as sa_select

        query = sa_select(func.count()).select_from(AuditEvent)
        if filters:
            if filters.action:
                query = query.where(AuditEvent.action == filters.action)
            if filters.resource_type:
                query = query.where(AuditEvent.resource_type == filters.resource_type)
            if filters.actor_id:
                query = query.where(AuditEvent.actor_id == filters.actor_id)
        result = await self._session.execute(query)
        return result.scalar_one()
