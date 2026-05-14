"""
scanner/vinted_scanner.py
Orchestre les requêtes vers l'API Vinted.
- Déduplication via seen_ids avec LRU-like purge
- Rate limiting entre requêtes
- Cache TTL pour éviter de re-fetcher la même query trop vite
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict
from urllib.parse import quote

from ..config.settings import Config, SEARCH_QUERIES
from ..utils.rate_limiter import AsyncRateLimiter
from .http_client import VintedHTTPClient

logger = logging.getLogger(__name__)

_API_BASE = "https://www.vinted.fr/api/v2/catalog/items"

# Cache par query : (timestamp, items)
_QueryCache = dict[str, tuple[float, list[dict]]]


class VintedScanner:
    def __init__(self, config: Config, http: VintedHTTPClient):
        self.config = config
        self.http = http
        # Rate limiter : max 1 requête / 2s pour ne pas stresser Vinted
        self._rl = AsyncRateLimiter(rate=0.5, per=1.0, burst=3)
        # Cache TTL par query (évite de re-fetcher dans la même minute)
        self._cache: _QueryCache = {}
        self._cache_ttl = 60.0  # secondes
        # seen_ids : OrderedDict pour purge FIFO
        self._seen: OrderedDict[int, float] = OrderedDict()

    def _is_seen(self, item_id: int) -> bool:
        return item_id in self._seen

    def _mark_seen(self, item_id: int) -> None:
        self._seen[item_id] = time.monotonic()
        # Purge si dépasse la limite mémoire
        while len(self._seen) > self.config.seen_ids_max:
            self._seen.popitem(last=False)

    def _cache_get(self, query: str) -> list[dict] | None:
        entry = self._cache.get(query)
        if entry and time.monotonic() - entry[0] < self._cache_ttl:
            return entry[1]
        return None

    def _cache_set(self, query: str, items: list[dict]) -> None:
        self._cache[query] = (time.monotonic(), items)
        # Purge du cache si trop grand
        if len(self._cache) > 200:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest]

    async def fetch_query(self, query: str, per_page: int = 20) -> list[dict]:
        """Fetch une query Vinted avec cache + rate limit."""
        cached = self._cache_get(query)
        if cached is not None:
            logger.debug("Cache hit pour '%s'", query)
            return cached

        async with self._rl:
            data = await self.http.get_json(
                _API_BASE,
                params={
                    "search_text": query,
                    "per_page": per_page,
                    "order": "newest_first",
                },
            )

        items = data.get("items", []) if data else []
        self._cache_set(query, items)
        return items

    async def scan_all(self) -> list[dict]:
        """
        Lance toutes les queries en parallèle (par batches de 5)
        et retourne uniquement les articles nouveaux.
        """
        new_items: list[dict] = []
        queries = list(SEARCH_QUERIES)
        batch_size = 5

        for i in range(0, len(queries), batch_size):
            batch = queries[i : i + batch_size]
            results = await asyncio.gather(
                *[self.fetch_query(q) for q in batch],
                return_exceptions=True,
            )
            for res in results:
                if isinstance(res, Exception):
                    logger.error("Erreur dans batch scan : %s", res)
                    continue
                for item in res:
                    item_id = item.get("id")
                    if not item_id or self._is_seen(item_id):
                        continue
                    self._mark_seen(item_id)
                    new_items.append(item)
            # Petite pause entre batches
            await asyncio.sleep(1.0)

        logger.info("Scan terminé — %d nouveaux articles", len(new_items))
        return new_items

    @property
    def seen_count(self) -> int:
        return len(self._seen)
