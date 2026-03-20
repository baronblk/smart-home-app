"""
In-process TTL cache for FRITZ!Box API responses.

Rationale: FRITZ!Box SOAP calls take 1-3 s each. Without caching,
every HTMX poll (every 10 s) and every Netzwerk-page load triggers
a live call, blocking the response for seconds.

Design:
  - Per-key asyncio.Lock prevents cache stampede (only one caller
    fetches from FRITZ!Box; all concurrent callers wait and then
    read the cached value).
  - poll_and_snapshot_all() writes state into the cache after each
    background sweep, so the very first HTMX poll after startup
    already gets a cached value.
  - Control commands (turn_on/off) invalidate the relevant key so
    the next poll reflects the new state immediately.

Singleton instances (module-level):
  device_state_cache   — keyed by "state:{ain}",  TTL 10 s
  network_cache        — keyed by "dsl" / "hosts" / "wlan", TTL 15-30 s
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class _Entry:
    __slots__ = ("expires_at", "value")

    def __init__(self, value: Any, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at

    def is_valid(self) -> bool:
        return time.monotonic() < self.expires_at


class TTLCache:
    """Async TTL cache with per-key Lock to prevent cache stampede."""

    def __init__(self, name: str = "cache") -> None:
        self._name = name
        self._store: dict[str, _Entry] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._meta_lock = asyncio.Lock()

    async def _key_lock(self, key: str) -> asyncio.Lock:
        async with self._meta_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_or_fetch(
        self,
        key: str,
        ttl: float,
        fetch: Callable[[], Awaitable[T]],
    ) -> T:
        """Return cached value or call *fetch*, cache the result, return it."""
        # Fast path — no lock needed for a simple dict read
        entry = self._store.get(key)
        if entry and entry.is_valid():
            return cast(T, entry.value)

        lock = await self._key_lock(key)
        async with lock:
            # Double-check under lock (another coroutine may have fetched meanwhile)
            entry = self._store.get(key)
            if entry and entry.is_valid():
                return cast(T, entry.value)

            logger.debug("[%s] cache miss — fetching %r", self._name, key)
            value = await fetch()
            self._store[key] = _Entry(value, time.monotonic() + ttl)
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        """Write a value directly (e.g. from background poller)."""
        self._store[key] = _Entry(value, time.monotonic() + ttl)

    def invalidate(self, key: str) -> None:
        """Remove a key so the next call fetches fresh data."""
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# ---------------------------------------------------------------------------
# Singletons — import these in service modules
# ---------------------------------------------------------------------------

#: Per-device state cache. Key = "state:{ain}", TTL = 10 s (matches HTMX poll)
device_state_cache: TTLCache = TTLCache(name="device_state")

#: Network data cache. Keys: "dsl" (15 s), "hosts" (30 s), "wlan" (60 s)
network_cache: TTLCache = TTLCache(name="network")

#: Phone call list cache. Key = "calls:{calltype}:{days}", TTL = 120 s.
#: FritzCall fetches are expensive (2-4 s each). Both /stats and /partials/calls
#: fire on page load; caching ensures the second request is instant.
phone_cache: TTLCache = TTLCache(name="phone")
