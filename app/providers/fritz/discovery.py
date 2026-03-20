"""
AHA device discovery — parses fritzconnection device objects
into the provider's DeviceInfo data transfer objects.

This module is the only place that imports fritzconnection types.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.providers.base import DeviceCapability, DeviceInfo, DeviceType

if TYPE_CHECKING:
    # fritzconnection types — only imported for type checking,
    # never at runtime in the service layer.
    pass

logger = logging.getLogger(__name__)


def is_fritz_group_ain(ain: str) -> bool:
    """Return True for AINs that belong to FRITZ!Box virtual switch groups (Schaltgruppen).

    Virtual groups have AINs prefixed with 'grp' (case-insensitive), e.g. 'grp97E48000'.
    Physical devices — both native FRITZ!DECT (numeric) and third-party gateway devices
    (hex/alphanumeric like 'Z28DBA7FFFE6000D0') — must NOT be filtered out.

    The FRITZ!Box AHA API (getdevicelistinfos) returns BOTH physical devices
    (<device> elements) and virtual groups (<group> elements) in the same list.
    Virtual groups have the same DeviceName as the physical devices they wrap,
    causing apparent duplicates in the UI. We must skip them.

    Reference: FRITZ!Box AHA HTTP Interface specification, AIN format.
    """
    stripped = ain.strip()
    if not stripped:
        return True  # Empty AIN is invalid — skip it
    return stripped.lower().startswith("grp")


def parse_device_info(device: object) -> DeviceInfo | None:
    """
    Convert a fritzconnection HomeAutomationDevice into a DeviceInfo DTO.

    Returns None if the device is a FRITZ!Box virtual group (Schaltgruppe)
    and should be skipped during discovery.

    The device object is returned by FritzHomeAutomation.get_homeautomation_devices().
    It has attributes: AIN, DeviceName, ProductName, Manufacturer, FunctionBitMask,
    and is_* property helpers for capability detection.
    """
    ain: str = (getattr(device, "AIN", "") or "").strip()

    if is_fritz_group_ain(ain):
        raw_name = getattr(device, "DeviceName", None) or getattr(device, "ProductName", ain)
        logger.debug(
            "Skipping FRITZ!Box virtual group during discovery: AIN=%r name=%r",
            ain,
            raw_name,
        )
        return None

    raw_name = getattr(device, "DeviceName", None) or getattr(device, "ProductName", "Unknown")
    name: str = str(raw_name)
    # FritzHomeAutomation devices are present if returned; check SwitchState etc. for online
    is_present: bool = True
    firmware: str | None = getattr(device, "FirmwareVersion", None) or None

    capabilities = _parse_capabilities(device)
    device_type = _infer_device_type(capabilities, device)

    return DeviceInfo(
        ain=ain,
        name=name,
        device_type=device_type,
        capabilities=capabilities,
        is_present=is_present,
        firmware_version=firmware,
    )


def _parse_capabilities(device: object) -> DeviceCapability:
    """Detect which capabilities a device supports via is_* properties."""
    capabilities = DeviceCapability(0)

    # fritzconnection 1.14+ exposes is_switchable, is_radiator_control, etc.
    if getattr(device, "is_switchable", False) or getattr(device, "is_pluggable", False):
        capabilities |= DeviceCapability.SWITCH
    if getattr(device, "is_radiator_control", False):
        capabilities |= DeviceCapability.THERMOSTAT
    if getattr(device, "is_adjustable", False) or getattr(device, "is_bulb", False):
        capabilities |= DeviceCapability.DIMMER
    if getattr(device, "is_energy_sensor", False):
        capabilities |= DeviceCapability.POWER_METER

    return capabilities


def _infer_device_type(capabilities: DeviceCapability, device: object) -> DeviceType:
    """Infer the logical device type from capabilities."""
    if DeviceCapability.THERMOSTAT in capabilities:
        return DeviceType.THERMOSTAT
    if DeviceCapability.DIMMER in capabilities:
        return DeviceType.LIGHT
    if DeviceCapability.SWITCH in capabilities:
        return DeviceType.SWITCH
    return DeviceType.UNKNOWN
