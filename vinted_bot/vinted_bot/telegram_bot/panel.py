"""
telegram_bot/panel.py
Panel de contrôle Telegram avec inline keyboard buttons.
Commandes + boutons interactifs.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
)

from ..config.settings import Config, DEFAULT_MARQUES
from ..analytics.stats import BotStats

if TYPE_CHECKING:
    from ..telegram_bot.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def _main_keyboard(config: Config) -> InlineKeyboardMarkup:
    """Clavier principal du panel /bot."""
    etat_btn = "⏸ Pause" if config.actif else "▶️ Start"
    etat_cb  = "pause"   if config.actif else "start"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(etat_btn, callback_data=etat_cb),
            InlineKeyboardButton("📊 Stats",  callback_data="stats"),
        ],
        [
            InlineKeyboardButton("⚡ Mode Ultra",  callback_data="mode_ultra"),
            InlineKeyboardButton("🛡 Mode Safe",   callback_data="mode_safe"),
            InlineKeyboardButton("⚙️ Mode Normal", callback_data="mode_normal"),
        ],
        [
            InlineKeyboardButton("⏱ Cooldown –5min", callback_data="cd_minus"),
            InlineKeyboardButton(f"⏱ {config.cooldown_sec//60}min", callback_data="cd_info"),
            InlineKeyboardButton("⏱ Cooldown +5min", callback_data="cd_plus"),
        ],
        [
            InlineKeyboardButton("🎯 Score –5",  callback_data="score_minus"),
            InlineKeyboardButton(f"🎯 Score ≥{config.score_min}", callback_data="score_info"),
            InlineKeyboardButton("🎯 Score +5",  callback_data="score_plus"),
        ],
        [
            InlineKeyboardButton("🏷 Marques", callback_data="marques_menu"),
            InlineKeyboardButton("💶 Budget",  callback_data="budget_info"),
        ],
    ])


def _marques_keyboard() -> InlineKeyboardMarkup:
    """Sous-menu marques."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Toutes les marques", callback_data="marques_reset"),
        ],
        [
            InlineKeyboardButton("🔥 Hype only",    callback_data="marques_hype"),
            InlineKeyboardButton("👟 Sport only",   callback_data="marques_sport"),
        ],
        [
            InlineKeyboardButton("◀️ Retour", callback_data="back_main"),
        ],
    ])


HYPE_BRANDS = {
    "chrome hearts", "hellstar", "gallery dept", "rick owens", "denim tears",
    "broken planet", "minus two", "trapstar", "represent", "fear of god",
    "essentials", "off-white", "palm angels", "corteiz", "crtz", "syna world",
    "vicinity", "no faith studios", "supreme", "palace", "misbhv",
    "a-cold-wall", "vivienne westwood", "bape", "a bathing ape",
}

SPORT_BRANDS = {
    "nike", "adidas", "jordan", "air jordan", "new balance", "puma",
    "reebok", "asics", "converse", "vans", "saucony", "salomon",
    "arc'teryx", "arcteryx", "north face", "the north face", "patagonia",
    "napapijri", "canada goose", "moncler", "stone island", "cp company",
    "c.p. company", "carhartt",
}


class TelegramPanel:
    def __init__(self, config: Config, stats: BotStats, notifier: "TelegramNotifier"):
        self.config = config
        self.stats = stats
        self.notifier = notifier

    def register(self, app: Application) -> None:
        app.add_handler(CommandHandler("bot",      self.cmd_bot))
        app.add_handler(CommandHandler("start",    self.cmd_start))
        app.add_handler(CommandHandler("stop",     self.cmd_stop))
        app.add_handler(CommandHandler("status",   self.cmd_status))
        app.add_handler(CommandHandler("cooldown", self.cmd_cooldown))
        app.add_handler(CommandHandler("budget",   self.cmd_budget))
        app.add_handler(CommandHandler("score",    self.cmd_score))
        app.add_handler(CommandHandler("marque",   self.cmd_marque))
        app.add_handler(CommandHandler("mode",     self.cmd_mode))
        app.add_handler(CallbackQueryHandler(self.handle_callback))

    # ── Commandes texte ───────────────────────────────────────────────────────

    async def cmd_bot(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Panel principal avec boutons."""
        etat = "✅ Actif" if self.config.actif else "⛔ En pause"
        text = (
            f"<b>🤖 Panel Vinted Bot</b>\n\n"
            f"État : {etat}\n"
            f"Mode : {self.config.mode}\n"
            f"⏱️ Cooldown : {self.config.cooldown_sec // 60}min\n"
            f"🎯 Score min : {self.config.score_min}/100\n"
            f"💶 Budget : {self.config.prix_min}€ – {self.config.prix_max}€\n"
            f"🏷️ Marques : {len(self.config.marques)}\n"
        )
        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=_main_keyboard(self.config),
        )

    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        self.config.actif = True
        self.config.save()
        await update.message.reply_text(
            "✅ <b>Scan activé !</b>", parse_mode="HTML",
            reply_markup=_main_keyboard(self.config),
        )

    async def cmd_stop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        self.config.actif = False
        self.config.save()
        await update.message.reply_text(
            "⛔ <b>Scan mis en pause.</b>", parse_mode="HTML",
            reply_markup=_main_keyboard(self.config),
        )

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        etat = "✅ Actif" if self.config.actif else "⛔ En pause"
        text = (
            f"<b>📊 Status</b>\n\n"
            f"État : {etat} | Mode : {self.config.mode}\n"
            f"⏱️ Cooldown : {self.config.cooldown_sec}s\n"
            f"🎯 Score min : {self.config.score_min}/100\n"
            f"💶 Budget : {self.config.prix_min}€ – {self.config.prix_max}€\n"
            f"🏷️ Marques : {len(self.config.marques)}\n\n"
            f"{self.stats.summary()}\n\n"
            f"<b>Commandes :</b>\n"
            f"/bot — panel interactif\n"
            f"/start /stop\n"
            f"/cooldown &lt;sec&gt;\n"
            f"/budget &lt;min&gt; &lt;max&gt;\n"
            f"/score &lt;0-100&gt;\n"
            f"/mode ultra|safe|pro|normal\n"
            f"/marque add|remove|reset|list|hype|sport\n"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def cmd_cooldown(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        try:
            secs = int(ctx.args[0])
            assert secs >= 30
            self.config.cooldown_sec = secs
            self.config.save()
            await update.message.reply_text(
                f"⏱️ Cooldown : <b>{secs}s ({secs//60}min)</b>", parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("❌ Usage : /cooldown &lt;secondes&gt;  ex: /cooldown 600")

    async def cmd_budget(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        try:
            pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
            assert 0 <= pmin < pmax
            self.config.prix_min, self.config.prix_max = pmin, pmax
            self.config.save()
            await update.message.reply_text(
                f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

    async def cmd_score(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        try:
            s = int(ctx.args[0])
            assert 0 <= s <= 100
            self.config.score_min = s
            self.config.save()
            await update.message.reply_text(
                f"🎯 Score minimum : <b>{s}/100</b>", parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("❌ Usage : /score &lt;0-100&gt;  ex: /score 40")

    async def cmd_mode(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        try:
            mode = ctx.args[0].lower()
            assert mode in ("ultra", "safe", "pro", "normal")
            self.config.apply_mode(mode)
            await update.message.reply_text(
                f"⚙️ Mode activé : <b>{mode}</b>\n"
                f"⏱ Cooldown : {self.config.cooldown_sec}s\n"
                f"🎯 Score min : {self.config.score_min}",
                parse_mode="HTML",
            )
        except Exception:
            await update.message.reply_text("❌ Usage : /mode ultra|safe|pro|normal")

    async def cmd_marque(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        try:
            action = ctx.args[0].lower()
        except IndexError:
            await update.message.reply_text(
                "Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n"
                "/marque reset\n/marque list\n/marque hype\n/marque sport"
            )
            return

        if action == "reset":
            self.config.marques = set(DEFAULT_MARQUES)
            self.config.save()
            await update.message.reply_text(f"✅ {len(self.config.marques)} marques réactivées.")
        elif action == "hype":
            self.config.marques = set(HYPE_BRANDS)
            self.config.save()
            await update.message.reply_text(f"🔥 Mode hype : {len(self.config.marques)} marques.")
        elif action == "sport":
            self.config.marques = set(SPORT_BRANDS)
            self.config.save()
            await update.message.reply_text(f"👟 Mode sport : {len(self.config.marques)} marques.")
        elif action == "list":
            texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(self.config.marques))
            await update.message.reply_text(texte[:4000], parse_mode="HTML")
        elif action in ("add", "remove"):
            nom = " ".join(ctx.args[1:]).lower().strip()
            if not nom:
                await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;")
                return
            if action == "add":
                self.config.marques.add(nom)
                await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
            else:
                self.config.marques.discard(nom)
                await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
            self.config.save()
        else:
            await update.message.reply_text("❌ Action : add | remove | reset | list | hype | sport")

    # ── Callbacks boutons ─────────────────────────────────────────────────────

    async def handle_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "start":
            self.config.actif = True
            self.config.save()
        elif data == "pause":
            self.config.actif = False
            self.config.save()
        elif data == "stats":
            await query.message.reply_text(
                f"<b>📊 Stats live</b>\n\n{self.stats.summary()}",
                parse_mode="HTML",
            )
            return
        elif data.startswith("mode_"):
            mode = data.split("_")[1]
            self.config.apply_mode(mode)
        elif data == "cd_minus":
            self.config.cooldown_sec = max(60, self.config.cooldown_sec - 300)
            self.config.save()
        elif data == "cd_plus":
            self.config.cooldown_sec = min(7200, self.config.cooldown_sec + 300)
            self.config.save()
        elif data == "score_minus":
            self.config.score_min = max(0, self.config.score_min - 5)
            self.config.save()
        elif data == "score_plus":
            self.config.score_min = min(100, self.config.score_min + 5)
            self.config.save()
        elif data == "marques_menu":
            await query.edit_message_reply_markup(_marques_keyboard())
            return
        elif data == "marques_reset":
            self.config.marques = set(DEFAULT_MARQUES)
            self.config.save()
        elif data == "marques_hype":
            self.config.marques = set(HYPE_BRANDS)
            self.config.save()
        elif data == "marques_sport":
            self.config.marques = set(SPORT_BRANDS)
            self.config.save()
        elif data == "back_main":
            pass  # on rafraîchit juste le clavier principal
        elif data in ("cd_info", "score_info", "budget_info"):
            return  # bouton informatif, ne fait rien

        # Rafraîchir le panel
        etat = "✅ Actif" if self.config.actif else "⛔ En pause"
        text = (
            f"<b>🤖 Panel Vinted Bot</b>\n\n"
            f"État : {etat}\n"
            f"Mode : {self.config.mode}\n"
            f"⏱️ Cooldown : {self.config.cooldown_sec // 60}min\n"
            f"🎯 Score min : {self.config.score_min}/100\n"
            f"💶 Budget : {self.config.prix_min}€ – {self.config.prix_max}€\n"
            f"🏷️ Marques : {len(self.config.marques)}\n"
        )
        try:
            await query.edit_message_text(
                text, parse_mode="HTML",
                reply_markup=_main_keyboard(self.config),
            )
        except Exception:
            pass  # message non modifié si identique
