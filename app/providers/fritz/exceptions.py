"""
Fritz-specific exception mapping.

Maps fritzconnection errors to application-level exceptions so
that the service layer never imports fritzconnection exceptions.
"""
from app.exceptions import (
    DeviceCommandError,
    DeviceNotFoundError,
    ProviderAuthError,
    ProviderConnectionError,
)


def map_fritz_error(exc: Exception, ain: str = "") -> Exception:
    """
    Convert a fritzconnection exception to an application exception.

    This function is called inside FritzProvider/FritzAdapter methods
    to keep fritzconnection errors from leaking into the service layer.
    """
    exc_name = type(exc).__name__
    exc_str = str(exc).lower()

    if "authentication" in exc_str or "auth" in exc_str or "login" in exc_str:
        return ProviderAuthError(f"FRITZ!Box authentication failed: {exc}")

    if "connection" in exc_str or "refused" in exc_str or "timeout" in exc_str:
        return ProviderConnectionError(f"Cannot reach FRITZ!Box: {exc}")

    if "not found" in exc_str or "unknown" in exc_str:
        return DeviceNotFoundError(ain)

    # Generic fallback for AHA command errors
    return DeviceCommandError(f"Fritz device command failed ({exc_name}): {exc}")
