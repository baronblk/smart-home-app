"""
HTML page routes — serve Jinja2 templates for the web UI.

These routes detect browser requests (Accept: text/html) and render
full pages. API clients receive JSON from the API routes.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_provider
from app.providers.base import BaseProvider

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("dashboard/index.html", {"request": request})


@router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("devices/index.html", {"request": request})


@router.get("/devices/{ain}", response_class=HTMLResponse)
async def device_detail_page(
    ain: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    provider: BaseProvider = Depends(get_provider),
) -> HTMLResponse:
    """Device detail page with live state, controls, and chart placeholders."""
    from app.devices.service import DeviceService

    service = DeviceService(session, provider)
    device = await service.get_device_by_ain(ain)
    # Try to get live state, fall back to latest snapshot
    state = None
    try:
        state = await service.get_live_state(ain)
    except Exception:
        snapshot = await service.get_latest_snapshot(ain)
        if snapshot:
            state = type(
                "State",
                (),
                {
                    "ain": ain,
                    "is_on": snapshot.is_on,
                    "temperature_celsius": snapshot.temperature_celsius,
                    "target_temperature": snapshot.target_temperature,
                    "power_watts": snapshot.power_watts,
                    "energy_wh": snapshot.energy_wh,
                    "brightness_level": snapshot.brightness_level,
                },
            )()
    return templates.TemplateResponse(
        "devices/detail.html",
        {"request": request, "device": device, "state": state},
    )


@router.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("groups/manage.html", {"request": request})


@router.get("/schedules", response_class=HTMLResponse)
async def schedules_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("schedules/index.html", {"request": request})


@router.get("/automations", response_class=HTMLResponse)
async def automations_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("automations/index.html", {"request": request})


@router.get("/automations/new", response_class=HTMLResponse)
async def automations_builder_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("automations/builder.html", {"request": request})


@router.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("audit/index.html", {"request": request})


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("analytics/index.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("auth/profile.html", {"request": request})


@router.get("/phone", response_class=HTMLResponse)
async def phone_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("phone/index.html", {"request": request})


@router.get("/network", response_class=HTMLResponse)
async def network_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("network/index.html", {"request": request})


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("settings/index.html", {"request": request})


@router.get("/partials/devices/{ain}/state", response_class=HTMLResponse)
async def partials_device_state(
    ain: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    provider: BaseProvider = Depends(get_provider),
) -> HTMLResponse:
    """HTMX partial: renders live device state panel, polled every 10s."""
    from app.devices.service import DeviceService

    service = DeviceService(session, provider)
    device = await service.get_device_by_ain(ain)
    state = None
    try:
        state = await service.get_live_state(ain)
    except Exception:
        snapshot = await service.get_latest_snapshot(ain)
        if snapshot:
            state = type(
                "State",
                (),
                {
                    "ain": ain,
                    "is_on": snapshot.is_on,
                    "temperature_celsius": snapshot.temperature_celsius,
                    "target_temperature": snapshot.target_temperature,
                    "power_watts": snapshot.power_watts,
                    "energy_wh": snapshot.energy_wh,
                    "brightness_level": snapshot.brightness_level,
                },
            )()
    return templates.TemplateResponse(
        "partials/device_state_panel.html",
        {"request": request, "device": device, "state": state},
    )


@router.get("/partials/devices", response_class=HTMLResponse)
async def partials_devices(
    request: Request,
    session: AsyncSession = Depends(get_db),
    provider: BaseProvider = Depends(get_provider),
) -> HTMLResponse:
    """HTMX partial: renders device cards for the dashboard/device grid."""
    from app.devices.service import DeviceService

    service = DeviceService(session, provider)
    devices = await service.list_devices(include_inactive=False)

    # Build cards from DB-cached device data (no live polling for speed)
    cards: list[dict[str, object]] = []
    for device in devices:
        cards.append({"device": device, "state": None})

    return templates.TemplateResponse(
        "partials/device_grid.html",
        {"request": request, "cards": cards},
    )
