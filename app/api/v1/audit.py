"""
Audit log endpoints — admin-only, paginated and filterable.

GET /api/v1/audit — list audit events
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventFilter, AuditEventRead
from app.audit.service import AuditService
from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.users.models import User

router = APIRouter()


@router.get("", response_model=list[AuditEventRead])
async def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    actor_id: uuid.UUID | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    current_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
) -> list:
    filters = AuditEventFilter(
        action=action,
        resource_type=resource_type,
        actor_id=actor_id,
        since=since,
        until=until,
    )
    service = AuditService(session)
    return list(await service.list_events(filters=filters, limit=limit, offset=offset))
