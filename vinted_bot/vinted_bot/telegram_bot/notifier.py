"""
telegram_bot/notifier.py
Envoi Telegram avec :
- queue async (évite le spam)
- rate limiting (1 message / 0.5s par défaut)
- retry sur FloodWait
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Bot
from telegram.error import RetryAfter, TelegramError

from ..config.settings import Config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot: Bot, chat_id: str, config: Config):
        self.bot = bot
        self.chat_id = chat_id
        self.config = config
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        """Démarre le worker de la queue."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker(), name="telegram_notifier")

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def send(self, text: str) -> None:
        """Ajoute un message à la queue (non-bloquant)."""
        await self._queue.put(text)

    async def send_now(self, text: str) -> bool:
        """Envoi immédiat, sans passer par la queue."""
        return await self._send_raw(text)

    async def _send_raw(self, text: str) -> bool:
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )
            return True
        except RetryAfter as e:
            logger.warning("Telegram FloodWait : pause %ds", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self._send_raw(text)  # retry une fois
        except TelegramError as e:
            logger.error("TelegramError : %s", e)
            return False
        except Exception as e:
            logger.error("Erreur envoi Telegram inattendue : %s", e)
            return False

    async def _worker(self) -> None:
        """Consomme la queue avec rate limiting."""
        logger.debug("Notifier worker démarré.")
        while True:
            try:
                text = await self._queue.get()
                await self._send_raw(text)
                self._queue.task_done()
                await asyncio.sleep(self.config.telegram_min_interval_sec)
            except asyncio.CancelledError:
                logger.debug("Notifier worker arrêté.")
                break
            except Exception as e:
                logger.error("Erreur worker notifier : %s", e)
                await asyncio.sleep(1.0)
