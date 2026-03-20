"""
Unit tests for fritz/discovery.py — specifically the virtual group filter.

Root-cause context: FritzHomeAutomation.get_homeautomation_devices() returns
BOTH physical FRITZ!DECT devices (numeric AINs) and FRITZ!Box virtual groups
/ Schaltgruppen (AINs starting with "grp"). The latter were being stored as
real Device records, causing duplicate names in the UI.

Third-party devices connected via FRITZ!Smart Gateway use hex/alphanumeric
AINs (e.g. "Z28DBA7FFFE6000D0") and must NOT be filtered out — only AINs
starting with "grp" (case-insensitive) are virtual groups.

These tests ensure the filter correctly separates physical devices from virtual
groups across all known AIN formats.
"""

import pytest

from app.providers.base import DeviceType
from app.providers.fritz.discovery import is_fritz_group_ain, parse_device_info

# ---------------------------------------------------------------------------
# is_fritz_group_ain — unit tests for the AIN classifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ain, expected",
    [
        # Physical FRITZ!DECT device AINs (purely numeric with optional space)
        ("12345 678901", False),
        ("087610006405", False),
        ("16572 0185715", False),
        ("123456789012", False),
        ("99999 999999", False),
        # Third-party / gateway devices (hex/alphanumeric) — NOT groups
        ("Z28DBA7FFFE6000D0", False),  # IKEA TRETAKT Zigbee plug via FRITZ!Smart Gateway
        ("Z28DBA7FFFE6000D1", False),  # another gateway device
        ("AABBCCDDEEFF0011", False),  # generic hex AIN — NOT a group
        # FRITZ!Box virtual group / Schaltgruppe AINs (start with "grp")
        ("grp97E48000", True),
        ("grp-1A2B3C4D", True),
        ("GRP12345678", True),  # uppercase variant
        ("grpABCD1234", True),
        ("grp00000000", True),
        # Edge cases
        ("", True),  # empty → treat as invalid / skip
        ("   ", True),  # whitespace-only → skip
        ("12 34 56", False),  # spaces inside numeric → still physical device
    ],
)
def test_is_fritz_group_ain(ain: str, expected: bool) -> None:
    assert is_fritz_group_ain(ain) == expected, f"is_fritz_group_ain({ain!r}) should be {expected}"


# ---------------------------------------------------------------------------
# parse_device_info — must return None for virtual groups
# ---------------------------------------------------------------------------


class _FakeDevice:
    """Minimal stand-in for a fritzconnection HomeAutomationDevice."""

    def __init__(self, ain: str, name: str = "Test Device") -> None:
        self.AIN = ain
        self.DeviceName = name
        self.FirmwareVersion = "1.0"
        self.is_switchable = True
        self.is_pluggable = False
        self.is_radiator_control = False
        self.is_adjustable = False
        self.is_bulb = False
        self.is_energy_sensor = False


def test_parse_device_info_skips_group_ain() -> None:
    """parse_device_info returns None for FRITZ!Box virtual group AINs."""
    device = _FakeDevice(ain="grp97E48000", name="Fenstersensor Wohnzimmer")
    result = parse_device_info(device)
    assert result is None, "Virtual group AIN must return None"


def test_parse_device_info_skips_empty_ain() -> None:
    """parse_device_info returns None when AIN is empty."""
    device = _FakeDevice(ain="", name="Mystery Device")
    result = parse_device_info(device)
    assert result is None, "Empty AIN must return None"


def test_parse_device_info_returns_physical_device() -> None:
    """parse_device_info returns DeviceInfo for a valid numeric AIN."""
    device = _FakeDevice(ain="12345 678901", name="Fenstersensor Wohnzimmer")
    result = parse_device_info(device)
    assert result is not None, "Physical device must NOT be filtered out"
    assert result.ain == "12345 678901"
    assert result.name == "Fenstersensor Wohnzimmer"
    assert result.device_type == DeviceType.SWITCH  # is_switchable=True


def test_parse_device_info_returns_gateway_device() -> None:
    """parse_device_info returns DeviceInfo for a third-party gateway device with hex AIN."""
    device = _FakeDevice(ain="Z28DBA7FFFE6000D0", name="SmartPlug Stehlampe")
    result = parse_device_info(device)
    assert result is not None, "Third-party gateway device must NOT be filtered out"
    assert result.ain == "Z28DBA7FFFE6000D0"
    assert result.name == "SmartPlug Stehlampe"
    assert result.device_type == DeviceType.SWITCH  # is_switchable=True


def test_parse_device_info_sensor_no_capabilities() -> None:
    """A read-only sensor (no switch/thermostat/dimmer/power) is UNKNOWN type but valid."""

    class _SensorDevice(_FakeDevice):
        def __init__(self, ain: str, name: str = "Test Device") -> None:
            super().__init__(ain=ain, name=name)
            # Override instance attributes set by base __init__
            self.is_switchable = False
            self.is_pluggable = False
            self.is_radiator_control = False
            self.is_adjustable = False
            self.is_bulb = False
            self.is_energy_sensor = False

    device = _SensorDevice(ain="11630 0068574", name="Fenstersensor Arbeitszimmer")
    result = parse_device_info(device)
    assert result is not None, "Read-only sensor with valid AIN must NOT be filtered"
    assert result.ain == "11630 0068574"
    assert result.device_type == DeviceType.UNKNOWN


# ---------------------------------------------------------------------------
# Discovery pipeline: physical devices kept, groups dropped
# ---------------------------------------------------------------------------


def test_no_duplicates_after_filtering_groups() -> None:
    """
    Simulates discover_devices() processing a mixed list of physical devices
    and FRITZ!Box virtual groups. After filtering, only physical devices remain.
    """
    raw_devices = [
        _FakeDevice(ain="12345 678901", name="Fenstersensor Wohnzimmer"),  # physical ✓
        _FakeDevice(ain="grp97E48000", name="Fenstersensor Wohnzimmer"),  # virtual ✗
        _FakeDevice(ain="16572 0185715", name="Computer"),  # physical ✓
        _FakeDevice(ain="grp1A2B3C4D", name="Wohnzimmer TV ein/aus"),  # virtual ✗
        _FakeDevice(ain="087610006405", name="FRITZ!DECT 301"),  # physical ✓
    ]

    results = [parse_device_info(d) for d in raw_devices]
    physical = [r for r in results if r is not None]

    assert len(physical) == 3, f"Expected 3 physical devices, got {len(physical)}"
    ains = [d.ain for d in physical]
    assert "12345 678901" in ains
    assert "16572 0185715" in ains
    assert "087610006405" in ains
    # No virtual group AINs
    assert not any("grp" in a.lower() for a in ains)
