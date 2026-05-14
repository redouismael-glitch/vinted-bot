import requests
import time
import os
import asyncio
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise EnvironmentError("❌ TELEGRAM_TOKEN manquant.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquant.")

# ══════════════════════════════════════════════════════════════════════════════
#  MARQUES & RÈGLES
# ══════════════════════════════════════════════════════════════════════════════
TOUTES_LES_MARQUES = {
    "chrome hearts", "hellstar", "denim tears", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "broken planet", "minus two", "no faith studios",
    "corteiz", "crtz", "syna world", "trapstar", "vicinity", "represent",
    "fear of god", "essentials", "off-white", "palm angels", "misbhv",
    "a-cold-wall", "a cold wall", "vivienne westwood",
    "nike", "adidas", "new balance", "stone island", "cp company", "c.p. company",
    "north face", "the north face", "ralph lauren", "polo ralph lauren",
    "lacoste", "carhartt", "levi's", "levis", "moncler", "stussy", "stüssy",
    "arc'teryx", "arcteryx", "patagonia", "supreme", "palace", "jordan",
    "air jordan", "yeezy", "bape", "a bathing ape", "kith",
    "zara", "h&m", "mango", "massimo dutti", "sandro", "maje",
    "ami paris", "jacquemus", "diesel", "calvin klein", "tommy hilfiger",
    "dickies", "uniqlo", "birkenstock", "asics", "sezane", "sézane",
    "puma", "reebok", "converse", "vans", "saucony", "salomon",
    "canada goose", "napapijri", "columbia", "balenciaga", "gucci",
    "burberry", "prada", "dior", "louis vuitton", "acne studios",
    "a.p.c", "apc", "fred perry", "hugo boss",
}

KEYWORDS_HYPE = {
    "vintage", "deadstock", "ds", "vnds", "rare", "limited", "collab",
    "og", "retro", "dunk", "air max", "air force", "jordan 1", "jordan 4",
    "jordan 11", "350", "990", "2002r", "550", "travis", "sacai", "fragment",
}

KEYWORDS_EXCLUS = {
    "lot de", "pack", "déguisement", "costume", "bébé", "enfant",
    "fille", "garçon", "chaussettes", "sous-vêtement",
}

# Marques avec bonus hype pour le score /100
MARQUES_HYPE_BONUS = {
    "chrome hearts", "hellstar", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "corteiz", "crtz", "supreme", "palace",
    "off-white", "fear of god", "trapstar", "broken planet", "syna world",
    "yeezy", "bape", "jordan", "air jordan", "represent", "minus two",
}

REGLES_MARGE = {
    "chrome hearts":     (2.5, 30), "hellstar":          (2.5, 25),
    "gallery dept":      (2.3, 25), "gallery dept.":     (2.3, 25),
    "rick owens":        (2.2, 25), "drkshdw":           (2.2, 25),
    "denim tears":       (2.2, 20), "broken planet":     (2.0, 20),
    "minus two":         (2.0, 20), "trapstar":          (2.0, 20),
    "represent":         (1.9, 18), "fear of god":       (1.9, 20),
    "essentials":        (1.8, 15), "off-white":         (2.0, 25),
    "palm angels":       (1.9, 20), "misbhv":            (1.8, 15),
    "a-cold-wall":       (1.8, 15), "a cold wall":       (1.8, 15),
    "vivienne westwood": (1.9, 20), "corteiz":           (2.2, 20),
    "crtz":              (2.2, 20), "syna world":        (2.0, 18),
    "vicinity":          (1.9, 15), "no faith studios":  (2.0, 15),
    "supreme":           (2.5, 20), "palace":            (2.2, 20),
    "jordan":            (1.8, 15), "air jordan":        (1.8, 15),
    "stone island":      (1.7, 15), "cp company":        (1.7, 15),
    "c.p. company":      (1.7, 15), "balenciaga":        (1.7, 20),
    "arc'teryx":         (1.7, 20), "arcteryx":          (1.7, 20),
    "moncler":           (1.7, 25), "canada goose":      (1.6, 20),
    "north face":        (1.5, 10), "the north face":    (1.5, 10),
    "napapijri":         (1.5, 10), "nike":              (1.5, 10),
    "adidas":            (1.5, 10), "new balance":       (1.5, 10),
    "ralph lauren":      (1.5, 10), "jacquemus":         (1.6, 12),
    "ami paris":         (1.5, 12), "sandro":            (1.5, 10),
    "maje":              (1.4,  8), "lacoste":           (1.4,  8),
    "tommy hilfiger":    (1.4,  8), "carhartt":          (1.4,  8),
    "levi's":            (1.3,  8), "levis":             (1.3,  8),
    "diesel":            (1.4,  8), "calvin klein":      (1.3,  6),
    "birkenstock":       (1.4,  8), "asics":             (1.4,  8),
    "zara":              (1.3,  5), "uniqlo":            (1.3,  5),
    "_defaut":           (1.4,  8),
}

SEARCH_QUERIES = [
    "nike", "adidas", "jordan", "new balance", "stone island",
    "lacoste", "ralph lauren", "tommy hilfiger", "supreme", "palace",
    "corteiz", "north face", "carhartt", "stussy", "yeezy",
    "arc'teryx", "moncler", "cp company", "napapijri", "hellstar",
    "chrome hearts", "rick owens", "broken planet", "trapstar",
    "represent", "fear of god", "off-white", "palm angels",
    "gallery dept", "vivienne westwood", "syna world", "minus two",
]

# ══════════════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
config = {
    "actif":        False,
    "cooldown":     30,       # secondes
    "prix_min":     3.0,
    "prix_max":     200.0,
    "score_min":    60,       # score /100 minimum pour alerter
    "marques":      set(TOUTES_LES_MARQUES),
}
seen_ids: set = set()

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def _make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    try:
        s.get("https://www.vinted.fr", timeout=10)
    except Exception:
        pass
    return s

_session = _make_session()

def _fetch_sync(query: str) -> list:
    global _session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/catalog",
        "X-Requested-With": "XMLHttpRequest",
    }
    url = (
        f"https://www.vinted.fr/api/v2/catalog/items"
        f"?search_text={requests.utils.quote(query)}&per_page=20&order=newest_first"
    )
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ fetch '{query}': {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  SCORE /100 INTELLIGENT
# ══════════════════════════════════════════════════════════════════════════════
def calculer_score(prix, revente, marge, marque, titre) -> int:
    """
    Score /100 basé sur :
    - ratio marge/prix          → 0-45 pts
    - marge absolue             → 0-20 pts
    - bonus marque hype         → 0-15 pts
    - bonus keywords hype       → 0-10 pts
    - bonus sous-côte extrême   → 0-10 pts
    """
    t = titre.lower()
    score = 0

    # 1. Ratio marge/prix (plus c'est sous-côté, plus le score monte)
    ratio = marge / prix if prix > 0 else 0
    score += min(45, int(ratio * 70))

    # 2. Marge absolue
    if marge >= 100: score += 20
    elif marge >= 50: score += 15
    elif marge >= 30: score += 10
    elif marge >= 20: score += 7
    elif marge >= 10: score += 4

    # 3. Bonus marque hype
    if marque in MARQUES_HYPE_BONUS:
        score += 15
    elif marque in REGLES_MARGE and REGLES_MARGE[marque][0] >= 1.8:
        score += 8

    # 4. Bonus keywords hype dans le titre
    hype_count = sum(1 for k in KEYWORDS_HYPE if k in t)
    score += min(10, hype_count * 4)

    # 5. Bonus sous-côte extrême (prix très bas par rapport à revente)
    if revente > prix * 3:
        score += 10
    elif revente > prix * 2.5:
        score += 6

    return min(100, score)

def niveau_affaire(score: int) -> str:
    if score >= 90: return "💎 PÉPITE EXTRÊME"
    if score >= 78: return "🔥🔥🔥 ÉNORME AFFAIRE"
    if score >= 65: return "🔥🔥 TRÈS BONNE AFFAIRE"
    if score >= 50: return "🔥 BONNE AFFAIRE"
    return "👍 AFFAIRE CORRECTE"

# ══════════════════════════════════════════════════════════════════════════════
#  FILTRAGE & ANALYSE
# ══════════════════════════════════════════════════════════════════════════════
def extraire_prix(item):
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None

def detecter_marque(titre, marque_vinted):
    t = titre.lower()
    m = marque_vinted.lower().strip()
    for marque in config["marques"]:
        if marque in m or marque in t:
            return marque
    return None

def analyser(item):
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?")
    prix       = extraire_prix(item)
    item_id    = item.get("id")
    t          = titre.lower()

    if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
        return False, {}
    if any(mot in t for mot in KEYWORDS_EXCLUS):
        return False, {}

    marque = detecter_marque(titre, marque_raw)
    if marque is None:
        if not any(k in t for k in KEYWORDS_HYPE):
            return False, {}
        marque = "_defaut"

    coef, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
    revente = round(prix * coef, 2)
    marge   = round(revente * 0.90 - prix, 2)
    if marge < marge_min:
        return False, {}

    score = calculer_score(prix, revente, marge, marque, titre)

    if score < config["score_min"]:
        return False, {}

    return True, {
        "titre":   titre,
        "marque":  marque_raw or marque,
        "taille":  taille,
        "prix":    prix,
        "revente": revente,
        "marge":   marge,
        "score":   score,
        "niveau":  niveau_affaire(score),
        "url":     f"https://www.vinted.fr/items/{item_id}",
    }

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN
# ══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    loop = asyncio.get_event_loop()

    while True:
        if not config["actif"]:
            await asyncio.sleep(3)
            continue

        print(f"\n🔍 Scan — {time.strftime('%H:%M:%S')}")
        alertes = 0

        for query in SEARCH_QUERIES:
            if not config["actif"]:
                break
            try:
                items = await loop.run_in_executor(None, _fetch_sync, query)
            except Exception as e:
                print(f"❌ Executor: {e}")
                items = []

            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                # Libère mémoire si trop d'IDs
                if len(seen_ids) > 50000:
                    seen_ids.clear()

                ok, d = analyser(item)
                if not ok:
                    continue

                alertes += 1
                msg = (
                    f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
                    f"👕 <b>{d['titre']}</b>\n"
                    f"🏷️ Marque : {d['marque']}\n"
                    f"📐 Taille : {d['taille']}\n"
                    f"💶 Prix achat : {d['prix']}€\n"
                    f"📈 Revente estimée : ~{d['revente']}€\n"
                    f"💰 Marge nette : ~{d['marge']}€\n\n"
                    f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
                )
                print(f"  🚨 {d['titre'][:45]} | score {d['score']}/100 | marge ~{d['marge']}€")
                try:
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                    )
                except Exception as e:
                    print(f"❌ Telegram: {e}")
                await asyncio.sleep(0.5)

            await asyncio.sleep(2)

        print(f"✅ Scan terminé — {alertes} alertes | prochain dans {config['cooldown']}s")

        # Cooldown en secondes — réactif au stop/pause
        elapsed = 0
        while elapsed < config["cooldown"]:
            if not config["actif"]:
                break
            await asyncio.sleep(1)
            elapsed += 1

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL /bot — BOUTONS INLINE
# ══════════════════════════════════════════════════════════════════════════════
def build_panel_keyboard():
    etat_btn  = "⏸ Pause" if config["actif"] else "▶️ Start"
    etat_cb   = "panel_pause" if config["actif"] else "panel_start"
    score_min = config["score_min"]

    keyboard = [
        [
            InlineKeyboardButton(etat_btn, callback_data=etat_cb),
            InlineKeyboardButton("⏹ Stop", callback_data="panel_stop"),
        ],
        [
            InlineKeyboardButton("⏱ Cooldown 10s",  callback_data="cd_10"),
            InlineKeyboardButton("⏱ Cooldown 30s",  callback_data="cd_30"),
            InlineKeyboardButton("⏱ Cooldown 60s",  callback_data="cd_60"),
        ],
        [
            InlineKeyboardButton("⏱ Cooldown 2min", callback_data="cd_120"),
            InlineKeyboardButton("⏱ Cooldown 5min", callback_data="cd_300"),
        ],
        [
            InlineKeyboardButton("💶 Budget 5–50€",   callback_data="budget_5_50"),
            InlineKeyboardButton("💶 Budget 5–100€",  callback_data="budget_5_100"),
            InlineKeyboardButton("💶 Budget 5–200€",  callback_data="budget_5_200"),
        ],
        [
            InlineKeyboardButton(f"🎯 Score min: {score_min}/100 ▼", callback_data="score_down"),
            InlineKeyboardButton(f"🎯 Score min: {score_min}/100 ▲", callback_data="score_up"),
        ],
        [
            InlineKeyboardButton("🔄 Actualiser", callback_data="panel_refresh"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_panel_text():
    etat   = "✅ Actif" if config["actif"] else "⏸ En pause"
    return (
        f"🤖 <b>Panel Vinted Bot</b>\n\n"
        f"État : {etat}\n"
        f"⏱️ Cooldown : <b>{config['cooldown']}s</b>\n"
        f"💶 Budget : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"🎯 Score minimum : <b>{config['score_min']}/100</b>\n"
        f"🏷️ Marques actives : <b>{len(config['marques'])}</b>\n\n"
        f"<i>Utilise les boutons pour tout contrôler.</i>"
    )

async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_panel_text(),
        reply_markup=build_panel_keyboard(),
        parse_mode="HTML",
    )

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "panel_start":
        config["actif"] = True

    elif data == "panel_pause":
        config["actif"] = False

 elif data == "panel_stop":
    config["actif"] = False
    await query.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer automatiquement.")
    sys.exit(0)

    elif data == "panel_refresh":
        pass  # juste rafraîchir l'affichage

    elif data.startswith("cd_"):
        config["cooldown"] = int(data.split("_")[1])

    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"] = float(pmin)
        config["prix_max"] = float(pmax)

    elif data == "score_up":
        config["score_min"] = min(95, config["score_min"] + 5)

    elif data == "score_down":
        config["score_min"] = max(30, config["score_min"] - 5)

    # Mise à jour du panel
    try:
        await query.edit_message_text(
            build_panel_text(),
            reply_markup=build_panel_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TEXTE (gardées pour compatibilité)
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("⏸ <b>Scan mis en pause.</b>\nTape /start pour relancer.", parse_mode="HTML")

async def cmd_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        secondes = int(ctx.args[0])
        assert secondes >= 1
        config["cooldown"] = secondes
        await update.message.reply_text(f"⏱️ Cooldown : <b>{secondes}s</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /cooldown &lt;secondes&gt;  ex: /cooldown 30")

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
    await update.message.reply_text(
        f"<b>📊 Status</b>\n\n"
        f"État : {etat}\n"
        f"⏱️ Cooldown : {config['cooldown']}s\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
        f"🎯 Score min : {config['score_min']}/100\n"
        f"🏷️ Marques : {len(config['marques'])}\n\n"
        "👉 Tape /bot pour le panel interactif",
        parse_mode="HTML"
    )

async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        action = ctx.args[0].lower()
    except IndexError:
        await update.message.reply_text("Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n/marque reset\n/marque list")
        return

    if action == "reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        await update.message.reply_text(f"✅ {len(config['marques'])} marques réactivées.")
    elif action == "list":
        texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"]))
        await update.message.reply_text(texte[:4000], parse_mode="HTML")
    elif action in ("add", "remove"):
        nom = " ".join(ctx.args[1:]).lower().strip()
        if not nom:
            await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;")
            return
        if action == "add":
            config["marques"].add(nom)
            await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
        else:
            config["marques"].discard(nom)
            await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list")

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
async def post_init(app: Application):
    asyncio.create_task(boucle_scan(app))
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=(
            "🤖 <b>Bot Vinted prêt !</b>\n\n"
            f"🏷️ {len(config['marques'])} marques chargées\n"
            f"⏱️ Cooldown : {config['cooldown']}s\n"
            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
            f"🎯 Score min : {config['score_min']}/100\n\n"
            "👉 Tape /bot pour ouvrir le panel\n"
            "👉 Tape /start pour lancer le scan"
        ),
        parse_mode="HTML",
    )

def main():
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("bot",      cmd_bot))
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("cooldown", cmd_cooldown))
    app.add_handler(CommandHandler("budget",   cmd_budget))
    app.add_handler(CommandHandler("marque",   cmd_marque))
    app.add_handler(CommandHandler("status",   cmd_status))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("📡 Bot en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
