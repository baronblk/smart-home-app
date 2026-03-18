"""
MockProvider — in-memory BaseProvider implementation for tests and dev mode.

Loads device list from tests/fixtures/fritz_mock_data.json.
Maintains stateful in-memory device states — set_switch(), set_temperature(),
and set_dimmer() all update the in-memory state, making tests deterministic.

Usage: set FRITZ_MOCK_MODE=true in .env.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.exceptions import DeviceCommandError, DeviceNotFoundError
from app.providers.base import (
    BaseProvider,
    DeviceCapability,
    DeviceInfo,
    DeviceState,
    DeviceType,
)

logger = logging.getLogger(__name__)

# Path to fixture file (colocated with this module so it works in Docker too)
_FIXTURE_PATH = Path(__file__).parent / "fritz_mock_data.json"

# Legacy path for backward compatibility with test fixtures
_FIXTURE_PATH_LEGACY = (
    Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "fritz_mock_data.json"
)

_CAPABILITY_MAP: dict[str, DeviceCapability] = {
    "SWITCH": DeviceCapability.SWITCH,
    "THERMOSTAT": DeviceCapability.THERMOSTAT,
    "DIMMER": DeviceCapability.DIMMER,
    "POWER_METER": DeviceCapability.POWER_METER,
}

_DEVICE_TYPE_MAP: dict[str, DeviceType] = {
    "thermostat": DeviceType.THERMOSTAT,
    "switch": DeviceType.SWITCH,
    "light": DeviceType.LIGHT,
    "unknown": DeviceType.UNKNOWN,
}


class MockProvider(BaseProvider):
    """
    Deterministic in-memory provider for testing and development.

    Not a singleton — each test can create its own instance with a
    fresh state by calling MockProvider() directly.
    For application-wide use, call MockProvider.get_instance().
    """

    _instance: MockProvider | None = None

    def __init__(self, fixture_path: Path | None = None) -> None:
        if fixture_path is None:
            # Try colocated file first (Docker), fall back to tests/ (local dev)
            fixture_path = _FIXTURE_PATH if _FIXTURE_PATH.exists() else _FIXTURE_PATH_LEGACY
        data = json.loads(fixture_path.read_text())
        self._devices: dict[str, DeviceInfo] = {}
        self._states: dict[str, dict[str, Any]] = {}

        for d in data["devices"]:
            caps = DeviceCapability(0)
            for cap_str in d["capabilities"]:
                if cap_str in _CAPABILITY_MAP:
                    caps |= _CAPABILITY_MAP[cap_str]

            info = DeviceInfo(
                ain=d["ain"],
                name=d["name"],
                device_type=_DEVICE_TYPE_MAP.get(d["device_type"], DeviceType.UNKNOWN),
                capabilities=caps,
                is_present=d["is_present"],
                firmware_version=d.get("firmware_version"),
            )
            self._devices[d["ain"]] = info
            self._states[d["ain"]] = deepcopy(d["state"])

        logger.info("MockProvider loaded %d devices from fixture.", len(self._devices))

    @classmethod
    def get_instance(cls) -> MockProvider:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton — use in test teardown."""
        cls._instance = None

    async def discover_devices(self) -> list[DeviceInfo]:
        return list(self._devices.values())

    async def get_device_state(self, ain: str) -> DeviceState:
        if ain not in self._devices:
            raise DeviceNotFoundError(ain)
        s = self._states[ain]
        return DeviceState(
            ain=ain,
            is_on=s.get("is_on"),
            temperature_celsius=s.get("temperature_celsius"),
            target_temperature=s.get("target_temperature"),
            power_watts=s.get("power_watts"),
            energy_wh=s.get("energy_wh"),
            brightness_level=s.get("brightness_level"),
            last_updated=datetime.now(UTC),
        )

    async def set_switch(self, ain: str, on: bool) -> None:
        self._require_device(ain)
        self._require_capability(ain, DeviceCapability.SWITCH)
        self._states[ain]["is_on"] = on

    async def set_temperature(self, ain: str, celsius: float) -> None:
        self._require_device(ain)
        self._require_capability(ain, DeviceCapability.THERMOSTAT)
        if not (8.0 <= celsius <= 28.0) and celsius not in (0, 32):
            raise DeviceCommandError(
                f"Temperature {celsius}°C out of range (8-28, 0=off, 32=boost)."
            )
        self._states[ain]["target_temperature"] = celsius

    async def set_dimmer(self, ain: str, level: int) -> None:
        self._require_device(ain)
        self._require_capability(ain, DeviceCapability.DIMMER)
        if not (0 <= level <= 255):
            raise DeviceCommandError(f"Brightness level {level} out of range (0-255).")
        self._states[ain]["brightness_level"] = level
        self._states[ain]["is_on"] = level > 0

    def _require_device(self, ain: str) -> None:
        if ain not in self._devices:
            raise DeviceNotFoundError(ain)

    def _require_capability(self, ain: str, capability: DeviceCapability) -> None:
        if capability not in self._devices[ain].capabilities:
            raise DeviceCommandError(f"Device {ain} does not support {capability.name}.")
