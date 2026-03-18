"""
Unit tests for MockProvider.

Tests run without any FRITZ!Box hardware or database.
"""

import pytest

from app.exceptions import DeviceCommandError, DeviceNotFoundError
from app.providers.base import DeviceCapability, DeviceType
from app.providers.mock.provider import MockProvider


@pytest.fixture
def provider() -> MockProvider:
    """Fresh MockProvider instance for each test."""
    return MockProvider()


@pytest.mark.asyncio
async def test_discover_devices_returns_all(provider: MockProvider) -> None:
    devices = await provider.discover_devices()
    assert len(devices) == 4


@pytest.mark.asyncio
async def test_thermostat_device_info(provider: MockProvider) -> None:
    devices = await provider.discover_devices()
    thermostat = next(d for d in devices if d.device_type == DeviceType.THERMOSTAT and d.is_present)
    assert DeviceCapability.THERMOSTAT in thermostat.capabilities
    assert thermostat.is_present is True


@pytest.mark.asyncio
async def test_switch_device_has_power_meter(provider: MockProvider) -> None:
    devices = await provider.discover_devices()
    switch = next(d for d in devices if d.device_type == DeviceType.SWITCH)
    assert DeviceCapability.SWITCH in switch.capabilities
    assert DeviceCapability.POWER_METER in switch.capabilities


@pytest.mark.asyncio
async def test_get_device_state_thermostat(provider: MockProvider) -> None:
    ain = "11630 0111085"
    state = await provider.get_device_state(ain)
    assert state.ain == ain
    assert state.temperature_celsius == 21.5
    assert state.target_temperature == 22.0
    assert state.is_on is None  # No switch capability


@pytest.mark.asyncio
async def test_get_device_state_switch(provider: MockProvider) -> None:
    ain = "08761 0374811"
    state = await provider.get_device_state(ain)
    assert state.is_on is True
    assert state.power_watts == 12.5
    assert state.energy_wh == 4321


@pytest.mark.asyncio
async def test_set_switch_on_and_off(provider: MockProvider) -> None:
    ain = "08761 0374811"
    await provider.set_switch(ain, False)
    state = await provider.get_device_state(ain)
    assert state.is_on is False

    await provider.set_switch(ain, True)
    state = await provider.get_device_state(ain)
    assert state.is_on is True


@pytest.mark.asyncio
async def test_set_temperature(provider: MockProvider) -> None:
    ain = "11630 0111085"
    await provider.set_temperature(ain, 20.0)
    state = await provider.get_device_state(ain)
    assert state.target_temperature == 20.0


@pytest.mark.asyncio
async def test_set_temperature_invalid_range(provider: MockProvider) -> None:
    ain = "11630 0111085"
    with pytest.raises(DeviceCommandError):
        await provider.set_temperature(ain, 50.0)


@pytest.mark.asyncio
async def test_set_dimmer(provider: MockProvider) -> None:
    ain = "09995 0123456"
    await provider.set_dimmer(ain, 200)
    state = await provider.get_device_state(ain)
    assert state.brightness_level == 200
    assert state.is_on is True


@pytest.mark.asyncio
async def test_set_dimmer_to_zero_turns_off(provider: MockProvider) -> None:
    ain = "09995 0123456"
    await provider.set_dimmer(ain, 0)
    state = await provider.get_device_state(ain)
    assert state.brightness_level == 0
    assert state.is_on is False


@pytest.mark.asyncio
async def test_device_not_found(provider: MockProvider) -> None:
    with pytest.raises(DeviceNotFoundError):
        await provider.get_device_state("99999 0000000")


@pytest.mark.asyncio
async def test_switch_command_on_thermostat_raises(provider: MockProvider) -> None:
    """Thermostat has no SWITCH capability."""
    ain = "11630 0111085"
    with pytest.raises(DeviceCommandError):
        await provider.set_switch(ain, True)


@pytest.mark.asyncio
async def test_offline_device_still_discoverable(provider: MockProvider) -> None:
    devices = await provider.discover_devices()
    offline = next(d for d in devices if not d.is_present)
    assert offline.ain == "11630 0222999"
