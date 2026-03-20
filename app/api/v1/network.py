"""
Network API — DSL status, WLAN networks, connected hosts (JSON + HTMX partials).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.network.service import NetworkService

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/status")
async def network_status() -> dict[str, Any]:
    """Return DSL/WAN connection status as JSON."""
    svc = NetworkService()
    return await svc.get_dsl_status()


@router.get("/wlan")
async def network_wlan() -> list[dict[str, Any]]:
    """Return WLAN network list as JSON."""
    svc = NetworkService()
    return await svc.get_wlan_networks()


@router.get("/hosts")
async def network_hosts(
    active_only: bool = Query(default=False),
) -> list[dict[str, Any]]:
    """Return host list as JSON."""
    svc = NetworkService()
    return await svc.get_hosts(active_only=active_only)


@router.get("/partials/status", response_class=HTMLResponse)
async def partials_network_status(request: Request) -> HTMLResponse:
    """HTMX partial — DSL status card content."""
    svc = NetworkService()
    status = await svc.get_dsl_status()
    return templates.TemplateResponse(
        "partials/network_status.html",
        {"request": request, "status": status},
    )


@router.get("/partials/hosts", response_class=HTMLResponse)
async def partials_hosts(
    request: Request,
    active_only: bool = Query(default=False),
) -> HTMLResponse:
    """HTMX partial — host table rows."""
    svc = NetworkService()
    # Fetch hosts and WLAN concurrently — both are cached independently,
    # so on a cache hit both return in <5 ms; on a miss the two slow
    # FRITZ!Box calls run in parallel instead of sequentially.
    hosts, wlan = await asyncio.gather(
        svc.get_hosts(active_only=active_only),
        svc.get_wlan_networks(),
    )
    total_wlan_clients = sum(n.get("client_count", 0) for n in wlan)
    return templates.TemplateResponse(
        "partials/host_rows.html",
        {
            "request": request,
            "hosts": hosts,
            "total_wlan_clients": total_wlan_clients,
        },
    )
