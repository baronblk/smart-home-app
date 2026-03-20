"""
NetworkService — wraps FritzStatus, FritzHosts, FritzWLAN for async use.

In mock mode (FRITZ_MOCK_MODE=true) returns synthetic data so the UI
works without real FRITZ!Box hardware.

Fiber/Glasfaser note:
  FritzStatus uses DSL-specific SOAP actions (WANDSLInterfaceConfig) that do
  not exist on fiber (FTTH/FTTB) boxes and raise FritzActionError.  This
  service handles that gracefully by fetching each attribute individually and
  falling back to WANCommonInterfaceCfg for speed and link status.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any, cast

from app.cache import network_cache
from app.config import settings

NA = chr(0x2013)  # EN DASH placeholder for missing values

logger = logging.getLogger(__name__)


def _safe_attr(fs: object, name: str, default: Any = None) -> Any:
    """Read an attribute from FritzStatus without crashing on DSL-only properties."""
    try:
        return getattr(fs, name)
    except Exception:
        return default


def _addon_speeds(fc: object) -> tuple[int, int]:
    """Return (down_bps, up_bps) from WANCommonInterfaceCfg:GetAddonInfos (fiber-safe)."""
    try:
        info = fc.call_action("WANCommonInterfaceCfg", "GetAddonInfos")  # type: ignore[attr-defined]
        return (
            int(info.get("NewLayer1DownstreamMaxBitRate", 0)),
            int(info.get("NewLayer1UpstreamMaxBitRate", 0)),
        )
    except Exception:
        return 0, 0


def _wan_link_props(fc: object) -> dict[str, Any]:
    """Return WANCommonInterfaceCfg:GetCommonLinkProperties dict, empty on error."""
    try:
        result = fc.call_action("WANCommonInterfaceCfg", "GetCommonLinkProperties")  # type: ignore[attr-defined]
        return cast(dict[str, Any], result)
    except Exception:
        return {}


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
        "noise_margin_down": NA,
        "noise_margin_up": NA,
        "attenuation_down": NA,
        "attenuation_up": NA,
        "model": "FRITZ!Box 5530 Fiber",
        "connection_type": "Glasfaser",
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
        """Return WAN connection status — cached 15 s, fiber-safe."""
        if settings.fritz_mock_mode:
            return _mock_dsl_status()
        return await network_cache.get_or_fetch(key="dsl", ttl=15.0, fetch=self._live_dsl_status)

    async def _live_dsl_status(self) -> dict[str, Any]:
        """Actual FRITZ!Box WAN status fetch (called on cache miss)."""
        loop = asyncio.get_event_loop()

        def _fetch() -> dict[str, Any]:
            from fritzconnection.lib.fritzstatus import FritzStatus

            fs = FritzStatus(
                address=settings.fritz_host,
                user=settings.fritz_username,
                password=settings.fritz_password,
                use_tls=False,
            )
            fc = fs.fc  # underlying FritzConnection for direct SOAP calls

            # --- Basic WAN attributes (work on DSL and fiber) ---
            is_connected: bool = bool(_safe_attr(fs, "is_connected", False))
            is_linked: bool = bool(_safe_attr(fs, "is_linked", False))
            external_ip: str = _safe_attr(fs, "external_ip") or NA
            external_ipv6: str = _safe_attr(fs, "external_ipv6") or NA
            uptime: int = _safe_attr(fs, "connection_uptime") or 0
            model: str = _safe_attr(fs, "modelname") or "FRITZ!Box"

            # --- Fiber fallback: WANCommonInterfaceCfg is always available ---
            link_props = _wan_link_props(fc)
            phys_status = link_props.get("NewPhysicalLinkStatus", "")
            access_type = link_props.get("NewWANAccessType", "WAN")
            if phys_status:
                is_linked = phys_status.lower() == "up"
                # Fiber: physical link up means internet is reachable even when
                # FritzStatus.is_connected returns False (DSL service absent)
                if is_linked and not is_connected:
                    is_connected = True

            # Friendly connection type label for the UI
            _at = access_type.lower()
            if _at in ("dsl", "adsl", "vdsl"):
                conn_type = "DSL"
            elif _at == "ethernet":
                conn_type = "Glasfaser / Kabel"
            else:
                conn_type = access_type or "WAN"

            # --- Speed: try DSL-specific first; fall back to WANCommonInterfaceCfg ---
            bit_rate = _safe_attr(fs, "max_bit_rate")
            if bit_rate:
                max_down, max_up = int(bit_rate[0]), int(bit_rate[1])
            else:
                max_down, max_up = 0, 0
            if max_down == 0:
                max_down, max_up = _addon_speeds(fc)

            # --- DSL-only: noise / attenuation (silently NA on fiber) ---
            noise: tuple[Any, Any] = _safe_attr(fs, "noise_margin") or (None, None)
            atten: tuple[Any, Any] = _safe_attr(fs, "attenuation") or (None, None)

            return {
                "is_connected": is_connected,
                "is_linked": is_linked,
                "external_ip": external_ip,
                "external_ipv6": external_ipv6,
                "uptime_str": _fmt_uptime(uptime) if uptime else NA,
                "uptime_seconds": uptime,
                "max_down_kbps": max_down // 1000,
                "max_up_kbps": max_up // 1000,
                "max_down_str": _fmt_kbps(max_down // 1000) if max_down else NA,
                "max_up_str": _fmt_kbps(max_up // 1000) if max_up else NA,
                "noise_margin_down": f"{noise[0]} dB" if noise[0] else NA,
                "noise_margin_up": f"{noise[1]} dB" if noise[1] else NA,
                "attenuation_down": f"{atten[0]} dB" if atten[0] else NA,
                "attenuation_up": f"{atten[1]} dB" if atten[1] else NA,
                "model": model,
                "connection_type": conn_type,
            }

        try:
            return await loop.run_in_executor(None, partial(_fetch))
        except Exception as exc:
            logger.warning("NetworkService.get_dsl_status failed: %s", exc)
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
                "connection_type": "WAN",
            }

    async def get_wlan_networks(self) -> list[dict[str, Any]]:
        """Return list of WLAN networks (2.4 GHz, 5 GHz, guest) — cached 60 s."""
        if settings.fritz_mock_mode:
            return _mock_wlan_networks()
        return await network_cache.get_or_fetch(
            key="wlan", ttl=60.0, fetch=self._live_wlan_networks
        )

    async def _live_wlan_networks(self) -> list[dict[str, Any]]:
        """Actual FRITZ!Box WLAN fetch (called on cache miss)."""
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
        """Return list of known network hosts — cached 30 s."""
        if settings.fritz_mock_mode:
            hosts = _mock_hosts()
            if active_only:
                return [h for h in hosts if h["active"]]
            return hosts
        return await network_cache.get_or_fetch(
            key=f"hosts:{active_only}",
            ttl=30.0,
            fetch=lambda: self._live_hosts(active_only),
        )

    async def _live_hosts(self, active_only: bool = False) -> list[dict[str, Any]]:
        """Actual FRITZ!Box hosts fetch (called on cache miss)."""
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
