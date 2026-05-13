import requests
import time
import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
    "actif":    False,   # démarre en pause, /start pour lancer
    "cooldown": 15,
    "prix_min": 3.0,
    "prix_max": 200.0,
    "marques":  set(TOUTES_LES_MARQUES),
}
seen_ids: set = set()
scan_task: asyncio.Task | None = None

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER (exécuté dans un executor pour ne pas bloquer l'event loop)
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
    """Requête Vinted synchrone — appelée via run_in_executor."""
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
#  FILTRAGE
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

    ratio = marge / prix if prix > 0 else 0
    score = (
        "🔥🔥🔥 Excellente affaire" if ratio >= 0.5 else
        "🔥🔥 Très bonne affaire"   if ratio >= 0.3 else
        "🔥 Bonne affaire"          if ratio >= 0.15 else
        "👍 Affaire correcte"
    )
    return True, {
        "titre": titre, "marque": marque_raw or marque,
        "taille": taille, "prix": prix,
        "revente": revente, "marge": marge, "score": score,
        "url": f"https://www.vinted.fr/items/{item_id}",
    }

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN (tâche asyncio permanente)
# ══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    """Tourne indéfiniment. Respecte config['actif'] et config['cooldown']."""
    loop = asyncio.get_event_loop()

    while True:
        if not config["actif"]:
            await asyncio.sleep(5)   # vérifie toutes les 5s si /start est tapé
            continue

        print(f"\n🔍 Scan — {time.strftime('%H:%M:%S')}")
        alertes = 0

        for query in SEARCH_QUERIES:
            if not config["actif"]:
                break
            try:
                items = await loop.run_in_executor(None, _fetch_sync, query)
            except Exception as e:
                print(f"❌ Executor error: {e}")
                items = []

            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                ok, d = analyser(item)
                if not ok:
                    continue

                alertes += 1
                msg = (
                    f"{d['score']}\n\n"
                    f"👕 <b>{d['titre']}</b>\n"
                    f"🏷️ Marque : {d['marque']}\n"
                    f"📐 Taille : {d['taille']}\n"
                    f"💶 Prix achat : {d['prix']}€\n"
                    f"📈 Revente estimée : ~{d['revente']}€\n"
                    f"💰 Marge nette : ~{d['marge']}€\n\n"
                    f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
                )
                print(f"  🚨 {d['titre'][:45]} | marge ~{d['marge']}€")
                try:
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=msg,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                    )
                except Exception as e:
                    print(f"❌ Telegram send error: {e}")
                await asyncio.sleep(0.5)

            await asyncio.sleep(2)  # pause polie entre requêtes Vinted

        print(f"✅ Scan terminé — {alertes} alertes | prochain dans {config['cooldown']} min")
        # Attente cooldown — en petits morceaux pour rester réactif à /stop
        for _ in range(config["cooldown"] * 60 // 5):
            if not config["actif"]:
                break
            await asyncio.sleep(5)

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text(
        "✅ <b>Bot activé !</b>\n"
        f"⏱️ Cooldown : {config['cooldown']} min\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
        f"🏷️ Marques actives : {len(config['marques'])}",
        parse_mode="HTML"
    )

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text(
        "⛔ <b>Bot mis en pause.</b>\nTape /start pour relancer.",
        parse_mode="HTML"
    )

async def cmd_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        minutes = int(ctx.args[0])
        assert minutes >= 1
        config["cooldown"] = minutes
        await update.message.reply_text(
            f"⏱️ Cooldown mis à jour : <b>{minutes} min</b>", parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ Usage : /cooldown &lt;minutes&gt;  ex: /cooldown 10")

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(
            f"💶 Budget mis à jour : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        action = ctx.args[0].lower()
    except IndexError:
        await update.message.reply_text(
            "Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n"
            "/marque reset\n/marque list"
        )
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

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    etat = "✅ Actif" if config["actif"] else "⛔ En pause"
    await update.message.reply_text(
        f"<b>📊 Status</b>\n\n"
        f"État : {etat}\n"
        f"⏱️ Cooldown : {config['cooldown']} min\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
        f"🏷️ Marques : {len(config['marques'])}\n\n"
        "<b>Commandes :</b>\n"
        "/start — activer le scan\n"
        "/stop — mettre en pause\n"
        "/cooldown &lt;min&gt;\n"
        "/budget &lt;min&gt; &lt;max&gt;\n"
        "/marque add|remove|reset|list\n"
        "/status",
        parse_mode="HTML"
    )

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
            f"⏱️ Cooldown : {config['cooldown']} min\n"
            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n\n"
            "👉 Tape /start pour lancer le scan\n\n"
            "<b>Toutes les commandes :</b>\n"
            "/start — lancer\n"
            "/stop — pause\n"
            "/cooldown 10 — intervalle en minutes\n"
            "/budget 5 150 — fourchette de prix\n"
            "/marque add hellstar\n"
            "/marque remove zara\n"
            "/marque list\n"
            "/marque reset\n"
            "/status"
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
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("cooldown", cmd_cooldown))
    app.add_handler(CommandHandler("budget",   cmd_budget))
    app.add_handler(CommandHandler("marque",   cmd_marque))
    app.add_handler(CommandHandler("status",   cmd_status))

    print("📡 Bot en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
