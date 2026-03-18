"""
Weather endpoints.

GET /api/v1/weather/current — return cached current weather
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import Role, require_role
from app.dependencies import get_db
from app.users.models import User
from app.weather.schemas import WeatherRead
from app.weather.service import WeatherService

router = APIRouter()


@router.get("/current", response_model=WeatherRead | None)
async def get_current_weather(
    current_user: User = Depends(require_role(Role.VIEWER)),
    session: AsyncSession = Depends(get_db),
) -> WeatherRead | None:
    """Return cached current weather. Fetches fresh data if cache is expired."""
    service = WeatherService(session)
    return await service.get_current()
