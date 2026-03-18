"""
AuditEvent SQLAlchemy model.

The audit_events table is APPEND-ONLY. No UPDATE or DELETE operations
are permitted at the repository level — this is enforced by the
AuditRepository class, which exposes no update/delete methods.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit event record.

    action: machine-readable string, e.g. "device_control", "user_login"
    resource_type: "device" | "user" | "schedule" | "automation_rule"
    resource_id: string representation of the resource's identifier (AIN or UUID)
    payload: JSONB with full event context (before/after values, parameters, etc.)
    """
    __tablename__ = "audit_events"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditEvent action={self.action} resource={self.resource_type}/{self.resource_id}>"
