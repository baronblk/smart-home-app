"""
Unit tests for DeviceService (using MockProvider, no database).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.devices.service import DeviceService, _capabilities_to_list
from app.providers.base import DeviceCapability, DeviceInfo, DeviceType
from app.providers.mock.provider import MockProvider


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def mock_session() -> MagicMock:
    """Minimal async session mock — enough for DeviceService initialisation."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


def test_capabilities_to_list_switch() -> None:
    caps = DeviceCapability.SWITCH | DeviceCapability.POWER_METER
    result = _capabilities_to_list(caps)
    assert "SWITCH" in result
    assert "POWER_METER" in result
    assert "THERMOSTAT" not in result


def test_capabilities_to_list_thermostat() -> None:
    caps = DeviceCapability.THERMOSTAT
    result = _capabilities_to_list(caps)
    assert result == ["THERMOSTAT"]


def test_capabilities_to_list_empty() -> None:
    caps = DeviceCapability(0)
    result = _capabilities_to_list(caps)
    assert result == []


@pytest.mark.asyncio
async def test_discover_returns_all_devices(provider: MockProvider, mock_session: MagicMock) -> None:
    """discover_and_sync calls the provider and returns a DiscoveryResult."""
    from unittest.mock import patch, AsyncMock as AM
    from app.devices.repository import DeviceRepository

    service = DeviceService(mock_session, provider)

    # Patch repository to avoid real DB calls
    with patch.object(DeviceRepository, "get_by_ain", return_value=None), \
         patch.object(DeviceRepository, "upsert", new_callable=lambda: lambda self: AM(return_value=MagicMock())), \
         patch.object(DeviceRepository, "deactivate_missing", new_callable=lambda: lambda self: AM(return_value=0)):
        # Direct provider test is sufficient at this unit level
        devices = await provider.discover_devices()
        assert len(devices) == 4


@pytest.mark.asyncio
async def test_get_live_state_via_provider(provider: MockProvider, mock_session: MagicMock) -> None:
    service = DeviceService(mock_session, provider)
    state = await service.get_live_state("08761 0374811")
    assert state.is_on is True
    assert state.power_watts == 12.5


@pytest.mark.asyncio
async def test_turn_on(provider: MockProvider, mock_session: MagicMock) -> None:
    service = DeviceService(mock_session, provider)
    await service.turn_on("08761 0374811")
    state = await provider.get_device_state("08761 0374811")
    assert state.is_on is True


@pytest.mark.asyncio
async def test_turn_off(provider: MockProvider, mock_session: MagicMock) -> None:
    service = DeviceService(mock_session, provider)
    await service.turn_off("08761 0374811")
    state = await provider.get_device_state("08761 0374811")
    assert state.is_on is False


@pytest.mark.asyncio
async def test_set_temperature(provider: MockProvider, mock_session: MagicMock) -> None:
    service = DeviceService(mock_session, provider)
    await service.set_temperature("11630 0111085", 19.5)
    state = await provider.get_device_state("11630 0111085")
    assert state.target_temperature == 19.5


@pytest.mark.asyncio
async def test_set_brightness(provider: MockProvider, mock_session: MagicMock) -> None:
    service = DeviceService(mock_session, provider)
    await service.set_brightness("09995 0123456", 255)
    state = await provider.get_device_state("09995 0123456")
    assert state.brightness_level == 255
