"""
Device domain type re-exports.

The domain layer re-exports DeviceType and DeviceCapability from the
provider base so that service/repository code doesn't need to import
from app.providers.base directly.
"""
from app.providers.base import DeviceCapability, DeviceType

__all__ = ["DeviceCapability", "DeviceType"]
