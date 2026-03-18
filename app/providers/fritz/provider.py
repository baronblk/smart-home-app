"""
FritzProvider — implements BaseProvider using fritzconnection.

This is the only module (besides fritz/adapter.py, fritz/discovery.py,
fritz/exceptions.py) that is allowed to import fritzconnection.

The provider is a singleton: call FritzProvider.get_instance() to
get or create the shared instance. The instance is initialised lazily
on first use.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial

from app.config import settings
from app.providers.base import BaseProvider, DeviceInfo, DeviceState
from app.providers.fritz.adapter import FritzAdapter
from app.providers.fritz.discovery import parse_device_info
from app.providers.fritz.exceptions import map_fritz_error

logger = logging.getLogger(__name__)


class FritzProvider(BaseProvider):
    """
    Connects to a FRITZ!Box via fritzconnection's FritzHome class.

    fritzconnection is synchronous. All calls are run in a thread pool
    via asyncio.run_in_executor to avoid blocking the event loop.
    """

    _instance: FritzProvider | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self) -> None:
        self._fritz_home: object | None = None
        self._adapter: FritzAdapter | None = None
        self._device_capabilities: dict[str, object] = {}

    @classmethod
    def get_instance(cls) -> FritzProvider:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ensure_connected(self) -> None:
        """Lazily initialise the fritzconnection FritzHome instance."""
        if self._fritz_home is not None:
            return

        async with self._lock:
            if self._fritz_home is not None:
                return

            loop = asyncio.get_event_loop()
            try:
                # Import fritzconnection here — the ONLY place in the app
                from fritzconnection.lib.fritzhome import FritzHome

                fritz_home = await loop.run_in_executor(
                    None,
                    partial(
                        FritzHome,
                        address=settings.fritz_host,
                        user=settings.fritz_username,
                        password=settings.fritz_password,
                        use_tls=False,
                    ),
                )
                await loop.run_in_executor(None, fritz_home.login)
                self._fritz_home = fritz_home
                self._adapter = FritzAdapter(fritz_home)
                logger.info("Connected to FRITZ!Box at %s", settings.fritz_host)
            except Exception as exc:
                raise map_fritz_error(exc) from exc

    async def discover_devices(self) -> list[DeviceInfo]:
        await self._ensure_connected()
        loop = asyncio.get_event_loop()
        try:
            fritz_home = self._fritz_home
            devices_raw = await loop.run_in_executor(
                None,
                fritz_home.get_device_list,  # type: ignore[union-attr]
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
            # Fetch capabilities on demand
            await self.discover_devices()
            capabilities = self._device_capabilities.get(ain)
            if capabilities is None:
                from app.exceptions import DeviceNotFoundError

                raise DeviceNotFoundError(ain)
        return await self._adapter.get_state(ain, capabilities)  # type: ignore[arg-type]

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
