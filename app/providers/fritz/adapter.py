"""
Fritz device adapter — per-device AHA command wrappers.

Centralises all direct fritzconnection AHA API calls in one place.
All exceptions are caught and re-raised as application exceptions
via fritz/exceptions.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial
from typing import TYPE_CHECKING

from app.providers.base import DeviceCapability, DeviceState
from app.providers.fritz.exceptions import map_fritz_error

if TYPE_CHECKING:
    pass  # fritzconnection types are imported at runtime below


class FritzAdapter:
    """
    Wraps fritzconnection's FritzHome instance with async wrappers.

    fritzconnection is synchronous, so all calls are executed in a
    thread pool via asyncio.get_event_loop().run_in_executor().
    """

    def __init__(self, fritz_home: object) -> None:
        # fritz_home is a fritzconnection.lib.fritzhome.FritzHome instance
        self._fritz_home = fritz_home
        self._loop = asyncio.get_event_loop()

    async def _run(self, func, *args):  # type: ignore[no-untyped-def]
        """Execute a synchronous fritzconnection call in a thread pool."""
        return await self._loop.run_in_executor(None, partial(func, *args))

    async def get_state(self, ain: str, capabilities: DeviceCapability) -> DeviceState:
        """Build a DeviceState by reading all supported capabilities."""
        try:
            is_on = None
            temperature_celsius = None
            target_temperature = None
            power_watts = None
            energy_wh = None
            brightness_level = None

            if DeviceCapability.SWITCH in capabilities:
                is_on = await self._run(self._fritz_home.get_switch_state, ain)

            if DeviceCapability.THERMOSTAT in capabilities:
                temperature_celsius = await self._run(
                    self._fritz_home.get_temperature, ain
                )
                target_celsius = await self._run(
                    self._fritz_home.get_target_temperature, ain
                )
                target_temperature = target_celsius

            if DeviceCapability.POWER_METER in capabilities:
                power_watts = await self._run(self._fritz_home.get_switch_power, ain)
                energy_wh = await self._run(self._fritz_home.get_switch_energy, ain)

            if DeviceCapability.DIMMER in capabilities:
                raw_level = await self._run(self._fritz_home.get_level_percentage, ain)
                # fritzconnection returns 0-100%, map to 0-255
                brightness_level = int((raw_level or 0) * 2.55) if raw_level is not None else None

            return DeviceState(
                ain=ain,
                is_on=is_on,
                temperature_celsius=temperature_celsius,
                target_temperature=target_temperature,
                power_watts=power_watts,
                energy_wh=energy_wh,
                brightness_level=brightness_level,
                last_updated=datetime.now(timezone.utc),
            )
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_switch(self, ain: str, on: bool) -> None:
        try:
            if on:
                await self._run(self._fritz_home.set_switch_on, ain)
            else:
                await self._run(self._fritz_home.set_switch_off, ain)
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_temperature(self, ain: str, celsius: float) -> None:
        try:
            await self._run(self._fritz_home.set_target_temperature, ain, celsius)
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_dimmer(self, ain: str, level: int) -> None:
        try:
            # Convert 0-255 to 0-100% for fritzconnection
            percentage = int(level / 2.55)
            await self._run(self._fritz_home.set_level_percentage, ain, percentage)
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc
