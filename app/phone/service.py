"""
PhoneService — wraps FritzCall for async use.

In mock mode (FRITZ_MOCK_MODE=true) returns synthetic call data so the UI
works without real FRITZ!Box hardware.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Any

from app.config import settings

NA = chr(0x2013)  # EN DASH placeholder for missing values

logger = logging.getLogger(__name__)

# Call type constants from fritzconnection
CALL_RECEIVED = 1
CALL_MISSED = 2
CALL_OUT = 3
CALL_REJECTED = 10

CALL_TYPE_LABEL: dict[int, str] = {
    CALL_RECEIVED: "eingehend",
    CALL_MISSED: "verpasst",
    CALL_OUT: "ausgehend",
    CALL_REJECTED: "abgewiesen",
    9: "aktiv (eingehend)",
    11: "aktiv (ausgehend)",
}

CALL_TYPE_ICON: dict[int, str] = {
    CALL_RECEIVED: "phone-incoming",
    CALL_MISSED: "phone-missed",
    CALL_OUT: "phone-outgoing",
    CALL_REJECTED: "phone-off",
    9: "phone-call",
    11: "phone-call",
}


def _call_to_dict(call: Any) -> dict[str, Any]:
    """Convert a fritzconnection Call object to a plain dict."""
    ctype = call.type if call.type is not None else 0
    is_out = ctype in (CALL_OUT, 11)
    number = call.CalledNumber if is_out else call.CallerNumber
    name = call.Name or ""
    date = call.date if hasattr(call, "date") and call.date else None
    duration = call.duration if hasattr(call, "duration") and call.duration else timedelta(0)
    return {
        "id": call.Id,
        "type": ctype,
        "type_label": CALL_TYPE_LABEL.get(ctype, str(ctype)),
        "type_icon": CALL_TYPE_ICON.get(ctype, "phone"),
        "number": number or NA,
        "name": name,
        "device": call.Device or "",
        "date": date,
        "date_str": date.strftime("%d.%m.%Y %H:%M") if date else NA,
        "duration_str": str(duration) if duration.total_seconds() > 0 else NA,
        "is_missed": ctype == CALL_MISSED,
        "is_out": is_out,
    }


def _mock_calls() -> list[dict[str, Any]]:
    """Return realistic mock call data for development / mock mode."""
    now = datetime.now()
    return [
        {
            "id": 1,
            "type": CALL_RECEIVED,
            "type_label": "eingehend",
            "type_icon": "phone-incoming",
            "number": "+49 89 12345678",
            "name": "Max Mustermann",
            "device": "FRITZ!Fon C6",
            "date": now - timedelta(minutes=30),
            "date_str": (now - timedelta(minutes=30)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": "0:04:22",
            "is_missed": False,
            "is_out": False,
        },
        {
            "id": 2,
            "type": CALL_MISSED,
            "type_label": "verpasst",
            "type_icon": "phone-missed",
            "number": "+49 30 98765432",
            "name": "",
            "device": "",
            "date": now - timedelta(hours=2),
            "date_str": (now - timedelta(hours=2)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": NA,
            "is_missed": True,
            "is_out": False,
        },
        {
            "id": 3,
            "type": CALL_OUT,
            "type_label": "ausgehend",
            "type_icon": "phone-outgoing",
            "number": "+49 89 55551234",
            "name": "Erika Mustermann",
            "device": "FRITZ!Fon C6",
            "date": now - timedelta(hours=5),
            "date_str": (now - timedelta(hours=5)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": "0:12:47",
            "is_missed": False,
            "is_out": True,
        },
        {
            "id": 4,
            "type": CALL_MISSED,
            "type_label": "verpasst",
            "type_icon": "phone-missed",
            "number": "08001234567",
            "name": "Kundenservice GmbH",
            "device": "",
            "date": now - timedelta(days=1),
            "date_str": (now - timedelta(days=1)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": NA,
            "is_missed": True,
            "is_out": False,
        },
        {
            "id": 5,
            "type": CALL_OUT,
            "type_label": "ausgehend",
            "type_icon": "phone-outgoing",
            "number": "+49 40 22334455",
            "name": "Familie Müller",
            "device": "FRITZ!Fon C6",
            "date": now - timedelta(days=1, hours=3),
            "date_str": (now - timedelta(days=1, hours=3)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": "0:08:03",
            "is_missed": False,
            "is_out": True,
        },
        {
            "id": 6,
            "type": CALL_RECEIVED,
            "type_label": "eingehend",
            "type_icon": "phone-incoming",
            "number": "+49 211 66778899",
            "name": "Büro Schmidt",
            "device": "FRITZ!Fon MT-F",
            "date": now - timedelta(days=2),
            "date_str": (now - timedelta(days=2)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": "0:02:15",
            "is_missed": False,
            "is_out": False,
        },
        {
            "id": 7,
            "type": CALL_REJECTED,
            "type_label": "abgewiesen",
            "type_icon": "phone-off",
            "number": "01806123456",
            "name": "",
            "device": "",
            "date": now - timedelta(days=3),
            "date_str": (now - timedelta(days=3)).strftime("%d.%m.%Y %H:%M"),
            "duration_str": NA,
            "is_missed": False,
            "is_out": False,
        },
    ]


class PhoneService:
    """Async wrapper around FritzCall — runs sync calls in thread pool."""

    async def get_calls(
        self,
        calltype: int = 0,
        days: int | None = 30,
        num: int | None = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch call list.

        calltype: 0=all, 1=received, 2=missed, 3=outgoing, 10=rejected
        Returns a list of plain dicts, sorted newest-first.
        """
        if settings.fritz_mock_mode:
            calls = _mock_calls()
            if calltype != 0:
                calls = [c for c in calls if c["type"] == calltype]
            return calls

        loop = asyncio.get_event_loop()
        try:
            from fritzconnection.lib.fritzcall import FritzCall

            def _fetch() -> list[dict[str, Any]]:
                fc = FritzCall(
                    address=settings.fritz_host,
                    user=settings.fritz_username,
                    password=settings.fritz_password,
                    use_tls=False,
                )
                raw = fc.get_calls(calltype=calltype, days=days, num=num)
                return [_call_to_dict(c) for c in raw]

            return await loop.run_in_executor(None, partial(_fetch))
        except Exception as exc:
            logger.warning("FritzCall failed, returning empty list: %s", exc)
            return []

    async def get_stats(self) -> dict[str, int]:
        """Return counts per call type for the badge display."""
        all_calls = await self.get_calls(calltype=0, days=30)
        return {
            "total": len(all_calls),
            "received": sum(1 for c in all_calls if c["type"] == CALL_RECEIVED),
            "missed": sum(1 for c in all_calls if c["type"] == CALL_MISSED),
            "outgoing": sum(1 for c in all_calls if c["type"] == CALL_OUT),
            "rejected": sum(1 for c in all_calls if c["type"] == CALL_REJECTED),
        }
