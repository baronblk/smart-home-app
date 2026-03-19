"""
Device group models — organize devices into rooms/categories.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceGroup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)

    members: Mapped[list["DeviceGroupMember"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="DeviceGroupMember.display_order",
    )

    def __repr__(self) -> str:
        return f"<DeviceGroup name={self.name!r}>"


class DeviceGroupMember(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "device_group_members"
    __table_args__ = (UniqueConstraint("group_id", "device_id", name="uq_group_device"),)

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device_groups.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    group: Mapped["DeviceGroup"] = relationship(back_populates="members")
