"""Analytics endpoints — aggregated time-series data for charts."""
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.devices.models import Device, DeviceStateSnapshot
from app.users.models import User

router = APIRouter()


@router.get("/power/history")
async def power_history(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Hourly average total power consumption for the last N hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    result = await session.execute(
        select(
            func.date_trunc("hour", DeviceStateSnapshot.recorded_at).label("hour"),
            func.avg(DeviceStateSnapshot.power_watts).label("avg_watts"),
            func.sum(DeviceStateSnapshot.power_watts).label("total_watts"),
        )
        .where(
            DeviceStateSnapshot.power_watts.isnot(None),
            DeviceStateSnapshot.recorded_at >= since,
        )
        .group_by(func.date_trunc("hour", DeviceStateSnapshot.recorded_at))
        .order_by(func.date_trunc("hour", DeviceStateSnapshot.recorded_at))
    )
    rows = result.all()
    return [
        {
            "hour": row.hour.isoformat() if row.hour else None,
            "avg_watts": round(float(row.avg_watts), 1) if row.avg_watts else 0.0,
            "total_watts": round(float(row.total_watts), 1) if row.total_watts else 0.0,
        }
        for row in rows
    ]


@router.get("/temperature/history")
async def temperature_history(
    ain: str | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Hourly average temperature for a device or all thermostats."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    q = (
        select(
            func.date_trunc("hour", DeviceStateSnapshot.recorded_at).label("hour"),
            func.avg(DeviceStateSnapshot.temperature_celsius).label("avg_temp"),
        )
        .where(
            DeviceStateSnapshot.temperature_celsius.isnot(None),
            DeviceStateSnapshot.recorded_at >= since,
        )
        .group_by(func.date_trunc("hour", DeviceStateSnapshot.recorded_at))
        .order_by(func.date_trunc("hour", DeviceStateSnapshot.recorded_at))
    )
    if ain:
        device_subq = select(Device.id).where(Device.ain == ain).scalar_subquery()
        q = q.where(DeviceStateSnapshot.device_id == device_subq)
    result = await session.execute(q)
    rows = result.all()
    return [
        {
            "hour": row.hour.isoformat() if row.hour else None,
            "avg_temp": round(float(row.avg_temp), 1) if row.avg_temp else None,
        }
        for row in rows
    ]


@router.get("/devices/top-consumers")
async def top_consumers(
    limit: int = Query(default=10, ge=1, le=50),
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Top N devices by average power consumption over the last N hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    result = await session.execute(
        select(
            Device.ain,
            Device.name,
            func.avg(DeviceStateSnapshot.power_watts).label("avg_watts"),
        )
        .join(DeviceStateSnapshot, DeviceStateSnapshot.device_id == Device.id)
        .where(
            DeviceStateSnapshot.power_watts.isnot(None),
            DeviceStateSnapshot.power_watts > 0,
            DeviceStateSnapshot.recorded_at >= since,
        )
        .group_by(Device.id, Device.ain, Device.name)
        .order_by(func.avg(DeviceStateSnapshot.power_watts).desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "ain": row.ain,
            "name": row.name,
            "avg_watts": round(float(row.avg_watts), 1) if row.avg_watts else 0.0,
        }
        for row in rows
    ]
