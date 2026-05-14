"""
core/engine.py
Moteur principal : orchestre scan → filtre → score → alerte.
Tourne en tâche asyncio permanente, contrôlé via config.actif.
"""
from __future__ import annotations

import asyncio
import logging
import time

from ..analytics.scoring import compute_score
from ..analytics.stats import BotStats
from ..config.settings import Config
from ..filters.item_filter import apply_all
from ..scanner.http_client import VintedHTTPClient
from ..scanner.vinted_scanner import VintedScanner
from ..telegram_bot.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def _extract_price(item: dict) -> float | None:
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None


def _format_alert(item: dict, brand_key: str, score_result) -> str:
    titre      = item.get("title", "Sans titre")
    marque_raw = item.get("brand_title", "") or brand_key
    taille     = item.get("size_title", "?")
    prix       = _extract_price(item) or "?"
    item_id    = item.get("id")
    url        = f"https://www.vinted.fr/items/{item_id}"

    return (
        f"{score_result.label}\n"
        f"🎯 Score : <b>{score_result.score}/100</b>\n\n"
        f"👕 <b>{titre}</b>\n"
        f"🏷️ Marque : {marque_raw}\n"
        f"📐 Taille : {taille}\n"
        f"💶 Prix achat : {prix}€\n"
        f"📈 Revente estimée : ~{score_result.prix_revente_estime}€\n"
        f"💰 Marge nette : ~{score_result.marge_nette}€\n\n"
        f"🔗 <a href='{url}'>Voir l'annonce</a>"
    )


class BotEngine:
    def __init__(
        self,
        config: Config,
        notifier: TelegramNotifier,
        stats: BotStats,
    ):
        self.config   = config
        self.notifier = notifier
        self.stats    = stats
        self._http    = VintedHTTPClient(max_retries=3)
        self._scanner = VintedScanner(config, self._http)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="bot_engine")
            logger.info("BotEngine démarré.")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._http.aclose()
        logger.info("BotEngine arrêté.")

    async def _loop(self) -> None:
        """Boucle principale : scan → sleep(cooldown), en morceaux de 5s."""
        while True:
            try:
                if self.config.actif:
                    await self._run_scan()
                # Attente cooldown par tranches de 5s (réactif à /stop)
                elapsed = 0
                while elapsed < self.config.cooldown_sec:
                    await asyncio.sleep(5)
                    elapsed += 5
                    if not self.config.actif:
                        break
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats.errors += 1
                logger.exception("Erreur critique dans BotEngine._loop : %s", e)
                await asyncio.sleep(30)  # pause avant retry

    async def _run_scan(self) -> None:
        t0 = time.monotonic()
        self.stats.scans_total += 1
        logger.info(
            "Scan #%d démarré | score_min=%d | seen=%d",
            self.stats.scans_total, self.config.score_min, self._scanner.seen_count,
        )

        try:
            new_items = await self._scanner.scan_all()
        except Exception as e:
            self.stats.errors += 1
            logger.error("Erreur scan_all : %s", e)
            return

        self.stats.items_fetched += len(new_items)

        for item in new_items:
            await self._process_item(item)

        duration = time.monotonic() - t0
        self.stats.last_scan_ts = time.monotonic()
        self.stats.last_scan_duration_sec = duration
        logger.info(
            "Scan terminé en %.1fs | %d items | %d alertes total",
            duration, len(new_items), self.stats.alerts_sent,
        )

    async def _process_item(self, item: dict) -> None:
        # ── Filtres ───────────────────────────────────────────────────────────
        passed, reason, brand_key = apply_all(item, self.config)
        if not passed:
            self.stats.items_filtered += 1
            return

        self.stats.items_analyzed += 1

        # ── Scoring ───────────────────────────────────────────────────────────
        prix = _extract_price(item)
        if prix is None:
            return

        titre     = item.get("title", "") or ""
        condition = item.get("status", None)

        score_result = compute_score(
            prix=prix,
            brand_key=brand_key,
            titre=titre,
            condition_key=condition,
        )

        # ── Alerte si score suffisant ─────────────────────────────────────────
        if score_result.score < self.config.score_min:
            return

        if score_result.marge_nette <= 0:
            return

        self.stats.alerts_sent += 1
        msg = _format_alert(item, brand_key, score_result)
        await self.notifier.send(msg)
        logger.info(
            "🚨 Alerte #%d : %s | score=%d | marge=%.0f€",
            self.stats.alerts_sent,
            titre[:40],
            score_result.score,
            score_result.marge_nette,
        )
