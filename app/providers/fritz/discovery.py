"""
AHA device discovery — parses fritzconnection device objects
into the provider's DeviceInfo data transfer objects.

This module is the only place that imports fritzconnection types.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.providers.base import DeviceCapability, DeviceInfo, DeviceType

if TYPE_CHECKING:
    # fritzconnection types — only imported for type checking,
    # never at runtime in the service layer.
    pass


def parse_device_info(device: object) -> DeviceInfo:
    """
    Convert a fritzconnection device object into a DeviceInfo DTO.

    The device object is an instance of fritzconnection's internal
    device class returned by FritzHome.get_device_list().
    """
    ain: str = getattr(device, "ain", "").strip()
    name: str = getattr(device, "name", "Unknown")
    is_present: bool = bool(getattr(device, "present", False))
    firmware: str | None = getattr(device, "fw_version", None)

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
    """Detect which capabilities a device supports."""
    capabilities = DeviceCapability(0)

    # fritzconnection exposes has_switch, has_thermostat, etc.
    if getattr(device, "has_switch", False):
        capabilities |= DeviceCapability.SWITCH
    if getattr(device, "has_thermostat", False):
        capabilities |= DeviceCapability.THERMOSTAT
    if getattr(device, "has_level_control", False):
        capabilities |= DeviceCapability.DIMMER
    if getattr(device, "has_powermeter", False):
        capabilities |= DeviceCapability.POWER_METER

    return capabilities


def _infer_device_type(
    capabilities: DeviceCapability, device: object
) -> DeviceType:
    """Infer the logical device type from capabilities."""
    if DeviceCapability.THERMOSTAT in capabilities:
        return DeviceType.THERMOSTAT
    if DeviceCapability.DIMMER in capabilities:
        return DeviceType.LIGHT
    if DeviceCapability.SWITCH in capabilities:
        return DeviceType.SWITCH
    return DeviceType.UNKNOWN
