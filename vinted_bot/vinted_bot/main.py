"""
main.py
Point d'entrée du bot Vinted.
Initialise tous les modules et démarre l'application Telegram.
"""
from __future__ import annotations

import asyncio
import os
import logging

from telegram.ext import Application

from vinted_bot.config.settings import Config
from vinted_bot.analytics.stats import BotStats
from vinted_bot.telegram_bot.notifier import TelegramNotifier
from vinted_bot.telegram_bot.panel import TelegramPanel
from vinted_bot.core.engine import BotEngine
from vinted_bot.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def get_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"❌ Variable d'environnement manquante : {key}")
    return val


async def post_init(app: Application) -> None:
    """Hook appelé après initialisation de l'application Telegram."""
    config: Config       = app.bot_data["config"]
    stats: BotStats      = app.bot_data["stats"]
    notifier: TelegramNotifier = app.bot_data["notifier"]
    engine: BotEngine    = app.bot_data["engine"]

    # Démarrer les workers
    notifier.start()
    engine.start()

    # Message de bienvenue
    mode_desc = {
        "ultra":  "⚡ Ultra low latency",
        "safe":   "🛡 Safe mode",
        "pro":    "💼 Pro resell",
        "normal": "⚙️ Normal",
    }.get(config.mode, config.mode)

    await notifier.send_now(
        f"🤖 <b>Vinted Bot démarré !</b>\n\n"
        f"Mode : {mode_desc}\n"
        f"🏷️ {len(config.marques)} marques chargées\n"
        f"⏱️ Cooldown : {config.cooldown_sec}s\n"
        f"🎯 Score min : {config.score_min}/100\n"
        f"💶 Budget : {config.prix_min}€ – {config.prix_max}€\n\n"
        f"{'✅ Scan actif' if config.actif else '⛔ En pause — tape /start pour lancer'}\n\n"
        f"👉 <b>/bot</b> pour ouvrir le panel interactif\n"
        f"👉 <b>/status</b> pour voir les stats"
    )
    logger.info("Bot prêt. actif=%s, mode=%s", config.actif, config.mode)


async def post_shutdown(app: Application) -> None:
    engine: BotEngine = app.bot_data["engine"]
    notifier: TelegramNotifier = app.bot_data["notifier"]
    await engine.stop()
    await notifier.stop()
    logger.info("Shutdown propre effectué.")


def main() -> None:
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    token   = get_env("TELEGRAM_TOKEN")
    chat_id = get_env("TELEGRAM_CHAT_ID")

    # ── Chargement de la config ───────────────────────────────────────────────
    config = Config.load()
    stats  = BotStats()

    # ── Construction de l'app Telegram ───────────────────────────────────────
    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── Injection des dépendances via bot_data ────────────────────────────────
    notifier = TelegramNotifier(bot=app.bot, chat_id=chat_id, config=config)
    engine   = BotEngine(config=config, notifier=notifier, stats=stats)
    panel    = TelegramPanel(config=config, stats=stats, notifier=notifier)

    app.bot_data["config"]   = config
    app.bot_data["stats"]    = stats
    app.bot_data["notifier"] = notifier
    app.bot_data["engine"]   = engine

    # ── Enregistrement des handlers ───────────────────────────────────────────
    panel.register(app)

    logger.info("Démarrage du polling Telegram…")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
