"""
Scheduler SQLAlchemy models.

Schedule: time-based device action (cron/interval/one-shot).
AutomationRule: condition-based rule (trigger + optional condition + action).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Schedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Time-based device schedule.

    trigger_type: "cron" | "interval" | "date"
    trigger_config: APScheduler-compatible trigger kwargs as JSONB.
      cron example:   {"hour": 22, "minute": 0}
      interval example: {"seconds": 3600}
      date example:   {"run_date": "2026-04-01T08:00:00+00:00"}

    action_type: currently "device_control"
    action_config: {"ain": "...", "action": "on"|"off"|"temperature"|"brightness", "value": ...}
    """
    __tablename__ = "schedules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Trigger definition
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Action definition
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, default="device_control")
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # State
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Owner (FK to users — added as string column for simplicity before ORM relation)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Schedule name={self.name} trigger={self.trigger_type} enabled={self.is_enabled}>"


class AutomationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Condition-based automation rule.

    trigger_type: "time" | "device_state" | "weather"
    trigger_config: conditions for rule evaluation (JSONB)
      time: {"start_time": "18:00", "end_time": "22:00"}
      device_state: {"ain": "...", "property": "temperature_celsius", "operator": "lt", "value": 18}
      weather: {"property": "temperature", "operator": "lt", "value": 5}

    condition_config: optional additional conditions (JSONB, may be null)

    action_type: "device_control"
    action_config: same as Schedule.action_config
    """
    __tablename__ = "automation_rules"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    condition_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    action_type: Mapped[str] = mapped_column(String(32), nullable=False, default="device_control")
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AutomationRule name={self.name} trigger={self.trigger_type}>"
