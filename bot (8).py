import requests
import time
import os
import asyncio
import threading
from telegram import Bot, Update
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
#  MARQUES
# ══════════════════════════════════════════════════════════════════════════════
TOUTES_LES_MARQUES = {
    # Hype / Streetwear
    "chrome hearts", "hellstar", "denim tears", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "broken planet", "minus two", "no faith studios",
    "corteiz", "crtz", "syna world", "trapstar", "vicinity", "represent",
    "fear of god", "essentials", "off-white", "palm angels", "misbhv",
    "a-cold-wall", "a cold wall", "vivienne westwood",
    # Sportswear / Premium
    "nike", "adidas", "new balance", "stone island", "cp company", "c.p. company",
    "north face", "the north face", "ralph lauren", "polo ralph lauren",
    "lacoste", "carhartt", "levi's", "levis", "moncler", "stussy", "stüssy",
    "arc'teryx", "arcteryx", "patagonia", "supreme", "palace", "jordan",
    "air jordan", "yeezy", "bape", "a bathing ape", "kith",
    # Grandes enseignes revendables
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
    "chrome hearts":  (2.5, 30),
    "hellstar":       (2.5, 25),
    "gallery dept":   (2.3, 25),
    "gallery dept.":  (2.3, 25),
    "rick owens":     (2.2, 25),
    "drkshdw":        (2.2, 25),
    "denim tears":    (2.2, 20),
    "broken planet":  (2.0, 20),
    "minus two":      (2.0, 20),
    "trapstar":       (2.0, 20),
    "represent":      (1.9, 18),
    "fear of god":    (1.9, 20),
    "essentials":     (1.8, 15),
    "off-white":      (2.0, 25),
    "palm angels":    (1.9, 20),
    "misbhv":         (1.8, 15),
    "a-cold-wall":    (1.8, 15),
    "a cold wall":    (1.8, 15),
    "vivienne westwood": (1.9, 20),
    "corteiz":        (2.2, 20),
    "crtz":           (2.2, 20),
    "syna world":     (2.0, 18),
    "vicinity":       (1.9, 15),
    "no faith studios": (2.0, 15),
    "supreme":        (2.5, 20),
    "palace":         (2.2, 20),
    "jordan":         (1.8, 15),
    "air jordan":     (1.8, 15),
    "stone island":   (1.7, 15),
    "cp company":     (1.7, 15),
    "c.p. company":   (1.7, 15),
    "balenciaga":     (1.7, 20),
    "arc'teryx":      (1.7, 20),
    "arcteryx":       (1.7, 20),
    "moncler":        (1.7, 25),
    "canada goose":   (1.6, 20),
    "north face":     (1.5, 10),
    "the north face": (1.5, 10),
    "napapijri":      (1.5, 10),
    "nike":           (1.5, 10),
    "adidas":         (1.5, 10),
    "new balance":    (1.5, 10),
    "ralph lauren":   (1.5, 10),
    "jacquemus":      (1.6, 12),
    "ami paris":      (1.5, 12),
    "sandro":         (1.5, 10),
    "maje":           (1.4,  8),
    "lacoste":        (1.4,  8),
    "tommy hilfiger": (1.4,  8),
    "carhartt":       (1.4,  8),
    "levi's":         (1.3,  8),
    "levis":          (1.3,  8),
    "diesel":         (1.4,  8),
    "calvin klein":   (1.3,  6),
    "birkenstock":    (1.4,  8),
    "asics":          (1.4,  8),
    "zara":           (1.3,  5),
    "uniqlo":         (1.3,  5),
    "_defaut":        (1.4,  8),
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
#  ÉTAT GLOBAL (modifiable via commandes Telegram)
# ══════════════════════════════════════════════════════════════════════════════
config = {
    "actif":        True,
    "cooldown":     15,          # minutes entre chaque scan
    "prix_min":     3.0,
    "prix_max":     200.0,
    "marques":      set(TOUTES_LES_MARQUES),  # filtre actif (toutes par défaut)
}

seen_ids: set = set()
scan_thread: threading.Thread | None = None
stop_event = threading.Event()

# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM — envoi simple
# ══════════════════════════════════════════════════════════════════════════════
async def _envoyer(message: str):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=False,
    )

def send_alert(message: str):
    try:
        asyncio.run(_envoyer(message))
    except Exception as e:
        print(f"  ❌ Telegram : {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    stop_event.clear()
    demarrer_scan()
    await update.message.reply_text(
        "✅ <b>Bot démarré !</b>\n"
        f"⏱️ Cooldown : {config['cooldown']} min\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
        f"🏷️ Marques actives : {len(config['marques'])}",
        parse_mode="HTML"
    )

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    stop_event.set()
    await update.message.reply_text("⛔ <b>Bot arrêté.</b>\nUtilise /start pour relancer.", parse_mode="HTML")

async def cmd_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage : /cooldown 10  (en minutes)"""
    try:
        minutes = int(ctx.args[0])
        if minutes < 1:
            raise ValueError
        config["cooldown"] = minutes
        await update.message.reply_text(f"⏱️ Cooldown mis à jour : <b>{minutes} minutes</b>", parse_mode="HTML")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage : /cooldown &lt;minutes&gt;\nEx : /cooldown 10")

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage : /budget 5 150  (prix_min prix_max)"""
    try:
        pmin = float(ctx.args[0])
        pmax = float(ctx.args[1])
        if pmin < 0 or pmax <= pmin:
            raise ValueError
        config["prix_min"] = pmin
        config["prix_max"] = pmax
        await update.message.reply_text(
            f"💶 Budget mis à jour : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;\nEx : /budget 5 150")

async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /marque add supreme      → ajoute une marque
    /marque remove supreme   → retire une marque
    /marque reset            → remet toutes les marques
    /marque list             → liste les marques actives
    """
    try:
        action = ctx.args[0].lower()
    except IndexError:
        await update.message.reply_text(
            "❌ Usage :\n"
            "/marque add &lt;nom&gt;\n"
            "/marque remove &lt;nom&gt;\n"
            "/marque reset\n"
            "/marque list"
        )
        return

    if action == "reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        await update.message.reply_text(f"✅ Toutes les marques réactivées ({len(config['marques'])} marques).")

    elif action == "list":
        liste = sorted(config["marques"])
        texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(liste)
        # Telegram limite à 4096 chars
        if len(texte) > 4000:
            texte = texte[:4000] + "…"
        await update.message.reply_text(texte, parse_mode="HTML")

    elif action in ("add", "remove"):
        try:
            nom = " ".join(ctx.args[1:]).lower().strip()
            if not nom:
                raise IndexError
        except IndexError:
            await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom de la marque&gt;")
            return

        if action == "add":
            config["marques"].add(nom)
            await update.message.reply_text(f"✅ Marque ajoutée : <b>{nom}</b>", parse_mode="HTML")
        else:
            config["marques"].discard(nom)
            await update.message.reply_text(f"🗑️ Marque retirée : <b>{nom}</b>", parse_mode="HTML")

    else:
        await update.message.reply_text("❌ Action inconnue. Utilise : add / remove / reset / list")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    etat = "✅ Actif" if config["actif"] else "⛔ Arrêté"
    await update.message.reply_text(
        f"<b>Status du bot</b>\n\n"
        f"État : {etat}\n"
        f"⏱️ Cooldown : {config['cooldown']} min\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
        f"🏷️ Marques actives : {len(config['marques'])}\n\n"
        f"<b>Commandes disponibles :</b>\n"
        f"/start — démarrer le bot\n"
        f"/stop — arrêter le bot\n"
        f"/cooldown &lt;min&gt; — changer l'intervalle\n"
        f"/budget &lt;min&gt; &lt;max&gt; — changer le budget\n"
        f"/marque add/remove/reset/list — gérer les marques\n"
        f"/status — afficher ce message",
        parse_mode="HTML"
    )

# ══════════════════════════════════════════════════════════════════════════════
#  VINTED SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    })
    try:
        s.get("https://www.vinted.fr", timeout=10)
    except Exception as e:
        print(f"⚠️ Init session : {e}")
    return s

_session: requests.Session = _make_session()

def fetch_vinted(query: str) -> list[dict]:
    global _session
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/catalog",
        "X-Requested-With": "XMLHttpRequest",
    }
    url = (
        f"https://www.vinted.fr/api/v2/catalog/items"
        f"?search_text={requests.utils.quote(query)}"
        f"&per_page=20&order=newest_first"
    )
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠️ Vinted {resp.status_code} pour '{query}'")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"  ❌ fetch '{query}' : {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  FILTRAGE ET MARGE
# ══════════════════════════════════════════════════════════════════════════════
def extraire_prix(item: dict) -> float | None:
    try:
        raw = item.get("price", {})
        if isinstance(raw, dict):
            return float(raw.get("amount", 0))
        return float(raw)
    except (TypeError, ValueError):
        return None

def detecter_marque(titre: str, marque_vinted: str) -> str | None:
    titre_low  = titre.lower()
    marque_low = marque_vinted.lower().strip()
    for m in config["marques"]:
        if m in marque_low or m in titre_low:
            return m
    return None

def calculer_marge(prix_achat: float, marque: str) -> tuple[float, float]:
    coef, _ = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
    prix_revente = round(prix_achat * coef, 2)
    frais        = round(prix_revente * 0.10, 2)
    marge        = round(prix_revente - frais - prix_achat, 2)
    return prix_revente, marge

def est_bonne_affaire(item: dict) -> tuple[bool, dict]:
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?")
    prix       = extraire_prix(item)
    item_id    = item.get("id")
    titre_low  = titre.lower()

    if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
        return False, {}

    for mot in KEYWORDS_EXCLUS:
        if mot in titre_low:
            return False, {}

    marque = detecter_marque(titre, marque_raw)
    if marque is None:
        if not any(k in titre_low for k in KEYWORDS_HYPE):
            return False, {}
        marque = "_defaut"

    _, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
    prix_revente, marge = calculer_marge(prix, marque)
    if marge < marge_min:
        return False, {}

    ratio = marge / prix if prix > 0 else 0
    if ratio >= 0.5:
        score = "🔥🔥🔥 Excellente affaire"
    elif ratio >= 0.3:
        score = "🔥🔥 Très bonne affaire"
    elif ratio >= 0.15:
        score = "🔥 Bonne affaire"
    else:
        score = "👍 Affaire correcte"

    return True, {
        "titre":        titre,
        "marque":       marque_raw or marque,
        "taille":       taille,
        "prix":         prix,
        "prix_revente": prix_revente,
        "marge":        marge,
        "score":        score,
        "url":          f"https://www.vinted.fr/items/{item_id}",
    }

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN (thread séparé)
# ══════════════════════════════════════════════════════════════════════════════
def boucle_scan():
    while not stop_event.is_set():
        if config["actif"]:
            check_vinted()
        # Attente cooldown, interruptible par stop_event
        cooldown_sec = config["cooldown"] * 60
        stop_event.wait(timeout=cooldown_sec)

def check_vinted():
    print(f"\n{'═'*55}")
    print(f"🔍 Scan — {time.strftime('%H:%M:%S')} | cooldown {config['cooldown']}min | budget {config['prix_min']}–{config['prix_max']}€")
    print(f"{'═'*55}")

    stats = {"total": 0, "nouveaux": 0, "filtres": 0, "alertes": 0}

    for query in SEARCH_QUERIES:
        if stop_event.is_set():
            break
        items = fetch_vinted(query)
        stats["total"] += len(items)

        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            stats["nouveaux"] += 1

            bonne, details = est_bonne_affaire(item)
            if not bonne:
                stats["filtres"] += 1
                continue

            stats["alertes"] += 1
            message = (
                f"{details['score']}\n\n"
                f"👕 <b>{details['titre']}</b>\n"
                f"🏷️ Marque : {details['marque']}\n"
                f"📐 Taille : {details['taille']}\n"
                f"💶 Prix achat : {details['prix']}€\n"
                f"📈 Revente estimée : ~{details['prix_revente']}€\n"
                f"💰 Marge nette : ~{details['marge']}€\n\n"
                f"🔗 <a href='{details['url']}'>Voir l'annonce</a>"
            )
            print(f"  🚨 {details['titre'][:45]} | {details['marge']}€ de marge")
            send_alert(message)
            time.sleep(0.5)

        time.sleep(2)

    print(f"📊 {stats['total']} récupérés | {stats['nouveaux']} nouveaux | {stats['filtres']} filtrés | {stats['alertes']} alertes\n")

def demarrer_scan():
    global scan_thread
    stop_event.clear()
    if scan_thread is None or not scan_thread.is_alive():
        scan_thread = threading.Thread(target=boucle_scan, daemon=True)
        scan_thread.start()

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("🤖 Bot Vinted démarré !")

    # Lancer le scan en arrière-plan
    demarrer_scan()

    # Message de bienvenue
    send_alert(
        "🤖 <b>Bot Vinted démarré !</b>\n"
        f"🏷️ {len(config['marques'])} marques surveillées\n"
        f"⏱️ Cooldown : {config['cooldown']} min\n"
        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n\n"
        "📋 <b>Commandes disponibles :</b>\n"
        "/start — démarrer\n"
        "/stop — arrêter\n"
        "/cooldown 10 — changer l'intervalle (minutes)\n"
        "/budget 5 150 — changer le budget\n"
        "/marque add nike — ajouter une marque\n"
        "/marque remove zara — retirer une marque\n"
        "/marque list — voir les marques actives\n"
        "/marque reset — remettre toutes les marques\n"
        "/status — voir la config actuelle"
    )

    # Lancer le bot Telegram (commandes)
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(CommandHandler("cooldown", cmd_cooldown))
    app.add_handler(CommandHandler("budget",   cmd_budget))
    app.add_handler(CommandHandler("marque",   cmd_marque))
    app.add_handler(CommandHandler("status",   cmd_status))

    print("📡 En écoute des commandes Telegram…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
