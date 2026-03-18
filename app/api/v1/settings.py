"""
Settings API — admin-only endpoints for provider and system configuration.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.rbac import Role, require_role
from app.config import settings
from app.users.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- Schemas ----------


class ProviderSettingsRead(BaseModel):
    """Current provider configuration (read-only view, password masked)."""

    fritz_mock_mode: bool
    fritz_host: str
    fritz_username: str
    fritz_password_set: bool = Field(description="True if a password is configured")
    fritz_ssl_verify: bool


class ProviderConnectionTest(BaseModel):
    """Result of a FRITZ!Box connection test."""

    success: bool
    message: str
    device_count: int | None = None


class SystemInfo(BaseModel):
    """General system information for the admin panel."""

    environment: str
    database_url_masked: str
    redis_url: str
    weather_api_configured: bool
    weather_location: str


# ---------- Endpoints ----------


@router.get("/provider", response_model=ProviderSettingsRead)
async def get_provider_settings(
    _current_user: User = Depends(require_role(Role.ADMIN)),
) -> ProviderSettingsRead:
    """Return current FRITZ!Box provider configuration (admin only)."""
    return ProviderSettingsRead(
        fritz_mock_mode=settings.fritz_mock_mode,
        fritz_host=settings.fritz_host,
        fritz_username=settings.fritz_username,
        fritz_password_set=bool(settings.fritz_password),
        fritz_ssl_verify=settings.fritz_ssl_verify,
    )


@router.post("/provider/test", response_model=ProviderConnectionTest)
async def test_provider_connection(
    _current_user: User = Depends(require_role(Role.ADMIN)),
) -> ProviderConnectionTest:
    """
    Test the FRITZ!Box connection with current settings.

    In mock mode, returns a synthetic success response.
    In live mode, attempts to discover devices from the FRITZ!Box.
    """
    from app.dependencies import get_provider

    provider = get_provider()

    try:
        devices = await provider.discover_devices()
        provider_name = type(provider).__name__
        return ProviderConnectionTest(
            success=True,
            message=f"Verbindung erfolgreich ({provider_name}). {len(devices)} Gerät(e) gefunden.",
            device_count=len(devices),
        )
    except Exception as exc:
        logger.warning("Provider connection test failed: %s", exc)
        return ProviderConnectionTest(
            success=False,
            message=f"Verbindung fehlgeschlagen: {exc}",
            device_count=None,
        )


@router.get("/system", response_model=SystemInfo)
async def get_system_info(
    _current_user: User = Depends(require_role(Role.ADMIN)),
) -> dict[str, Any]:
    """Return general system information (admin only)."""
    # Mask the database URL password
    db_url = settings.database_url
    masked_db = _mask_url_password(db_url)

    return {
        "environment": settings.environment,
        "database_url_masked": masked_db,
        "redis_url": settings.redis_url,
        "weather_api_configured": bool(settings.openweathermap_api_key),
        "weather_location": f"{settings.weather_location_lat}, {settings.weather_location_lon}",
    }


def _mask_url_password(url: str) -> str:
    """Replace the password portion of a database URL with ***."""
    try:
        # postgresql+asyncpg://user:password@host:port/db
        if "://" in url and "@" in url:
            prefix, rest = url.split("://", 1)
            userinfo, hostinfo = rest.rsplit("@", 1)
            if ":" in userinfo:
                user, _ = userinfo.split(":", 1)
                return f"{prefix}://{user}:***@{hostinfo}"
        return url
    except Exception:
        return "***"
