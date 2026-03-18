"""
Fritz device adapter — per-device AHA command wrappers.

Uses fritzconnection's FritzHomeAutomation (TR-064) for switch commands
and FritzConnection.call_http() (AHA-HTTP interface) for thermostat,
power meter, and dimmer operations.

All exceptions are caught and re-raised as application exceptions
via fritz/exceptions.py.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from functools import partial
from typing import Any

from app.providers.base import DeviceCapability, DeviceState
from app.providers.fritz.exceptions import map_fritz_error


class FritzAdapter:
    """
    Wraps fritzconnection's FritzHomeAutomation instance with async wrappers.

    fritzconnection is synchronous, so all calls are executed in a
    thread pool via asyncio.get_event_loop().run_in_executor().
    """

    def __init__(self, fha: Any) -> None:
        """
        Args:
            fha: FritzHomeAutomation instance (has .fc for FritzConnection)
        """
        self._fha = fha
        self._loop = asyncio.get_event_loop()

    async def _run(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a synchronous fritzconnection call in a thread pool."""
        return await self._loop.run_in_executor(None, partial(func, *args, **kwargs))

    def _call_http(self, command: str, ain: str, **kwargs: Any) -> str:
        """
        Synchronous AHA-HTTP interface call.
        Returns the content string from the response.
        """
        result = self._fha.fc.call_http(command, ain, **kwargs)
        return str(result.get("content", "")).strip()

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
                raw = await self._run(self._call_http, "getswitchstate", ain)
                is_on = raw == "1"

            if DeviceCapability.THERMOSTAT in capabilities:
                raw_temp = await self._run(self._call_http, "gettemperature", ain)
                if raw_temp:
                    temperature_celsius = float(raw_temp) / 10.0

                raw_target = await self._run(self._call_http, "gethkrtsoll", ain)
                if raw_target:
                    val = int(raw_target)
                    if val == 253:
                        target_temperature = 0.0  # OFF
                    elif val == 254:
                        target_temperature = 32.0  # ON/boost
                    else:
                        target_temperature = val / 2.0

            if DeviceCapability.POWER_METER in capabilities:
                raw_power = await self._run(self._call_http, "getswitchpower", ain)
                if raw_power:
                    power_watts = float(raw_power) / 1000.0  # mW -> W

                raw_energy = await self._run(self._call_http, "getswitchenergy", ain)
                if raw_energy:
                    energy_wh = float(raw_energy)  # Wh

            if DeviceCapability.DIMMER in capabilities:
                raw_level = await self._run(self._call_http, "getlevel", ain)
                if raw_level:
                    brightness_level = int(raw_level)  # 0-255

            return DeviceState(
                ain=ain,
                is_on=is_on,
                temperature_celsius=temperature_celsius,
                target_temperature=target_temperature,
                power_watts=power_watts,
                energy_wh=energy_wh,
                brightness_level=brightness_level,
                last_updated=datetime.now(UTC),
            )
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_switch(self, ain: str, on: bool) -> None:
        try:
            cmd = "setswitchon" if on else "setswitchoff"
            await self._run(self._call_http, cmd, ain)
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_temperature(self, ain: str, celsius: float) -> None:
        try:
            if celsius == 0:
                param = 253  # OFF
            elif celsius >= 32:
                param = 254  # Boost
            else:
                param = int(celsius * 2)  # half-degree steps
            await self._run(self._call_http, "sethkrtsoll", ain, param=str(param))
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc

    async def set_dimmer(self, ain: str, level: int) -> None:
        try:
            await self._run(self._call_http, "setlevel", ain, level=str(level))
        except Exception as exc:
            raise map_fritz_error(exc, ain) from exc
