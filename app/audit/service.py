"""
Audit service — fire-and-forget event emission + query.

emit_event() is the primary interface for writing audit events.
It uses asyncio.create_task() to write non-blockingly — the
calling request handler does not wait for the audit write to complete.
"""

import asyncio
import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.audit.repository import AuditRepository
from app.audit.schemas import AuditEventFilter

logger = logging.getLogger(__name__)

# Set to hold strong references to background tasks
_background_tasks: set[asyncio.Task[None]] = set()


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    async def list_events(
        self,
        filters: AuditEventFilter | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AuditEvent]:
        return await self._repo.query(filters=filters, limit=limit, offset=offset)

    async def count_events(self, filters: AuditEventFilter | None = None) -> int:
        return await self._repo.count(filters=filters)


def emit_event(
    action: str,
    actor_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """
    Fire-and-forget audit event emission.

    Creates an asyncio task to write the event non-blockingly.
    Call this from any service method that performs a state-changing operation.

    Usage:
        emit_event("device_control", actor_id=user.id, resource_type="device",
                   resource_id=ain, payload={"action": "on"})
    """
    _task = asyncio.create_task(
        _write_event(
            action=action,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    # Store reference to prevent garbage collection of the task
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)


async def _write_event(
    action: str,
    actor_id: uuid.UUID | None,
    resource_type: str | None,
    resource_id: str | None,
    payload: dict[str, Any] | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Internal coroutine that actually writes the audit event to the DB."""
    from app.db.session import async_session_factory

    try:
        event = AuditEvent(
            timestamp=datetime.now(UTC),
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        async with async_session_factory() as session:
            session.add(event)
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to write audit event (action=%s): %s", action, exc)
