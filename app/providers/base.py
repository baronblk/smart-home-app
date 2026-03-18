"""
Provider abstraction layer — base classes and data transfer objects.

RULE: Nothing outside app/providers/ may import fritzconnection.

BaseProvider defines the contract that FritzProvider and MockProvider
implement. All device operations in the application go through this
interface, never through fritzconnection directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Flag, StrEnum, auto


class DeviceType(StrEnum):
    THERMOSTAT = "thermostat"
    SWITCH = "switch"
    LIGHT = "light"
    UNKNOWN = "unknown"


class DeviceCapability(Flag):
    """Bitmask of capabilities a device may support."""
    SWITCH = auto()       # Can be turned on/off
    THERMOSTAT = auto()   # Has a thermostat (temperature control)
    DIMMER = auto()       # Supports dimming (brightness control)
    POWER_METER = auto()  # Reports current power consumption + energy


@dataclass(frozen=True)
class DeviceInfo:
    """
    Immutable device descriptor returned by discover_devices().

    This is a pure data transfer object from the provider to the
    service layer. It is NOT a SQLAlchemy model.
    """
    ain: str                              # AVM AIN identifier (unique per device)
    name: str
    device_type: DeviceType
    capabilities: DeviceCapability
    is_present: bool                      # False if device is offline
    firmware_version: str | None = None


@dataclass
class DeviceState:
    """
    Mutable device state snapshot returned by get_device_state().

    None values mean the capability is not supported by this device.
    """
    ain: str
    is_on: bool | None = None             # None if no SWITCH capability
    temperature_celsius: float | None = None   # Current temperature (thermostat)
    target_temperature: float | None = None    # Set-point temperature
    power_watts: float | None = None           # Current power draw (POWER_METER)
    energy_wh: float | None = None             # Total energy consumed (POWER_METER)
    brightness_level: int | None = None        # 0–255, None if not DIMMER
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class BaseProvider(ABC):
    """
    Abstract interface for smart home device providers.

    Implementations must be thread-safe and support concurrent async
    calls. All methods are async because they perform I/O operations.
    """

    @abstractmethod
    async def discover_devices(self) -> list[DeviceInfo]:
        """
        Discover all devices registered on the provider.

        Returns a list of DeviceInfo descriptors. Call this to
        populate or refresh the device list in the database.
        """
        ...

    @abstractmethod
    async def get_device_state(self, ain: str) -> DeviceState:
        """
        Fetch the current state of a device by its AIN.

        Raises DeviceNotFoundError if the AIN is unknown to the provider.
        """
        ...

    @abstractmethod
    async def set_switch(self, ain: str, on: bool) -> None:
        """
        Turn a switchable device on or off.

        Raises DeviceCommandError if the device does not support SWITCH.
        """
        ...

    @abstractmethod
    async def set_temperature(self, ain: str, celsius: float) -> None:
        """
        Set the target temperature on a thermostat device.

        Valid range: 8.0–28.0 °C. 0 = off, 32 = boost mode.
        Raises DeviceCommandError if the device does not support THERMOSTAT.
        """
        ...

    @abstractmethod
    async def set_dimmer(self, ain: str, level: int) -> None:
        """
        Set the brightness level of a dimmable light.

        level: 0 (off) to 255 (full brightness).
        Raises DeviceCommandError if the device does not support DIMMER.
        """
        ...

    async def health_check(self) -> bool:
        """Return True if the provider backend is reachable. Default: True."""
        return True
