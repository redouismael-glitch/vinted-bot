"""
utils/rate_limiter.py
Token bucket rate limiter 100% async.
Utilisé pour limiter les requêtes Vinted et les envois Telegram.
"""
from __future__ import annotations

import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """
    Token bucket : garantit au max `rate` appels par `per` secondes.
    Thread-safe via asyncio.Lock.
    """

    def __init__(self, rate: float, per: float = 1.0, burst: int | None = None):
        self.rate = rate          # tokens ajoutés par seconde
        self.per = per
        self.burst = burst or int(rate * per)
        self._tokens: float = float(self.burst)
        self._last: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(
                self.burst,
                self._tokens + elapsed * (self.rate / self.per),
            )
            if self._tokens < 1:
                wait = (1 - self._tokens) * (self.per / self.rate)
                logger.debug("Rate limiter : pause %.2fs", wait)
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, *args):
        pass
