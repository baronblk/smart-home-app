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
    Convert a fritzconnection HomeAutomationDevice into a DeviceInfo DTO.

    The device object is returned by FritzHomeAutomation.get_homeautomation_devices().
    It has attributes: AIN, DeviceName, ProductName, Manufacturer, FunctionBitMask,
    and is_* property helpers for capability detection.
    """
    ain: str = (getattr(device, "AIN", "") or "").strip()
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
