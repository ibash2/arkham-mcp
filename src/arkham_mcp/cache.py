"""
In-memory TTL cache for ArkhamClient responses.
No external dependencies — uses only stdlib.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# TTL presets in seconds
TTL_STATIC = 86_400      # chains, entity_types — меняются редко
TTL_ENTITY = 3_600       # entity metadata — меняется ~часами
TTL_ADDRESS = 900        # enriched address, tokens, contracts — 15 min
TTL_MARKET = 300         # balances, network status, altcoin index — 5 min
TTL_FLOW = 300           # flow, history, counterparties — 5 min


@dataclass
class _Entry:
    value: Any
    expires_at: float


class ResponseCache:
    """
    Async-safe TTL cache for API responses.

    Usage:
        cache = ResponseCache()
        value = await cache.get_or_fetch("key", ttl=900, fetch=coro_fn)
    """

    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()

    def _is_valid(self, entry: _Entry) -> bool:
        return time.monotonic() < entry.expires_at

    async def get(self, key: str) -> tuple[bool, Any]:
        """Return (hit, value). hit=False if missing or expired."""
        async with self._lock:
            entry = self._store.get(key)
            if entry and self._is_valid(entry):
                return True, entry.value
            return False, None

    async def set(self, key: str, value: Any, ttl: float) -> None:
        async with self._lock:
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl)

    async def get_or_fetch(self, key: str, ttl: float, fetch) -> Any:
        """
        Return cached value or call `fetch()` coroutine, cache and return the result.
        fetch must be a zero-argument async callable.
        """
        hit, value = await self.get(key)
        if hit:
            return value
        value = await fetch()
        await self.set(key, value, ttl)
        return value

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def size(self) -> int:
        return len(self._store)

    async def evict_expired(self) -> int:
        """Remove expired entries. Returns count of evicted entries."""
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, e in self._store.items() if e.expires_at <= now]
            for k in expired:
                del self._store[k]
        return len(expired)
