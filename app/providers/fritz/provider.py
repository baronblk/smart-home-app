"""
FritzProvider — implements BaseProvider using fritzconnection 1.14+.

Uses FritzHomeAutomation (TR-064) for device discovery and switch control,
and FritzConnection.call_http() (AHA-HTTP interface) for thermostat,
power meter, and dimmer commands.

This is the only module (besides fritz/adapter.py, fritz/discovery.py,
fritz/exceptions.py) that is allowed to import fritzconnection.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

from app.config import settings
from app.providers.base import BaseProvider, DeviceCapability, DeviceInfo, DeviceState
from app.providers.fritz.adapter import FritzAdapter
from app.providers.fritz.discovery import parse_device_info
from app.providers.fritz.exceptions import map_fritz_error

logger = logging.getLogger(__name__)


class FritzProvider(BaseProvider):
    """
    Connects to a FRITZ!Box via fritzconnection.

    fritzconnection is synchronous. All calls are run in a thread pool
    via asyncio.run_in_executor to avoid blocking the event loop.
    """

    _instance: FritzProvider | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._fha: Any | None = None  # FritzHomeAutomation instance
        self._adapter: FritzAdapter | None = None
        self._device_capabilities: dict[str, DeviceCapability] = {}

    @classmethod
    def get_instance(cls) -> FritzProvider:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ensure_connected(self) -> None:
        """Lazily initialise the fritzconnection FritzHomeAutomation instance."""
        if self._fha is not None:
            return

        async with self._lock:
            if self._fha is not None:
                return

            loop = asyncio.get_event_loop()
            try:
                from fritzconnection.lib.fritzhomeauto import FritzHomeAutomation

                fha = await loop.run_in_executor(
                    None,
                    partial(
                        FritzHomeAutomation,
                        address=settings.fritz_host,
                        user=settings.fritz_username,
                        password=settings.fritz_password,
                        use_tls=False,
                    ),
                )
                self._fha = fha
                self._adapter = FritzAdapter(fha)
                logger.info("Connected to FRITZ!Box at %s", settings.fritz_host)
            except Exception as exc:
                raise map_fritz_error(exc) from exc

    async def discover_devices(self) -> list[DeviceInfo]:
        await self._ensure_connected()
        loop = asyncio.get_event_loop()
        try:
            fha = self._fha
            assert fha is not None
            # Get list of HomeAutomationDevice objects
            devices_raw = await loop.run_in_executor(
                None,
                fha.get_homeautomation_devices,
            )
            result = []
            for device in devices_raw:
                info = parse_device_info(device)
                self._device_capabilities[info.ain] = info.capabilities
                result.append(info)
            return result
        except Exception as exc:
            raise map_fritz_error(exc) from exc

    async def get_device_state(self, ain: str) -> DeviceState:
        await self._ensure_connected()
        assert self._adapter is not None
        capabilities = self._device_capabilities.get(ain)
        if capabilities is None:
            await self.discover_devices()
            capabilities = self._device_capabilities.get(ain)
            if capabilities is None:
                from app.exceptions import DeviceNotFoundError

                raise DeviceNotFoundError(ain)
        return await self._adapter.get_state(ain, capabilities)

    async def set_switch(self, ain: str, on: bool) -> None:
        await self._ensure_connected()
        assert self._adapter is not None
        await self._adapter.set_switch(ain, on)

    async def set_temperature(self, ain: str, celsius: float) -> None:
        await self._ensure_connected()
        assert self._adapter is not None
        await self._adapter.set_temperature(ain, celsius)

    async def set_dimmer(self, ain: str, level: int) -> None:
        await self._ensure_connected()
        assert self._adapter is not None
        await self._adapter.set_dimmer(ain, level)

    async def health_check(self) -> bool:
        try:
            await self._ensure_connected()
            return True
        except Exception:
            return False
