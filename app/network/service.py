"""
NetworkService — wraps FritzStatus, FritzHosts, FritzWLAN for async use.

In mock mode (FRITZ_MOCK_MODE=true) returns synthetic data so the UI
works without real FRITZ!Box hardware.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

from app.config import settings

NA = chr(0x2013)  # EN DASH placeholder for missing values

logger = logging.getLogger(__name__)


def _mock_dsl_status() -> dict[str, Any]:
    return {
        "is_connected": True,
        "is_linked": True,
        "external_ip": "93.184.216.34",
        "external_ipv6": "2606:2800:220:1:248:1893:25c8:1946",
        "uptime_str": "3 Tage, 14:22:07",
        "uptime_seconds": 307327,
        "max_down_kbps": 250_000,
        "max_up_kbps": 40_000,
        "max_down_str": "250 Mbit/s",
        "max_up_str": "40 Mbit/s",
        "noise_margin_down": "9.0 dB",
        "noise_margin_up": "8.5 dB",
        "attenuation_down": "18.0 dB",
        "attenuation_up": "6.5 dB",
        "model": "FRITZ!Box 7590 AX",
    }


def _mock_wlan_networks() -> list[dict[str, Any]]:
    return [
        {
            "index": 1,
            "ssid": "HomeNet-5G",
            "channel": 36,
            "is_enabled": True,
            "is_hidden": False,
            "client_count": 8,
            "band": "5 GHz",
        },
        {
            "index": 2,
            "ssid": "HomeNet-2.4G",
            "channel": 6,
            "is_enabled": True,
            "is_hidden": False,
            "client_count": 5,
            "band": "2.4 GHz",
        },
        {
            "index": 3,
            "ssid": "HomeNet-Gast",
            "channel": 11,
            "is_enabled": True,
            "is_hidden": False,
            "client_count": 2,
            "band": "2.4 GHz",
        },
    ]


def _mock_hosts() -> list[dict[str, Any]]:
    return [
        {
            "ip": "192.168.178.2",
            "name": "nas-dxp4800",
            "mac": "AA:BB:CC:DD:EE:01",
            "interface_type": "Ethernet",
            "active": True,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.10",
            "name": "iPhone-Rene",
            "mac": "AA:BB:CC:DD:EE:02",
            "interface_type": "802.11ac",
            "active": True,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.11",
            "name": "iPad-Rene",
            "mac": "AA:BB:CC:DD:EE:03",
            "interface_type": "802.11ax",
            "active": True,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.20",
            "name": "SmartTV-Wohnzimmer",
            "mac": "AA:BB:CC:DD:EE:04",
            "interface_type": "Ethernet",
            "active": True,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.30",
            "name": "Drucker-HP",
            "mac": "AA:BB:CC:DD:EE:05",
            "interface_type": "802.11n",
            "active": False,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.31",
            "name": "Laptop-Office",
            "mac": "AA:BB:CC:DD:EE:06",
            "interface_type": "802.11ac",
            "active": True,
            "address_source": "DHCP",
        },
        {
            "ip": "192.168.178.40",
            "name": "FRITZ!DECT 200",
            "mac": "AA:BB:CC:DD:EE:07",
            "interface_type": "DECT",
            "active": True,
            "address_source": "statisch",
        },
        {
            "ip": "192.168.178.41",
            "name": "FRITZ!DECT 301",
            "mac": "AA:BB:CC:DD:EE:08",
            "interface_type": "DECT",
            "active": True,
            "address_source": "statisch",
        },
    ]


def _fmt_kbps(kbps: int) -> str:
    if kbps >= 1000:
        return f"{kbps / 1000:.0f} Mbit/s"
    return f"{kbps} kbit/s"


def _fmt_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days} Tag{'e' if days != 1 else ''}, {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class NetworkService:
    """Async wrapper around FritzStatus, FritzHosts, FritzWLAN."""

    async def get_dsl_status(self) -> dict[str, Any]:
        """Return DSL / WAN connection status."""
        if settings.fritz_mock_mode:
            return _mock_dsl_status()

        loop = asyncio.get_event_loop()
        try:
            from fritzconnection.lib.fritzstatus import FritzStatus

            def _fetch() -> dict[str, Any]:
                fs = FritzStatus(
                    address=settings.fritz_host,
                    user=settings.fritz_username,
                    password=settings.fritz_password,
                    use_tls=False,
                )
                max_down, max_up = fs.max_bit_rate or (0, 0)
                uptime = fs.connection_uptime or 0
                noise = fs.noise_margin or (None, None)
                atten = fs.attenuation or (None, None)
                return {
                    "is_connected": bool(fs.is_connected),
                    "is_linked": bool(fs.is_linked),
                    "external_ip": fs.external_ip or NA,
                    "external_ipv6": fs.external_ipv6 or NA,
                    "uptime_str": _fmt_uptime(uptime),
                    "uptime_seconds": uptime,
                    "max_down_kbps": max_down // 1000,
                    "max_up_kbps": max_up // 1000,
                    "max_down_str": _fmt_kbps(max_down // 1000),
                    "max_up_str": _fmt_kbps(max_up // 1000),
                    "noise_margin_down": f"{noise[0]} dB" if noise[0] else NA,
                    "noise_margin_up": f"{noise[1]} dB" if noise[1] else NA,
                    "attenuation_down": f"{atten[0]} dB" if atten[0] else NA,
                    "attenuation_up": f"{atten[1]} dB" if atten[1] else NA,
                    "model": fs.modelname or "FRITZ!Box",
                }

            return await loop.run_in_executor(None, partial(_fetch))
        except Exception as exc:
            logger.warning("FritzStatus failed: %s", exc)
            return {
                "is_connected": False,
                "is_linked": False,
                "external_ip": NA,
                "external_ipv6": NA,
                "uptime_str": NA,
                "uptime_seconds": 0,
                "max_down_kbps": 0,
                "max_up_kbps": 0,
                "max_down_str": NA,
                "max_up_str": NA,
                "noise_margin_down": NA,
                "noise_margin_up": NA,
                "attenuation_down": NA,
                "attenuation_up": NA,
                "model": "FRITZ!Box",
            }

    async def get_wlan_networks(self) -> list[dict[str, Any]]:
        """Return list of WLAN networks (2.4 GHz, 5 GHz, guest)."""
        if settings.fritz_mock_mode:
            return _mock_wlan_networks()

        loop = asyncio.get_event_loop()
        networks: list[dict[str, Any]] = []
        try:
            from fritzconnection.lib.fritzwlan import FritzWLAN

            def _fetch_one(idx: int) -> dict[str, Any] | None:
                try:
                    fw = FritzWLAN(
                        address=settings.fritz_host,
                        user=settings.fritz_username,
                        password=settings.fritz_password,
                        use_tls=False,
                        wifi_number=idx,
                    )
                    channel = fw.channel or 0
                    band = "5 GHz" if channel > 14 else "2.4 GHz"
                    return {
                        "index": idx,
                        "ssid": fw.ssid or f"WLAN {idx}",
                        "channel": channel,
                        "is_enabled": bool(fw.is_enabled),
                        "is_hidden": bool(fw.is_hidden),
                        "client_count": fw.total_host_number or 0,
                        "band": band,
                    }
                except Exception:
                    return None

            for i in (1, 2, 3):
                result = await loop.run_in_executor(None, partial(_fetch_one, i))
                if result is not None:
                    networks.append(result)
        except Exception as exc:
            logger.warning("FritzWLAN failed: %s", exc)
        return networks

    async def get_hosts(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Return list of known network hosts."""
        if settings.fritz_mock_mode:
            hosts = _mock_hosts()
            if active_only:
                return [h for h in hosts if h["active"]]
            return hosts

        loop = asyncio.get_event_loop()
        try:
            from fritzconnection.lib.fritzhosts import FritzHosts

            def _fetch() -> list[dict[str, Any]]:
                fh = FritzHosts(
                    address=settings.fritz_host,
                    user=settings.fritz_username,
                    password=settings.fritz_password,
                    use_tls=False,
                )
                raw = fh.get_active_hosts() if active_only else fh.get_hosts_info()
                result = []
                for h in raw:
                    result.append(
                        {
                            "ip": h.get("ip", NA),
                            "name": h.get("name", NA),
                            "mac": h.get("mac", NA),
                            "interface_type": h.get("interface_type", NA),
                            "active": bool(h.get("status", False)),
                            "address_source": h.get("address_source", "DHCP"),
                        }
                    )
                return result

            return await loop.run_in_executor(None, partial(_fetch))
        except Exception as exc:
            logger.warning("FritzHosts failed: %s", exc)
            return []
