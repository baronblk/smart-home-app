"""
Pydantic schemas for the Weather domain.
"""
from datetime import datetime

from pydantic import BaseModel


class WeatherRead(BaseModel):
    location_key: str
    temperature_celsius: float | None
    feels_like_celsius: float | None
    humidity_percent: int | None
    condition: str | None
    description: str | None
    wind_speed_ms: float | None
    icon_code: str | None
    fetched_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}
