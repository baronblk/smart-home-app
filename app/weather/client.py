"""
OpenWeatherMap HTTP client.

Uses httpx for async HTTP requests. The free tier allows 1,000 calls/day —
the 30-minute cache in WeatherService ensures we stay well within limits.
"""
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_current_weather(lat: float, lon: float) -> dict[str, Any]:
    """
    Fetch current weather from OpenWeatherMap.

    Returns the raw API response dict.
    Raises httpx.HTTPStatusError on non-2xx responses.
    Raises httpx.RequestError on network failures.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.openweathermap_api_key,
        "units": "metric",
        "lang": "de",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_OWM_BASE_URL, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.debug("OpenWeatherMap response: %s", data.get("name", "unknown location"))
        return data


def parse_weather_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the fields we care about from the raw OWM response.

    Returns a flat dict with the denormalized fields for WeatherCache.
    """
    main = data.get("main", {})
    weather_list = data.get("weather", [{}])
    weather = weather_list[0] if weather_list else {}
    wind = data.get("wind", {})

    return {
        "temperature_celsius": main.get("temp"),
        "feels_like_celsius": main.get("feels_like"),
        "humidity_percent": main.get("humidity"),
        "condition": weather.get("main"),
        "description": weather.get("description"),
        "wind_speed_ms": wind.get("speed"),
        "icon_code": weather.get("icon"),
    }
