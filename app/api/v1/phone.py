"""
Phone API — call list data endpoints (JSON + HTMX partials).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.phone.service import CALL_MISSED, CALL_OUT, CALL_RECEIVED, CALL_REJECTED, PhoneService

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/stats")
async def phone_stats() -> dict[str, int]:
    """Return call counts by type (last 30 days)."""
    svc = PhoneService()
    return await svc.get_stats()


@router.get("/calls")
async def phone_calls(
    calltype: int = Query(default=0, description="0=all 1=received 2=missed 3=out 10=rejected"),
    days: int = Query(default=30),
    num: int = Query(default=100),
) -> list[dict[str, Any]]:
    """Return call list as JSON."""
    svc = PhoneService()
    calls = await svc.get_calls(calltype=calltype, days=days, num=num)
    # Make dates serialisable
    for c in calls:
        if c.get("date") and hasattr(c["date"], "isoformat"):
            c["date"] = c["date"].isoformat()
    return calls


@router.get("/partials/calls", response_class=HTMLResponse)
async def partials_calls(
    request: Request,
    calltype: int = Query(default=0),
    days: int = Query(default=30),
) -> HTMLResponse:
    """HTMX partial — table rows for the call list."""
    svc = PhoneService()
    calls = await svc.get_calls(calltype=calltype, days=days, num=150)
    return templates.TemplateResponse(
        "partials/call_rows.html",
        {
            "request": request,
            "calls": calls,
            "RECEIVED": CALL_RECEIVED,
            "MISSED": CALL_MISSED,
            "OUT": CALL_OUT,
            "REJECTED": CALL_REJECTED,
        },
    )
