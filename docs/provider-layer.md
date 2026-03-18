# Provider/Adapter Layer

## Purpose

The Provider/Adapter layer is the single integration point between the application and FRITZ!Box hardware. It enforces a hard boundary: **nothing outside `app/providers/` may import `fritzconnection`**.

This isolation enables:
- Full test coverage without physical hardware (via `MockProvider`)
- Clean unit tests for all service layer logic
- Future substitution of the FRITZ!Box integration without touching business logic
- CI pipelines that run entirely in the cloud

---

## Architecture

```
app/
└── providers/
    ├── base.py          ← BaseProvider ABC + data transfer objects
    ├── fritz/
    │   ├── provider.py  ← FritzProvider (real hardware)
    │   ├── adapter.py   ← Per-device AHA command wrappers
    │   ├── discovery.py ← AHA device list XML parsing
    │   └── exceptions.py← Maps fritzconnection errors to app exceptions
    └── mock/
        └── provider.py  ← MockProvider (in-memory, for tests and dev)
```

---

## BaseProvider Interface (`app/providers/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import auto, Flag, StrEnum

class DeviceType(StrEnum):
    THERMOSTAT = "thermostat"
    SWITCH     = "switch"
    LIGHT      = "light"
    UNKNOWN    = "unknown"

class DeviceCapability(Flag):
    SWITCH      = auto()
    THERMOSTAT  = auto()
    DIMMER      = auto()
    POWER_METER = auto()

@dataclass(frozen=True)
class DeviceInfo:
    ain: str                           # AVM AIN identifier
    name: str
    device_type: DeviceType
    capabilities: DeviceCapability
    is_present: bool
    firmware_version: str | None = None

@dataclass
class DeviceState:
    ain: str
    is_on: bool | None                 # None if no switch capability
    temperature_celsius: float | None
    target_temperature: float | None
    power_watts: float | None
    energy_wh: float | None
    brightness_level: int | None       # 0-255, None if not dimmable
    last_updated: datetime

class BaseProvider(ABC):

    @abstractmethod
    async def discover_devices(self) -> list[DeviceInfo]: ...

    @abstractmethod
    async def get_device_state(self, ain: str) -> DeviceState: ...

    @abstractmethod
    async def set_switch(self, ain: str, on: bool) -> None: ...

    @abstractmethod
    async def set_temperature(self, ain: str, celsius: float) -> None: ...

    @abstractmethod
    async def set_dimmer(self, ain: str, level: int) -> None: ...
```

---

## FritzProvider (`app/providers/fritz/provider.py`)

Implements `BaseProvider` using `fritzconnection`.

- Connects to the FRITZ!Box at startup using `settings.FRITZ_HOST`, `FRITZ_USERNAME`, `FRITZ_PASSWORD`
- `discover_devices()` calls `FritzHome.get_device_list()` and delegates XML parsing to `discovery.py`
- All AHA commands are wrapped in `FritzAdapter` methods to centralize error handling
- Fritz-specific exceptions are caught in `exceptions.py` and re-raised as application-level exceptions

Connection is established lazily on first use and cached as a singleton for the application lifetime.

---

## MockProvider (`app/providers/mock/provider.py`)

Used when `settings.FRITZ_MOCK_MODE = True`.

- Loads device list from `tests/fixtures/fritz_mock_data.json` at startup
- Maintains an in-memory state dict for device states
- `set_switch()`, `set_temperature()`, `set_dimmer()` update the in-memory dict
- Fully deterministic — enables reproducible unit and integration tests

---

## Provider Selection (Dependency Injection)

The active provider is injected via FastAPI's `Depends()` system in `app/dependencies.py`:

```python
from app.providers.base import BaseProvider
from app.providers.fritz.provider import FritzProvider
from app.providers.mock.provider import MockProvider
from app.config import settings

def get_provider() -> BaseProvider:
    if settings.FRITZ_MOCK_MODE:
        return MockProvider.get_instance()
    return FritzProvider.get_instance()
```

Route handlers declare the dependency:
```python
@router.post("/devices/{ain}/on")
async def turn_on(ain: str, provider: BaseProvider = Depends(get_provider)):
    await provider.set_switch(ain, on=True)
```

---

## Adding a New Provider

To support a different smart home system (e.g., Home Assistant, Tuya):

1. Create `app/providers/<name>/provider.py`
2. Implement all abstract methods from `BaseProvider`
3. Add a new condition in `get_provider()` in `app/dependencies.py`
4. Add the corresponding environment variable to `.env.example`

No other code in the application needs to change.

---

## Error Handling

Fritz-specific errors in `app/providers/fritz/exceptions.py` are mapped to application exceptions:

| Fritz Error | App Exception |
|-------------|--------------|
| Connection refused / timeout | `ProviderConnectionError` |
| Authentication failure | `ProviderAuthError` |
| Device not found | `DeviceNotFoundError` |
| AHA command failed | `DeviceCommandError` |

These exceptions are handled by FastAPI exception handlers registered in `app/exceptions.py` and return appropriate HTTP status codes.
