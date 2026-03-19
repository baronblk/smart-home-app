"""
Pydantic schemas for the DeviceGroup domain.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    icon: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    display_order: int = 0


class DeviceGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    icon: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    display_order: int | None = None


class DeviceGroupMemberRead(BaseModel):
    device_id: uuid.UUID
    display_order: int

    model_config = {"from_attributes": True}


class DeviceGroupRead(BaseModel):
    id: uuid.UUID
    name: str
    icon: str | None
    color: str | None
    display_order: int
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    members: list[DeviceGroupMemberRead] = []

    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    device_id: uuid.UUID
    display_order: int = 0
