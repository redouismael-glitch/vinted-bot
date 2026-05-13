import requests
import schedule
import time
import os
from telegram import Bot
import asyncio

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — variables d'environnement Railway
# ══════════════════════════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise EnvironmentError("❌ TELEGRAM_TOKEN manquant dans les variables d'environnement.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquant dans les variables d'environnement.")

# ══════════════════════════════════════════════════════════════════════════════
#  MARQUES TENDANCE (streetwear / hype / revendables 2024-2025)
#  Ajoute ou retire des marques librement ici
# ══════════════════════════════════════════════════════════════════════════════
MARQUES_TENDANCE = {
    # Sportswear
    "nike", "jordan", "air jordan", "adidas", "new balance", "puma",
    "reebok", "asics", "converse", "vans", "saucony", "salomon", "on running",
    # Logo / preppy
    "stone island", "cp company", "ralph lauren", "polo ralph lauren",
    "lacoste", "tommy hilfiger", "fred perry", "hugo boss",
    # Streetwear hype
    "supreme", "palace", "corteiz", "off-white", "stussy", "stüssy",
    "bape", "a bathing ape", "kith", "aime leon dore", "ald",
    "carhartt", "dickies",
    # Luxe
    "balenciaga", "gucci", "louis vuitton", "dior", "prada", "burberry",
    "moncler", "canada goose",
    # Outdoor
    "arc'teryx", "arcteryx", "north face", "the north face", "patagonia",
    "napapijri", "columbia",
    # Denim / basics premium
    "levi's", "levis", "acne studios", "a.p.c", "apc", "ami paris",
    # Collabs / modèles iconiques
    "yeezy", "sacai", "fragment", "travis scott",
}

# Mots-clés dans le titre = article hype même sans marque reconnue
KEYWORDS_HYPE = {
    "vintage", "deadstock", "ds", "vnds", "rare", "limited", "collab",
    "og", "retro", "dunk", "air max", "air force", "jordan 1", "jordan 4",
    "jordan 11", "350", "990", "2002r", "550", "travis", "sacai", "fragment",
}

# Mots-clés qui excluent l'article directement
KEYWORDS_EXCLUS = {
    "lot de", "pack", "déguisement", "costume", "bébé", "enfant",
    "fille", "garçon", "chaussettes", "sous-vêtement",
}

# ══════════════════════════════════════════════════════════════════════════════
#  RÈGLES DE MARGE PAR MARQUE
#  (coefficient_revente, marge_minimum_acceptable_en_euros)
# ══════════════════════════════════════════════════════════════════════════════
REGLES_MARGE = {
    "supreme":        (2.5, 20),
    "palace":         (2.2, 20),
    "corteiz":        (2.2, 20),
    "off-white":      (2.0, 25),
    "yeezy":          (2.0, 25),
    "bape":           (2.0, 20),
    "a bathing ape":  (2.0, 20),
    "jordan":         (1.8, 15),
    "air jordan":     (1.8, 15),
    "stone island":   (1.7, 15),
    "cp company":     (1.7, 15),
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
    "lacoste":        (1.4,  8),
    "tommy hilfiger": (1.4,  8),
    "carhartt":       (1.4,  8),
    "levi's":         (1.3,  8),
    "levis":          (1.3,  8),
    # Défaut pour toute autre marque tendance
    "_defaut":        (1.4,  8),
}

PRIX_MIN = 3.0
PRIX_MAX = 200.0

# ══════════════════════════════════════════════════════════════════════════════
#  REQUÊTES VINTED
# ══════════════════════════════════════════════════════════════════════════════
SEARCH_QUERIES = [
    "nike", "adidas", "jordan", "new balance", "stone island",
    "lacoste", "ralph lauren", "tommy hilfiger", "supreme", "palace",
    "corteiz", "north face", "carhartt", "stussy", "yeezy",
    "arc'teryx", "moncler", "cp company", "napapijri", "vintage sneakers",
]

# ══════════════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
seen_ids: set = set()

# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM
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
        print("  ✅ Telegram envoyé")
    except Exception as e:
        print(f"  ❌ Erreur Telegram : {e}")

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
            print("  🔄 Session expirée, renouvellement…")
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"  ⚠️ Vinted {resp.status_code} pour '{query}'")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"  ❌ Erreur fetch '{query}' : {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  FILTRAGE ET CALCUL DE MARGE (100% Python, sans IA)
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
    for m in MARQUES_TENDANCE:
        if m in marque_low or m in titre_low:
            return m
    return None

def calculer_marge(prix_achat: float, marque: str) -> tuple[float, float]:
    coef, _ = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
    prix_revente = round(prix_achat * coef, 2)
    frais        = round(prix_revente * 0.10, 2)   # ~10% frais plateforme
    marge        = round(prix_revente - frais - prix_achat, 2)
    return prix_revente, marge

def est_bonne_affaire(item: dict) -> tuple[bool, dict]:
    titre      = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    taille     = item.get("size_title", "?")
    prix       = extraire_prix(item)
    item_id    = item.get("id")
    titre_low  = titre.lower()

    # 1. Prix dans la plage
    if prix is None or prix < PRIX_MIN or prix > PRIX_MAX:
        return False, {}

    # 2. Pas de mot-clé exclu
    for mot in KEYWORDS_EXCLUS:
        if mot in titre_low:
            return False, {}

    # 3. Marque tendance ou mot-clé hype
    marque = detecter_marque(titre, marque_raw)
    if marque is None:
        if not any(k in titre_low for k in KEYWORDS_HYPE):
            return False, {}
        marque = "_defaut"

    # 4. Marge suffisante
    _, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
    prix_revente, marge = calculer_marge(prix, marque)
    if marge < marge_min:
        return False, {}

    # 5. Niveau de score visuel
    ratio = marge / prix if prix > 0 else 0
    if ratio >= 0.5:
        score_label = "🔥🔥🔥 Excellente affaire"
    elif ratio >= 0.3:
        score_label = "🔥🔥 Très bonne affaire"
    elif ratio >= 0.15:
        score_label = "🔥 Bonne affaire"
    else:
        score_label = "👍 Affaire correcte"

    return True, {
        "titre":        titre,
        "marque":       marque_raw or marque,
        "taille":       taille,
        "prix":         prix,
        "prix_revente": prix_revente,
        "marge":        marge,
        "score":        score_label,
        "url":          f"https://www.vinted.fr/items/{item_id}",
    }

# ══════════════════════════════════════════════════════════════════════════════
#  SCAN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def check_vinted():
    print(f"\n{'═'*55}")
    print(f"🔍 Scan — {time.strftime('%H:%M:%S')}")
    print(f"{'═'*55}")

    stats = {"total": 0, "nouveaux": 0, "filtres": 0, "alertes": 0}

    for query in SEARCH_QUERIES:
        print(f"\n  📦 '{query}'")
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
            print(f"  🚨 ALERTE : {details['titre'][:45]} | marge ~{details['marge']}€")
            send_alert(message)
            time.sleep(0.5)  # anti-flood Telegram

        time.sleep(2)  # délai poli entre requêtes Vinted

    print(f"\n{'─'*55}")
    print(
        f"📊 {stats['total']} récupérés | "
        f"{stats['nouveaux']} nouveaux | "
        f"{stats['filtres']} filtrés | "
        f"{stats['alertes']} alertes"
    )
    print(f"{'─'*55}")

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🤖 Bot Vinted (sans IA) démarré !")
    send_alert(
        "🤖 <b>Bot Vinted démarré !</b>\n"
        f"🏷️ {len(MARQUES_TENDANCE)} marques surveillées\n"
        f"🔍 {len(SEARCH_QUERIES)} requêtes actives\n"
        "⏱️ Scan toutes les 15 minutes"
    )

    check_vinted()
    schedule.every(15).minutes.do(check_vinted)

    while True:
        schedule.run_pending()
        time.sleep(1)
