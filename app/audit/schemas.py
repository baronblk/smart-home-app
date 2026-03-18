"""
Pydantic schemas for the Audit domain.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventRead(BaseModel):
    id: uuid.UUID
    timestamp: datetime
    actor_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    payload: dict[str, Any] | None
    ip_address: str | None

    model_config = {"from_attributes": True}


class AuditEventFilter(BaseModel):
    action: str | None = None
    resource_type: str | None = None
    actor_id: uuid.UUID | None = None
    since: datetime | None = None
    until: datetime | None = None
