"""
WeatherCache SQLAlchemy model.

Stores the last successful OpenWeatherMap API response.
The cache is refreshed every 30 minutes by the APScheduler background job.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class WeatherCache(Base, UUIDPrimaryKeyMixin):
    """Single-row cache for current weather data per location."""

    __tablename__ = "weather_cache"

    location_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Full API response stored as JSONB for flexible access
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Denormalized fields for quick access without JSONB parsing
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    feels_like_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[int | None] = mapped_column(nullable=True)
    condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    icon_code: Mapped[str | None] = mapped_column(String(16), nullable=True)

    def __repr__(self) -> str:
        return f"<WeatherCache loc={self.location_key} fetched={self.fetched_at}>"
