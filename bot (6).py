import requests
import schedule
import time
import json
import os
import asyncio
import re
from datetime import datetime, timezone
from google import genai
from telegram import Bot

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not GEMINI_API_KEY:
    raise EnvironmentError("❌ GEMINI_API_KEY manquante dans les variables d'environnement.")
if not TELEGRAM_TOKEN:
    raise EnvironmentError("❌ TELEGRAM_TOKEN manquante dans les variables d'environnement.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquante dans les variables d'environnement.")

# Requêtes Vinted à lancer à chaque cycle
SEARCH_QUERIES = [
    "sneakers",
    "nike",
    "adidas",
    "jordan",
    "stone island",
    "lacoste",
    "ralph lauren",
    "tommy hilfiger",
    "veste",
    "hoodie",
]

# ── FILTRES PRÉ-GEMINI ────────────────────────────────────────────────────────
# Marques considérées comme revendables
MARQUES_CIBLES = {
    "nike", "adidas", "jordan", "stone island", "lacoste",
    "ralph lauren", "tommy hilfiger", "new balance", "corteiz",
    "palace", "supreme", "off-white", "stüssy", "stussy",
    "carhartt", "levi's", "levis", "converse", "vans", "puma",
    "reebok", "asics", "salomon", "arc'teryx", "arcteryx",
    "north face", "the north face",
}

# Mots-clés dans le titre qui indiquent un potentiel de revente
KEYWORDS_POSITIFS = {
    "vintage", "deadstock", "ds", "vnds", "rare", "limited",
    "collab", "collaboration", "og", "retro", "travis scott",
    "off white", "yeezy", "dunk", "air max", "air force",
    "acronym", "sacai", "fragment",
}

# Mots-clés à exclure (articles peu revendables)
KEYWORDS_NEGATIFS = {
    "lot", "pack", "déguisement", "costume", "bébé", "enfant",
    "fille", "garçon", "accessoire", "ceinture", "chaussette",
    "chaussettes", "bonnet", "casquette générique",
}

# Prix min/max (€) pour qu'un article soit analysé par Gemini
PRIX_MIN = 5.0
PRIX_MAX = 150.0

# Score Gemini minimum pour déclencher une alerte Telegram
SCORE_MIN_ALERTE = 7

# Limite stricte : nombre max d'appels Gemini par minute (API free = 15/min)
GEMINI_MAX_PAR_MINUTE = 10

# ── ÉTAT GLOBAL ───────────────────────────────────────────────────────────────
seen_ids: set = set()

class GeminiRateLimiter:
    """Compteur glissant : garantit ≤ GEMINI_MAX_PAR_MINUTE appels / 60 s."""
    def __init__(self, max_per_minute: int):
        self.max = max_per_minute
        self.calls: list[float] = []   # timestamps des appels

    def wait_if_needed(self):
        now = time.time()
        # Purge les appels vieux de plus d'une minute
        self.calls = [t for t in self.calls if now - t < 60]
        if len(self.calls) >= self.max:
            oldest = self.calls[0]
            wait = 60 - (now - oldest) + 0.5   # +0.5 s de marge
            if wait > 0:
                print(f"⏳ Rate-limit Gemini : pause {int(wait)+1}s…")
                time.sleep(wait)
            self.calls = [t for t in self.calls if time.time() - t < 60]

    def record_call(self):
        self.calls.append(time.time())

rate_limiter = GeminiRateLimiter(GEMINI_MAX_PAR_MINUTE)

# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════════════════════════════════════
async def _send_telegram(message: str):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="HTML",
        disable_web_page_preview=False,
    )

def send_alert(message: str):
    """Envoie un message Telegram de manière synchrone (compatible Railway)."""
    try:
        asyncio.run(_send_telegram(message))
        print("✅ Telegram envoyé")
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

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
        print(f"⚠️ Impossible d'initialiser la session Vinted : {e}")
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
        f"&per_page=20"
        f"&order=newest_first"
    )
    try:
        resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code == 401:
            print("🔄 Session expirée, renouvellement…")
            _session = _make_session()
            resp = _session.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"⚠️ Vinted {resp.status_code} pour '{query}'")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ Erreur scraping '{query}' : {e}")
        return []

# ══════════════════════════════════════════════════════════════════════════════
#  FILTRAGE PRÉ-GEMINI
# ══════════════════════════════════════════════════════════════════════════════
def _extraire_prix(item: dict) -> float | None:
    """Retourne le prix en float ou None si non disponible."""
    try:
        raw = item.get("price", {})
        # L'API Vinted peut renvoyer {"amount": "12.00"} ou {"amount": 12.0}
        if isinstance(raw, dict):
            return float(raw.get("amount", 0))
        return float(raw)
    except (TypeError, ValueError):
        return None

def pre_filtrer(item: dict) -> tuple[bool, str]:
    """
    Applique les filtres locaux AVANT tout appel Gemini.
    Retourne (True, "") si l'article passe, ou (False, raison) sinon.
    """
    titre  = (item.get("title") or "").lower()
    marque = (item.get("brand_title") or "").lower().strip()
    prix   = _extraire_prix(item)

    # 1. Prix hors plage
    if prix is None:
        return False, "prix introuvable"
    if prix < PRIX_MIN:
        return False, f"prix trop bas ({prix}€)"
    if prix > PRIX_MAX:
        return False, f"prix trop élevé ({prix}€)"

    # 2. Mot-clé négatif dans le titre
    for mot in KEYWORDS_NEGATIFS:
        if mot in titre:
            return False, f"mot-clé exclu '{mot}'"

    # 3. Marque cible OU mot-clé positif dans le titre
    marque_ok = any(m in marque for m in MARQUES_CIBLES) or any(m in titre for m in MARQUES_CIBLES)
    keyword_ok = any(k in titre for k in KEYWORDS_POSITIFS)

    if not marque_ok and not keyword_ok:
        return False, "ni marque cible ni mot-clé positif"

    return True, ""

# ══════════════════════════════════════════════════════════════════════════════
#  ANALYSE GEMINI
# ══════════════════════════════════════════════════════════════════════════════
client = genai.Client(api_key=GEMINI_API_KEY)

def analyser_avec_gemini(item: dict) -> dict | None:
    """
    Envoie l'article à Gemini après avoir respecté le rate-limit.
    Retourne le JSON parsé ou None en cas d'erreur.
    """
    titre  = item.get("title", "")
    prix   = _extraire_prix(item) or "?"
    marque = item.get("brand_title", "Inconnue")
    taille = item.get("size_title", "?")
    etat   = item.get("status", "?")

    prompt = f"""Tu es un expert en revente de vêtements et chaussures en France (Vinted, Leboncoin, Depop, Vestiaire Collective).
Analyse si c'est une bonne affaire à acheter pour revendre avec profit.

- Titre  : {titre}
- Marque : {marque}
- Prix   : {prix}€
- Taille : {taille}
- État   : {etat}

Réponds en JSON uniquement, sans markdown, sans texte autour :
{{"bonne_affaire": true/false, "score": 1-10, "prix_revente_estime": X, "raison": "explication courte en français"}}

Critères :
- Bonne affaire = marge probable ≥ 10€ après achat.
- Privilégie : Nike, Adidas, Jordan, Stone Island, Ralph Lauren, Lacoste, Corteiz, New Balance, Palace, Supreme.
- Pénalise les articles en mauvais état ou sans marque reconnue."""

    rate_limiter.wait_if_needed()
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        rate_limiter.record_call()
        text = response.text.strip()
        # Nettoyage robuste des balises markdown résiduelles
        text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON Gemini invalide : {e} — réponse brute : {response.text[:200]}")
        return None
    except Exception as e:
        print(f"❌ Erreur Gemini : {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  SCAN PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def check_vinted():
    print(f"\n{'═'*60}")
    print(f"🔍 Scan Vinted — {time.strftime('%H:%M:%S')}")
    print(f"{'═'*60}")

    stats = {"total": 0, "nouveaux": 0, "filtres": 0, "analyses": 0, "alertes": 0}

    for query in SEARCH_QUERIES:
        print(f"\n  📦 Requête : '{query}'")
        items = fetch_vinted(query)
        stats["total"] += len(items)

        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue

            seen_ids.add(item_id)
            stats["nouveaux"] += 1

            titre = item.get("title", "Sans titre")
            prix  = _extraire_prix(item)

            # ── ÉTAPE 1 : filtrage local ─────────────────────────────────
            passe, raison_rejet = pre_filtrer(item)
            if not passe:
                print(f"    ✗ [{prix}€] {titre[:50]} → filtré ({raison_rejet})")
                stats["filtres"] += 1
                continue

            print(f"    ✓ [{prix}€] {titre[:50]} → envoi à Gemini…")
            stats["analyses"] += 1

            # ── ÉTAPE 2 : analyse Gemini ─────────────────────────────────
            analyse = analyser_avec_gemini(item)
            if not analyse:
                continue

            bonne_affaire = analyse.get("bonne_affaire", False)
            score         = analyse.get("score", 0)

            if bonne_affaire and score >= SCORE_MIN_ALERTE:
                stats["alertes"] += 1
                marque       = item.get("brand_title", "?")
                taille       = item.get("size_title", "?")
                prix_revente = analyse.get("prix_revente_estime", "?")
                raison       = analyse.get("raison", "")
                url          = f"https://www.vinted.fr/items/{item_id}"

                marge_estimee = ""
                if isinstance(prix_revente, (int, float)) and prix is not None:
                    marge = round(float(prix_revente) - float(prix), 2)
                    marge_estimee = f"\n💰 Marge estimée : ~{marge}€"

                message = (
                    f"🔥 <b>BONNE AFFAIRE !</b>\n\n"
                    f"👕 <b>{titre}</b>\n"
                    f"🏷️ Marque : {marque}\n"
                    f"📐 Taille : {taille}\n"
                    f"💶 Prix achat : {prix}€\n"
                    f"📈 Revente estimée : ~{prix_revente}€"
                    f"{marge_estimee}\n"
                    f"⭐ Score : {score}/10\n"
                    f"💡 {raison}\n\n"
                    f"🔗 <a href='{url}'>Voir l'annonce</a>"
                )
                send_alert(message)
                time.sleep(1)  # anti-flood Telegram
            else:
                raison_refus = analyse.get("raison", "score insuffisant")
                print(f"       → Refusé par Gemini (score {score}/10 : {raison_refus})")

        time.sleep(2)  # délai poli entre requêtes Vinted

    print(f"\n{'─'*60}")
    print(f"📊 Stats : {stats['total']} récupérés | {stats['nouveaux']} nouveaux | "
          f"{stats['filtres']} filtrés | {stats['analyses']} analysés par Gemini | "
          f"{stats['alertes']} alertes envoyées")
    print(f"{'─'*60}")

# ══════════════════════════════════════════════════════════════════════════════
#  DÉMARRAGE
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🤖 Bot Vinted démarré !")
    send_alert(
        "🤖 <b>Bot Vinted démarré !</b>\n"
        "Je scanne toutes les 15 minutes.\n"
        f"Filtres actifs : prix {PRIX_MIN}€–{PRIX_MAX}€, marques cibles, score ≥ {SCORE_MIN_ALERTE}/10."
    )

    check_vinted()
    schedule.every(15).minutes.do(check_vinted)

    while True:
        schedule.run_pending()
        time.sleep(1)
