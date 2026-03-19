"""
Dashboard aggregation endpoints.

GET /api/v1/dashboard/stats    — aggregated metrics for dashboard widgets
GET /api/v1/dashboard/activity — recent audit events for activity feed
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.devices.models import Device, DeviceStateSnapshot
from app.scheduler.models import AutomationRule, Schedule
from app.users.models import User

router = APIRouter()


@router.get("/stats")
async def dashboard_stats(
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Aggregated dashboard metrics."""
    # Device counts
    total_result = await session.execute(
        select(func.count()).select_from(Device).where(Device.is_active == True)  # noqa: E712
    )
    total_devices = total_result.scalar() or 0

    online_result = await session.execute(
        select(func.count())
        .select_from(Device)
        .where(Device.is_active == True, Device.last_seen.isnot(None))  # noqa: E712
    )
    online_devices = online_result.scalar() or 0

    # Power: sum of latest snapshots for devices with power_watts
    # Use a subquery to get latest snapshot per device
    power_result = await session.execute(
        select(func.sum(DeviceStateSnapshot.power_watts)).where(
            DeviceStateSnapshot.power_watts.isnot(None),
            DeviceStateSnapshot.recorded_at >= func.now() - text("INTERVAL '2 minutes'"),
        )
    )
    total_power = power_result.scalar() or 0.0

    # Average temperature from recent thermostats
    temp_result = await session.execute(
        select(func.avg(DeviceStateSnapshot.temperature_celsius)).where(
            DeviceStateSnapshot.temperature_celsius.isnot(None),
            DeviceStateSnapshot.recorded_at >= func.now() - text("INTERVAL '2 minutes'"),
        )
    )
    avg_temp = temp_result.scalar()

    # Schedule and rule counts
    schedules_result = await session.execute(
        select(func.count()).select_from(Schedule).where(Schedule.is_enabled == True)  # noqa: E712
    )
    active_schedules = schedules_result.scalar() or 0

    rules_result = await session.execute(
        select(func.count()).select_from(AutomationRule).where(AutomationRule.is_enabled == True)  # noqa: E712
    )
    active_rules = rules_result.scalar() or 0

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "total_power_watts": round(total_power, 1),
        "avg_temperature": round(avg_temp, 1) if avg_temp else None,
        "active_schedules": active_schedules,
        "active_rules": active_rules,
    }


@router.get("/activity")
async def dashboard_activity(
    limit: int = 10,
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Recent audit events for the dashboard activity feed."""
    result = await session.execute(
        select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
        }
        for e in events
    ]
