"""
Pydantic schemas for the Scheduler domain.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_type: str  # cron | interval | date
    trigger_config: dict[str, Any]
    action_type: str = "device_control"
    action_config: dict[str, Any]
    is_enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_config: dict[str, Any] | None = None
    action_config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class ScheduleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict[str, Any]
    action_type: str
    action_config: dict[str, Any]
    is_enabled: bool
    last_triggered: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationRuleCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_type: str  # time | device_state | weather
    trigger_config: dict[str, Any]
    condition_config: dict[str, Any] | None = None
    action_type: str = "device_control"
    action_config: dict[str, Any]
    is_enabled: bool = True


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_config: dict[str, Any] | None = None
    condition_config: dict[str, Any] | None = None
    action_config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class AutomationRuleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict[str, Any]
    condition_config: dict[str, Any] | None
    action_type: str
    action_config: dict[str, Any]
    is_enabled: bool
    last_triggered: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
