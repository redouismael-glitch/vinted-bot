import requests
import time
import os
import asyncio
import sys
from collections import deque
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

MARQUES_HYPE_BONUS = {
    "chrome hearts", "hellstar", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "corteiz", "crtz", "supreme", "palace",
    "off-white", "fear of god", "trapstar", "broken planet", "syna world",
    "yeezy", "bape", "jordan", "air jordan", "represent", "minus two",
}

# Tailles rares qui méritent un bonus de score
TAILLES_RARES = {"xxs", "xs", "3xl", "4xl", "5xl", "xxl", "xxxl", "6", "6.5", "13", "14", "15"}

# États qui méritent un bonus de score
ETATS_PREMIUM = {"neuf avec étiquette", "neuf sans étiquette", "très bon état"}

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

# Base de prix moyens de revente par marque (prix marché indicatif)
PRIX_MARCHE = {
    "chrome hearts": 400, "hellstar": 120, "gallery dept": 250,
    "rick owens": 350, "drkshdw": 200, "supreme": 150, "palace": 100,
    "off-white": 200, "yeezy": 180, "jordan": 120, "air jordan": 120,
    "balenciaga": 400, "moncler": 600, "canada goose": 400,
    "stone island": 200, "cp company": 150, "arc'teryx": 250,
    "north face": 80, "nike": 80, "adidas": 70, "new balance": 90,
    "ralph lauren": 60, "lacoste": 50, "carhartt": 60,
    "ami paris": 130, "jacquemus": 150, "sandro": 100,
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
    "actif":            False,
    "msg_cooldown":     1,       # secondes entre chaque message Telegram
    "prix_min":         3.0,
    "prix_max":         200.0,
    "score_min":        60,      # score /100 minimum pour alerter
    "marques":          set(TOUTES_LES_MARQUES),
    # sous-menus panel
    "menu_actif":       "main",  # main | scan | budget | score | marques | historique | favoris
}

seen_ids: set = set()
historique_alertes: deque = deque(maxlen=50)  # 50 dernières alertes
favoris: list = []  # annonces mises en favoris

# ══════════════════════════════════════════════════════════════════════════════
#  SCRAPER
# ══════════════════════════════════════════════════════════════════════════════
def _make_session() -> requests.Session:
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
def calculer_score(prix: float, revente: float, marge: float,
                   marque: str, titre: str, taille: str, etat: str) -> int:
    """
    Score /100 basé sur :
    - ratio marge/prix          → 0-35 pts
    - marge absolue             → 0-20 pts
    - comparaison prix marché   → 0-10 pts
    - bonus marque hype         → 0-15 pts
    - bonus keywords hype       → 0-8  pts
    - bonus sous-côte extrême   → 0-6  pts
    - bonus état (neuf/TBE)     → 0-4  pts
    - bonus taille rare         → 0-2  pts
    """
    t = titre.lower()
    score = 0

    # 1. Ratio marge/prix
    ratio = marge / prix if prix > 0 else 0
    score += min(35, int(ratio * 55))

    # 2. Marge absolue
    if   marge >= 100: score += 20
    elif marge >= 50:  score += 15
    elif marge >= 30:  score += 10
    elif marge >= 20:  score += 7
    elif marge >= 10:  score += 4

    # 3. Comparaison au prix de marché (confiance)
    prix_marche = PRIX_MARCHE.get(marque)
    if prix_marche and prix_marche > 0:
        ratio_marche = prix / prix_marche
        if   ratio_marche <= 0.20: score += 10
        elif ratio_marche <= 0.35: score += 7
        elif ratio_marche <= 0.50: score += 4

    # 4. Bonus marque hype
    if marque in MARQUES_HYPE_BONUS:
        score += 15
    elif marque in REGLES_MARGE and REGLES_MARGE[marque][0] >= 1.8:
        score += 8

    # 5. Bonus keywords hype dans le titre
    hype_count = sum(1 for k in KEYWORDS_HYPE if k in t)
    score += min(8, hype_count * 3)

    # 6. Bonus sous-côte extrême
    if   revente > prix * 3.0: score += 6
    elif revente > prix * 2.5: score += 4

    # 7. Bonus état
    if etat.lower() in ETATS_PREMIUM:
        score += 4

    # 8. Bonus taille rare
    if taille.lower().strip() in TAILLES_RARES:
        score += 2

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
def extraire_prix(item: dict) -> float | None:
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None

def detecter_marque(titre: str, marque_vinted: str) -> str | None:
    t = titre.lower()
    m = marque_vinted.lower().strip()
    for marque in config["marques"]:
        if marque in m or marque in t:
            return marque
    return None

def analyser(item: dict) -> tuple[bool, dict]:
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?") or "?"
    etat       = item.get("status", "") or ""
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

    score = calculer_score(prix, revente, marge, marque, titre, taille, etat)
    if score < config["score_min"]:
        return False, {}

    data = {
        "id":      item_id,
        "titre":   titre,
        "marque":  marque_raw or marque,
        "taille":  taille,
        "etat":    etat,
        "prix":    prix,
        "revente": revente,
        "marge":   marge,
        "score":   score,
        "niveau":  niveau_affaire(score),
        "url":     f"https://www.vinted.fr/items/{item_id}",
        "heure":   time.strftime("%H:%M:%S"),
    }
    return True, data

# ══════════════════════════════════════════════════════════════════════════════
#  MESSAGE TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
def formater_alerte(d: dict, idx: int | None = None) -> str:
    fav_btn_hint = f"\n<i>💾 Utilise /bot → Favoris pour sauvegarder</i>" if idx is None else ""
    return (
        f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
        f"👕 <b>{d['titre']}</b>\n"
        f"🏷️ Marque : {d['marque']}\n"
        f"📐 Taille : {d['taille']}\n"
        f"✨ État : {d['etat'] or 'Non précisé'}\n"
        f"💶 Prix achat : <b>{d['prix']}€</b>\n"
        f"📈 Revente estimée : ~{d['revente']}€\n"
        f"💰 Marge nette : ~<b>{d['marge']}€</b>\n"
        f"🕐 {d['heure']}\n\n"
        f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
        f"{fav_btn_hint}"
    )

def build_alerte_keyboard(item_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"fav_add_{item_id}"),
    ]])

# ══════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE SCAN (scan continu, cooldown uniquement entre messages)
# ══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    loop = asyncio.get_event_loop()
    # File d'attente pour les alertes à envoyer
    alert_queue: asyncio.Queue = asyncio.Queue()

    # Tâche expéditrice : envoie les messages avec cooldown
    async def expediteur():
        while True:
            d = await alert_queue.get()
            msg    = formater_alerte(d)
            markup = build_alerte_keyboard(d["id"])
            try:
                await app.bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=msg,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                    reply_markup=markup,
                )
            except Exception as e:
                print(f"❌ Telegram: {e}")
            # Cooldown adaptatif : augmente si la file est longue
            qs = alert_queue.qsize()
            delay = config["msg_cooldown"] * (1 + qs // 5)
            await asyncio.sleep(min(delay, 5))

    asyncio.create_task(expediteur())

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

                if len(seen_ids) > 50_000:
                    # Garde les 25 000 plus récents
                    seen_ids.difference_update(list(seen_ids)[:25_000])

                ok, d = analyser(item)
                if not ok:
                    continue

                alertes += 1
                historique_alertes.appendleft(d)
                await alert_queue.put(d)
                print(f"  🚨 {d['titre'][:45]} | score {d['score']}/100 | ~{d['marge']}€")

            # Petit délai entre requêtes pour ne pas spammer l'API
            await asyncio.sleep(1)

        print(f"✅ Cycle terminé — {alertes} nouvelles alertes")
        # Scan continu : pas de cooldown entre cycles, seulement 1s de respiration
        await asyncio.sleep(1)

# ══════════════════════════════════════════════════════════════════════════════
#  PANEL /bot — MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def build_main_text() -> str:
    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
    nb_fav = len(favoris)
    nb_hist = len(historique_alertes)
    return (
        f"🤖 <b>Vinted Bot — Panel de contrôle</b>\n"
        f"{'─' * 32}\n"
        f"{'🟢' if config['actif'] else '🔴'} État          : <b>{etat}</b>\n"
        f"📨 Cooldown msg : <b>{config['msg_cooldown']}s</b>\n"
        f"💶 Budget        : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"🎯 Score min     : <b>{config['score_min']}/100</b>\n"
        f"🏷️ Marques        : <b>{len(config['marques'])}</b>\n"
        f"📋 Historique    : <b>{nb_hist}</b> alertes\n"
        f"⭐ Favoris       : <b>{nb_fav}</b> annonces\n"
        f"{'─' * 32}\n"
        f"<i>Choisis une catégorie ci-dessous :</i>"
    )

def build_main_keyboard() -> InlineKeyboardMarkup:
    etat_btn = "⏸ Pause" if config["actif"] else "▶️ Démarrer"
    etat_cb  = "panel_pause" if config["actif"] else "panel_start"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(etat_btn, callback_data=etat_cb),
            InlineKeyboardButton("⏹ Arrêter", callback_data="panel_stop"),
        ],
        [
            InlineKeyboardButton("📡 Scan",         callback_data="menu_scan"),
            InlineKeyboardButton("💶 Budget",        callback_data="menu_budget"),
            InlineKeyboardButton("🎯 Score",         callback_data="menu_score"),
        ],
        [
            InlineKeyboardButton("🏷️ Marques",        callback_data="menu_marques"),
            InlineKeyboardButton("📋 Historique",    callback_data="menu_historique"),
            InlineKeyboardButton("⭐ Favoris",       callback_data="menu_favoris"),
        ],
        [
            InlineKeyboardButton("🔁 Reset config",  callback_data="panel_reset"),
            InlineKeyboardButton("🔄 Actualiser",    callback_data="menu_main"),
        ],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : SCAN (cooldown messages)
# ══════════════════════════════════════════════════════════════════════════════
def build_scan_text() -> str:
    return (
        f"📡 <b>Paramètres de scan</b>\n"
        f"{'─' * 30}\n"
        f"⚡ Le scan tourne en <b>continu</b> (pas de cooldown entre cycles)\n\n"
        f"📨 Cooldown entre messages : <b>{config['msg_cooldown']}s</b>\n"
        f"   <i>(augmente automatiquement si trop d'alertes)</i>\n"
        f"{'─' * 30}\n"
        f"<i>Choisis le délai entre messages :</i>"
    )

def build_scan_keyboard() -> InlineKeyboardMarkup:
    cd = config["msg_cooldown"]
    def mark(v): return f"✅ {v}s" if cd == v else f"{v}s"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(mark(1),  callback_data="msgcd_1"),
            InlineKeyboardButton(mark(2),  callback_data="msgcd_2"),
            InlineKeyboardButton(mark(3),  callback_data="msgcd_3"),
        ],
        [
            InlineKeyboardButton(mark(5),  callback_data="msgcd_5"),
            InlineKeyboardButton(mark(10), callback_data="msgcd_10"),
            InlineKeyboardButton(mark(30), callback_data="msgcd_30"),
        ],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : BUDGET
# ══════════════════════════════════════════════════════════════════════════════
def build_budget_text() -> str:
    return (
        f"💶 <b>Filtre budget</b>\n"
        f"{'─' * 30}\n"
        f"Actuel : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"{'─' * 30}\n"
        f"<i>Choisis une plage de prix :</i>"
    )

def build_budget_keyboard() -> InlineKeyboardMarkup:
    cur = (config["prix_min"], config["prix_max"])
    def mark(a, b): return f"✅ {a}–{b}€" if cur == (float(a), float(b)) else f"{a}–{b}€"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(mark(3,  30),  callback_data="budget_3_30"),
            InlineKeyboardButton(mark(3,  50),  callback_data="budget_3_50"),
            InlineKeyboardButton(mark(5,  50),  callback_data="budget_5_50"),
        ],
        [
            InlineKeyboardButton(mark(5,  100), callback_data="budget_5_100"),
            InlineKeyboardButton(mark(5,  150), callback_data="budget_5_150"),
            InlineKeyboardButton(mark(5,  200), callback_data="budget_5_200"),
        ],
        [
            InlineKeyboardButton(mark(10, 300), callback_data="budget_10_300"),
            InlineKeyboardButton(mark(10, 500), callback_data="budget_10_500"),
        ],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : SCORE
# ══════════════════════════════════════════════════════════════════════════════
def build_score_text() -> str:
    s = config["score_min"]
    explication = {
        range(30, 50): "🟡 Mode large — beaucoup d'alertes",
        range(50, 65): "🟠 Mode équilibré — recommandé",
        range(65, 80): "🔴 Mode strict — bonnes affaires sûres",
        range(80, 96): "💎 Mode expert — pépites seulement",
    }
    desc = next((v for k, v in explication.items() if s in k), "")
    return (
        f"🎯 <b>Score minimum</b>\n"
        f"{'─' * 30}\n"
        f"Score actuel : <b>{s}/100</b>\n"
        f"{desc}\n"
        f"{'─' * 30}\n"
        f"<i>Ajuste le seuil :</i>"
    )

def build_score_keyboard() -> InlineKeyboardMarkup:
    s = config["score_min"]
    def mark(v): return f"✅ {v}" if s == v else str(v)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(mark(40), callback_data="score_set_40"),
            InlineKeyboardButton(mark(50), callback_data="score_set_50"),
            InlineKeyboardButton(mark(55), callback_data="score_set_55"),
            InlineKeyboardButton(mark(60), callback_data="score_set_60"),
        ],
        [
            InlineKeyboardButton(mark(65), callback_data="score_set_65"),
            InlineKeyboardButton(mark(70), callback_data="score_set_70"),
            InlineKeyboardButton(mark(75), callback_data="score_set_75"),
            InlineKeyboardButton(mark(80), callback_data="score_set_80"),
        ],
        [
            InlineKeyboardButton("▼ -5", callback_data="score_down"),
            InlineKeyboardButton(f"  {s}/100  ", callback_data="noop"),
            InlineKeyboardButton("▲ +5", callback_data="score_up"),
        ],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : MARQUES
# ══════════════════════════════════════════════════════════════════════════════
def build_marques_text() -> str:
    nb = len(config["marques"])
    total = len(TOUTES_LES_MARQUES)
    return (
        f"🏷️ <b>Gestion des marques</b>\n"
        f"{'─' * 30}\n"
        f"Actives : <b>{nb}/{total}</b> marques\n"
        f"{'─' * 30}\n"
        f"<i>Utilise /marque add &lt;nom&gt; ou /marque remove &lt;nom&gt; pour modifier.\n"
        f"/marque list pour voir la liste complète.</i>"
    )

def build_marques_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Réinitialiser toutes les marques", callback_data="marques_reset")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════
def build_historique_text() -> str:
    if not historique_alertes:
        return "📋 <b>Historique des alertes</b>\n\nAucune alerte pour le moment."
    lines = [f"📋 <b>Historique — {len(historique_alertes)} dernières alertes</b>\n{'─' * 30}"]
    for i, d in enumerate(list(historique_alertes)[:10], 1):
        lines.append(
            f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
            f"   {d['titre'][:35]} | {d['prix']}€ → ~{d['marge']}€ marge\n"
            f"   🕐 {d['heure']} — <a href='{d['url']}'>Voir</a>"
        )
    if len(historique_alertes) > 10:
        lines.append(f"\n<i>... et {len(historique_alertes) - 10} de plus</i>")
    return "\n".join(lines)

def build_historique_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Vider l'historique", callback_data="historique_clear")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  SOUS-MENU : FAVORIS
# ══════════════════════════════════════════════════════════════════════════════
def build_favoris_text() -> str:
    if not favoris:
        return "⭐ <b>Favoris</b>\n\nAucun favori enregistré.\n\n<i>Clique sur ⭐ dans une alerte pour ajouter.</i>"
    lines = [f"⭐ <b>Favoris — {len(favoris)} annonces</b>\n{'─' * 30}"]
    for i, d in enumerate(favoris, 1):
        lines.append(
            f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
            f"   {d['titre'][:35]}\n"
            f"   💶 {d['prix']}€ | 💰 ~{d['marge']}€ | 🕐 {d['heure']}\n"
            f"   <a href='{d['url']}'>Voir l'annonce</a>"
        )
    return "\n".join(lines)

def build_favoris_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, d in enumerate(favoris[:8]):
        buttons.append([InlineKeyboardButton(
            f"🗑️ Supprimer #{i+1} — {d['titre'][:25]}",
            callback_data=f"fav_del_{i}"
        )])
    buttons.append([InlineKeyboardButton("🗑️ Vider tous les favoris", callback_data="fav_clear")])
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTEUR DE MENU
# ══════════════════════════════════════════════════════════════════════════════
MENUS = {
    "main":       (build_main_text,       build_main_keyboard),
    "scan":       (build_scan_text,        build_scan_keyboard),
    "budget":     (build_budget_text,      build_budget_keyboard),
    "score":      (build_score_text,       build_score_keyboard),
    "marques":    (build_marques_text,     build_marques_keyboard),
    "historique": (build_historique_text,  build_historique_keyboard),
    "favoris":    (build_favoris_text,     build_favoris_keyboard),
}

async def afficher_menu(query, menu: str = "main"):
    text_fn, kb_fn = MENUS.get(menu, MENUS["main"])
    try:
        await query.edit_message_text(
            text_fn(),
            reply_markup=kb_fn(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDES TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text_fn, kb_fn = MENUS["main"]
    await update.message.reply_text(
        text_fn(), reply_markup=kb_fn(), parse_mode="HTML",
        disable_web_page_preview=True,
    )

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("⏸ <b>Scan mis en pause.</b>\nTape /start pour relancer.", parse_mode="HTML")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build_main_text() + "\n\n👉 Tape /bot pour le panel interactif",
        parse_mode="HTML",
    )

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
    except Exception:
        await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")

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
#  CALLBACK HANDLER
# ══════════════════════════════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Navigation menus ──────────────────────────────────────
    if data.startswith("menu_"):
        menu = data.split("_", 1)[1]
        await afficher_menu(query, menu)
        return

    # ── Contrôle scan ─────────────────────────────────────────
    if data == "panel_start":
        config["actif"] = True
    elif data == "panel_pause":
        config["actif"] = False
    elif data == "panel_stop":
        config["actif"] = False
        await query.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer automatiquement.")
        sys.exit(0)
    elif data == "panel_reset":
        config.update({
            "msg_cooldown": 1,
            "prix_min": 3.0,
            "prix_max": 200.0,
            "score_min": 60,
            "marques": set(TOUTES_LES_MARQUES),
        })

    # ── Cooldown messages ─────────────────────────────────────
    elif data.startswith("msgcd_"):
        config["msg_cooldown"] = int(data.split("_")[1])
        await afficher_menu(query, "scan")
        return

    # ── Budget ────────────────────────────────────────────────
    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"] = float(pmin)
        config["prix_max"] = float(pmax)
        await afficher_menu(query, "budget")
        return

    # ── Score ─────────────────────────────────────────────────
    elif data == "score_up":
        config["score_min"] = min(95, config["score_min"] + 5)
        await afficher_menu(query, "score")
        return
    elif data == "score_down":
        config["score_min"] = max(30, config["score_min"] - 5)
        await afficher_menu(query, "score")
        return
    elif data.startswith("score_set_"):
        config["score_min"] = int(data.split("_")[2])
        await afficher_menu(query, "score")
        return

    # ── Marques ───────────────────────────────────────────────
    elif data == "marques_reset":
        config["marques"] = set(TOUTES_LES_MARQUES)
        await afficher_menu(query, "marques")
        return

    # ── Historique ────────────────────────────────────────────
    elif data == "historique_clear":
        historique_alertes.clear()
        await afficher_menu(query, "historique")
        return

    # ── Favoris ───────────────────────────────────────────────
    elif data.startswith("fav_add_"):
        item_id_str = data.split("_", 2)[2]
        # Cherche dans l'historique
        trouve = next((d for d in historique_alertes if str(d.get("id")) == item_id_str), None)
        if trouve and trouve not in favoris:
            favoris.append(trouve)
            await query.answer("⭐ Ajouté aux favoris !", show_alert=True)
        elif trouve in favoris:
            await query.answer("Déjà dans les favoris.", show_alert=True)
        else:
            await query.answer("Introuvable dans l'historique.", show_alert=True)
        return
    elif data.startswith("fav_del_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(favoris):
            favoris.pop(idx)
        await afficher_menu(query, "favoris")
        return
    elif data == "fav_clear":
        favoris.clear()
        await afficher_menu(query, "favoris")
        return

    elif data == "noop":
        return

    # ── Rafraîchissement du panel principal ───────────────────
    await afficher_menu(query, "main")

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
            f"📨 Cooldown messages : {config['msg_cooldown']}s\n"
            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
            f"🎯 Score min : {config['score_min']}/100\n"
            f"⚡ Scan continu activé\n\n"
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
    app.add_handler(CommandHandler("bot",     cmd_bot))
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("stop",    cmd_stop))
    app.add_handler(CommandHandler("budget",  cmd_budget))
    app.add_handler(CommandHandler("marque",  cmd_marque))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("📡 Bot en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
