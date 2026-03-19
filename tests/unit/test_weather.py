"""
Unit tests for the weather domain.

Tests parse_weather_data() and WeatherService cache logic in isolation.
No real HTTP requests are made — httpx is patched.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.weather.client import parse_owm_data as parse_weather_data

# ------------------------------------------------------------------
# OWM response fixture
# ------------------------------------------------------------------

OWM_RESPONSE: dict[str, Any] = {
    "name": "Berlin",
    "sys": {"country": "DE"},
    "main": {
        "temp": 12.4,
        "feels_like": 10.1,
        "humidity": 72,
    },
    "weather": [{"main": "Clouds", "description": "überwiegend bewölkt", "icon": "04d"}],
    "wind": {"speed": 5.3, "deg": 220},
    "visibility": 10000,
    "clouds": {"all": 75},
}


# ------------------------------------------------------------------
# parse_weather_data
# ------------------------------------------------------------------


def test_parse_weather_data_extracts_all_fields() -> None:
    parsed = parse_weather_data(OWM_RESPONSE)

    assert parsed["temperature_celsius"] == pytest.approx(12.4)
    assert parsed["feels_like_celsius"] == pytest.approx(10.1)
    assert parsed["humidity_percent"] == 72
    assert parsed["condition"] == "Clouds"
    assert parsed["description"] == "überwiegend bewölkt"
    assert parsed["wind_speed_ms"] == pytest.approx(5.3)
    assert parsed["icon_code"] == "04d"


def test_parse_weather_data_handles_missing_fields() -> None:
    """parse_weather_data must not raise when optional fields are absent."""
    parsed = parse_weather_data({})

    assert parsed["temperature_celsius"] is None
    assert parsed["feels_like_celsius"] is None
    assert parsed["humidity_percent"] is None
    assert parsed["condition"] is None
    assert parsed["description"] is None
    assert parsed["wind_speed_ms"] is None
    assert parsed["icon_code"] is None


def test_parse_weather_data_handles_empty_weather_list() -> None:
    data = {**OWM_RESPONSE, "weather": []}
    parsed = parse_weather_data(data)
    assert parsed["condition"] is None
    assert parsed["icon_code"] is None


# ------------------------------------------------------------------
# WeatherService.get_current — valid cache hit
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_returns_cached_when_valid() -> None:
    """If the cache is not expired, no HTTP fetch should occur."""
    from app.weather.service import WeatherService

    now = datetime.now(UTC)
    mock_cache = MagicMock()
    mock_cache.location_key = "52.52,13.405"
    mock_cache.temperature_celsius = 12.4
    mock_cache.feels_like_celsius = 10.1
    mock_cache.humidity_percent = 72
    mock_cache.condition = "Clouds"
    mock_cache.description = "überwiegend bewölkt"
    mock_cache.wind_speed_ms = 5.3
    mock_cache.icon_code = "04d"
    mock_cache.fetched_at = now - timedelta(minutes=5)
    mock_cache.expires_at = now + timedelta(minutes=25)  # still valid

    mock_session = AsyncMock()

    service = WeatherService(mock_session)
    service._get_cache = AsyncMock(return_value=mock_cache)  # type: ignore[method-assign]

    with patch("app.weather.service.fetch_current_weather") as mock_fetch:
        result = await service.get_current()

    # Fetch should NOT have been called — cache is valid
    mock_fetch.assert_not_called()
    assert result is not None
    assert result.condition == "Clouds"
    assert result.temperature_celsius == pytest.approx(12.4)


@pytest.mark.asyncio
async def test_get_current_fetches_when_cache_expired() -> None:
    """When the cache is expired, a fresh fetch should be performed."""
    from app.weather.service import WeatherService

    now = datetime.now(UTC)
    mock_cache = MagicMock()
    mock_cache.expires_at = now - timedelta(minutes=5)  # expired

    mock_session = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    service = WeatherService(mock_session)
    service._get_cache = AsyncMock(return_value=mock_cache)  # type: ignore[method-assign]

    with (
        patch("app.weather.service.fetch_current_weather", new_callable=AsyncMock) as mock_fetch,
        patch("app.weather.service.parse_weather_data") as mock_parse,
        patch("app.weather.service.settings") as mock_settings,
    ):
        mock_settings.openweathermap_api_key = "test-key"
        mock_settings.weather_location_lat = 52.52
        mock_settings.weather_location_lon = 13.405
        mock_fetch.return_value = OWM_RESPONSE
        mock_parse.return_value = {
            "temperature_celsius": 12.4,
            "feels_like_celsius": 10.1,
            "humidity_percent": 72,
            "condition": "Clouds",
            "description": "überwiegend bewölkt",
            "wind_speed_ms": 5.3,
            "icon_code": "04d",
        }
        mock_session.refresh.side_effect = lambda obj: None

        with patch(
            "app.weather.schemas.WeatherRead.model_validate",
            return_value=MagicMock(condition="Clouds"),
        ):
            await service.get_current()

        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_returns_none_without_api_key() -> None:
    """When no API key is set, get_current should return None gracefully."""
    from app.weather.service import WeatherService

    mock_session = AsyncMock()
    service = WeatherService(mock_session)
    service._get_cache = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with patch("app.weather.service.settings") as mock_settings:
        mock_settings.openweathermap_api_key = ""
        mock_settings.weather_location_lat = 52.52
        mock_settings.weather_location_lon = 13.405
        result = await service.get_current()

    assert result is None


# ------------------------------------------------------------------
# WeatherService._is_valid
# ------------------------------------------------------------------


def test_is_valid_returns_true_for_fresh_cache() -> None:
    from app.weather.service import WeatherService

    cache = MagicMock()
    cache.expires_at = datetime.now(UTC) + timedelta(minutes=10)
    assert WeatherService._is_valid(cache) is True


def test_is_valid_returns_false_for_expired_cache() -> None:
    from app.weather.service import WeatherService

    cache = MagicMock()
    cache.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert WeatherService._is_valid(cache) is False
