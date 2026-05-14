"""
scanner/http_client.py
Client HTTP async basé sur httpx avec :
- connection pooling
- retry exponentiel
- timeout configurables
- gestion propre du cycle de vie
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Headers communs Vinted
_VINTED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.vinted.fr/catalog",
    "X-Requested-With": "XMLHttpRequest",
}

_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
_LIMITS  = httpx.Limits(max_connections=10, max_keepalive_connections=5)


class VintedHTTPClient:
    """
    Client HTTP async réutilisable.
    Instancier une seule fois, fermer avec .aclose() en fin de vie.
    """

    def __init__(self, max_retries: int = 3, backoff_base: float = 1.5):
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=_VINTED_HEADERS,
                timeout=_TIMEOUT,
                limits=_LIMITS,
                follow_redirects=True,
            )
            await self._init_session()
        return self._client

    async def _init_session(self) -> None:
        """Visite la page d'accueil pour obtenir les cookies de session."""
        try:
            assert self._client is not None
            await self._client.get(
                "https://www.vinted.fr",
                headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
            )
            logger.debug("Session Vinted initialisée.")
        except Exception as e:
            logger.warning("Init session Vinted échouée : %s", e)

    async def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict | None:
        """
        GET avec retry exponentiel.
        Retourne le JSON parsé ou None en cas d'échec définitif.
        """
        client = await self._get_client()

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = await client.get(url, params=params)

                if resp.status_code == 401:
                    logger.info("Session expirée (401), renouvellement…")
                    await self._init_session()
                    continue

                if resp.status_code == 429:
                    wait = float(resp.headers.get("Retry-After", 60))
                    logger.warning("Rate-limit Vinted (429), pause %.0fs", wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    logger.warning("HTTP %d pour %s", resp.status_code, url)
                    return None

                return resp.json()

            except httpx.TimeoutException:
                wait = self._backoff_base ** attempt
                logger.warning("Timeout (tentative %d/%d), retry dans %.1fs", attempt, self._max_retries, wait)
                await asyncio.sleep(wait)

            except httpx.NetworkError as e:
                wait = self._backoff_base ** attempt
                logger.warning("NetworkError %s (tentative %d/%d), retry dans %.1fs", e, attempt, self._max_retries, wait)
                # Recréer le client sur erreur réseau
                await self.aclose()
                await asyncio.sleep(wait)

            except Exception as e:
                logger.error("Erreur inattendue HTTP : %s", e)
                return None

        logger.error("Échec définitif après %d tentatives : %s", self._max_retries, url)
        return None

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
