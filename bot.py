import requests
import schedule
import time
import json
import os
import asyncio
from google import genai
from telegram import Bot

# ── CONFIG ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "AIzaSyC10rgFkAYgO6rMSRjoopEnu69L5vm1lDc")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "8523213672:AAEdHGkYqy0J3FRzpTueRhDVBiUTPsfJ0m4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8994030031")
BUDGET_MAX       = 8

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

seen_ids = set()

# ── GEMINI ────────────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
async def send_alert(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
        print("✅ Message Telegram envoyé")
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

# ── VINTED SCRAPER (sans cookie) ──────────────────────────────────────────────
def get_session_cookie():
    """Récupère un cookie de session automatiquement"""
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9",
        })
        session.get("https://www.vinted.fr", timeout=10)
        return session
    except Exception as e:
        print(f"❌ Erreur session : {e}")
        return None

session = get_session_cookie()

def fetch_vinted(query):
    global session
    try:
        if session is None:
            session = get_session_cookie()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer": "https://www.vinted.fr/catalog",
            "X-Requested-With": "XMLHttpRequest",
        }

        url = (
            f"https://www.vinted.fr/api/v2/catalog/items"
            f"?search_text={requests.utils.quote(query)}"
            f"&price_to={BUDGET_MAX}"
            f"&per_page=20"
            f"&order=newest_first"
        )

        resp = session.get(url, headers=headers, timeout=15)
        print(f"  Status {resp.status_code} pour '{query}'")

        if resp.status_code == 401:
            # Renouvelle la session et réessaie
            session = get_session_cookie()
            resp = session.get(url, headers=headers, timeout=15)

        if resp.status_code != 200:
            return []

        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ Erreur scraping : {e}")
        return []

# ── ANALYSE GEMINI ────────────────────────────────────────────────────────────
def analyse_article(item):
    titre  = item.get("title", "")
    prix   = item.get("price", {}).get("amount", "?")
    marque = item.get("brand_title", "Inconnue")
    taille = item.get("size_title", "?")
    etat   = item.get("status", "?")

    prompt = f"""
Tu es un expert en revente de vêtements et chaussures en France.
Analyse si c'est une bonne affaire à acheter pour revendre avec profit.

- Titre : {titre}
- Marque : {marque}
- Prix : {prix}€
- Taille : {taille}
- État : {etat}
- Budget max : {BUDGET_MAX}€

Réponds en JSON uniquement sans markdown :
{{"bonne_affaire": true/false, "score": 1-10, "prix_revente_estime": X, "raison": "explication courte"}}

Une bonne affaire = marge de revente > 5€. Privilégie Nike, Adidas, Jordan, Stone Island, Ralph Lauren, Lacoste, Corteiz.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"❌ Erreur Gemini : {e}")
        return None

# ── SCAN PRINCIPAL ────────────────────────────────────────────────────────────
def check_vinted():
    print(f"\n🔍 Scan Vinted... ({time.strftime('%H:%M:%S')})")
    new_items = 0

    for query in SEARCH_QUERIES:
        items = fetch_vinted(query)
        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            new_items += 1

            titre  = item.get("title", "Sans titre")
            prix   = item.get("price", {}).get("amount", "?")
            marque = item.get("brand_title", "?")
            url    = f"https://www.vinted.fr/items/{item_id}"

            print(f"  → {titre} ({prix}€)")
            analyse = analyse_article(item)

            if analyse and analyse.get("bonne_affaire") and analyse.get("score", 0) >= 7:
                score        = analyse.get("score", "?")
                prix_revente = analyse.get("prix_revente_estime", "?")
                raison       = analyse.get("raison", "")

                message = (
                    f"🔥 <b>BONNE AFFAIRE !</b>\n\n"
                    f"👕 <b>{titre}</b>\n"
                    f"🏷️ Marque : {marque}\n"
                    f"💶 Prix : {prix}€\n"
                    f"📈 Revente estimée : ~{prix_revente}€\n"
                    f"⭐ Score : {score}/10\n"
                    f"💡 {raison}\n\n"
                    f"🔗 <a href='{url}'>Voir l'annonce</a>"
                )
                asyncio.run(send_alert(message))
                time.sleep(1)

        time.sleep(3)

    print(f"✅ Scan terminé — {new_items} nouvelles annonces analysées")

# ── DÉMARRAGE ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Bot Vinted démarré !")
    asyncio.run(send_alert("🤖 Bot Vinted démarré ! Je scan toutes les 15 minutes."))

    check_vinted()
    schedule.every(15).minutes.do(check_vinted)

    while True:
        schedule.run_pending()
        time.sleep(1)
