"""
Weather service — fetch and cache current weather data.

The cache TTL is 30 minutes. The APScheduler background job
calls refresh_weather_cache() proactively to keep the cache warm.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.weather.client import fetch_current_weather, parse_weather_data
from app.weather.models import WeatherCache
from app.weather.schemas import WeatherRead

logger = logging.getLogger(__name__)

_CACHE_TTL_MINUTES = 30
_LOCATION_KEY = f"{settings.weather_location_lat},{settings.weather_location_lon}"


class WeatherService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self) -> WeatherRead | None:
        """
        Return cached weather data.

        If the cache is valid (not expired), return it immediately.
        If expired or missing, fetch fresh data from OpenWeatherMap.
        """
        cache = await self._get_cache()

        if cache is not None and self._is_valid(cache):
            return WeatherRead.model_validate(cache)

        # Cache miss or expired — fetch fresh
        return await self._fetch_and_cache()

    async def refresh(self) -> WeatherRead | None:
        """Force-refresh the weather cache. Called by APScheduler every 30 minutes."""
        return await self._fetch_and_cache()

    async def _fetch_and_cache(self) -> WeatherRead | None:
        # Open-Meteo doesn't need an API key, only OWM does
        if settings.weather_provider != "open-meteo" and not settings.openweathermap_api_key:
            logger.debug("No OpenWeatherMap API key configured — skipping weather fetch.")
            return None

        try:
            raw = await fetch_current_weather(
                settings.weather_location_lat,
                settings.weather_location_lon,
            )
            parsed = parse_weather_data(raw)
            now = datetime.now(UTC)
            expires = now + timedelta(minutes=_CACHE_TTL_MINUTES)

            cache = await self._get_cache()
            if cache is None:
                cache = WeatherCache(
                    location_key=_LOCATION_KEY,
                    lat=settings.weather_location_lat,
                    lon=settings.weather_location_lon,
                    fetched_at=now,
                    expires_at=expires,
                    data=raw,
                    **parsed,
                )
                self._session.add(cache)
            else:
                cache.fetched_at = now
                cache.expires_at = expires
                cache.data = raw
                for key, value in parsed.items():
                    setattr(cache, key, value)

            await self._session.flush()
            await self._session.refresh(cache)
            return WeatherRead.model_validate(cache)

        except Exception as exc:
            logger.warning("Weather fetch failed: %s", exc)
            # Return stale cache if available
            cache = await self._get_cache()
            if cache is not None:
                return WeatherRead.model_validate(cache)
            return None

    async def _get_cache(self) -> WeatherCache | None:
        result = await self._session.execute(
            select(WeatherCache).where(WeatherCache.location_key == _LOCATION_KEY)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _is_valid(cache: WeatherCache) -> bool:
        return cache.expires_at > datetime.now(UTC)
