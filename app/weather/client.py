"""
Weather HTTP clients — supports Open-Meteo (free, no key) and OpenWeatherMap.

Open-Meteo is preferred (WEATHER_PROVIDER=open-meteo) as it requires no API key.
OpenWeatherMap requires an API key (OPENWEATHERMAP_API_KEY).
"""

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Open-Meteo client (free, no API key required)
# ============================================================
_OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Map WMO weather codes to condition strings and icon codes
_WMO_CODES: dict[int, tuple[str, str, str]] = {
    0: ("Clear", "Klar", "01d"),
    1: ("Clear", "Überwiegend klar", "01d"),
    2: ("Clouds", "Teilweise bewölkt", "02d"),
    3: ("Clouds", "Bewölkt", "04d"),
    45: ("Fog", "Nebel", "50d"),
    48: ("Fog", "Reifnebel", "50d"),
    51: ("Drizzle", "Leichter Nieselregen", "09d"),
    53: ("Drizzle", "Nieselregen", "09d"),
    55: ("Drizzle", "Starker Nieselregen", "09d"),
    61: ("Rain", "Leichter Regen", "10d"),
    63: ("Rain", "Regen", "10d"),
    65: ("Rain", "Starker Regen", "10d"),
    71: ("Snow", "Leichter Schneefall", "13d"),
    73: ("Snow", "Schneefall", "13d"),
    75: ("Snow", "Starker Schneefall", "13d"),
    80: ("Rain", "Leichte Regenschauer", "09d"),
    81: ("Rain", "Regenschauer", "09d"),
    82: ("Rain", "Starke Regenschauer", "09d"),
    95: ("Thunderstorm", "Gewitter", "11d"),
}


async def fetch_openmeteo_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fetch current weather from Open-Meteo (free, no API key needed)."""
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        ),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_OPENMETEO_BASE_URL, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        logger.debug("Open-Meteo response for %.2f,%.2f", lat, lon)
        return data


def parse_openmeteo_data(data: dict[str, Any]) -> dict[str, Any]:
    """Parse Open-Meteo response into our standard weather fields."""
    current = data.get("current", {})
    wmo_code = current.get("weather_code", 0)
    condition, description, icon = _WMO_CODES.get(wmo_code, ("Unknown", "Unbekannt", "01d"))

    return {
        "temperature_celsius": current.get("temperature_2m"),
        "feels_like_celsius": current.get("apparent_temperature"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "condition": condition,
        "description": description,
        "wind_speed_ms": round((current.get("wind_speed_10m", 0)) / 3.6, 1),  # km/h → m/s
        "icon_code": icon,
    }


# ============================================================
# OpenWeatherMap client (API key required)
# ============================================================
_OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_owm_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fetch current weather from OpenWeatherMap (requires API key)."""
    params: dict[str, str | float] = {
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


def parse_owm_data(data: dict[str, Any]) -> dict[str, Any]:
    """Parse OpenWeatherMap response into our standard weather fields."""
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


# ============================================================
# Unified interface
# ============================================================
async def fetch_current_weather(lat: float, lon: float) -> dict[str, Any]:
    """Fetch weather using the configured provider."""
    provider = getattr(settings, "weather_provider", "open-meteo")
    if provider == "open-meteo":
        return await fetch_openmeteo_weather(lat, lon)
    else:
        return await fetch_owm_weather(lat, lon)


def parse_weather_data(data: dict[str, Any]) -> dict[str, Any]:
    """Parse weather data using the configured provider."""
    provider = getattr(settings, "weather_provider", "open-meteo")
    if provider == "open-meteo":
        return parse_openmeteo_data(data)
    else:
        return parse_owm_data(data)
