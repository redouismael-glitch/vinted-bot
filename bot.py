import requests
import schedule
import time
import google.generativeai as genai
from telegram import Bot
from bs4 import BeautifulSoup
import os
import json

# ── CONFIG ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "AIzaSyC10rgFkAYgO6rMSRjoopEnu69L5vm1lDc")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "8523213672:AAEdHGkYqy0J3FRzpTueRhDVBiUTPsfJ0m4")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # à remplir après
BUDGET_MAX      = 8  # euros

# Mots-clés à surveiller sur Vinted
SEARCH_QUERIES = [
    "sneakers tendance",
    "vêtements été",
    "vêtements hiver",
    "ralph lauren",
    "nike",
    "adidas",
    "jordan",
    "stone island",
    "lacoste",
    "tommy hilfiger",
]

# IDs déjà vus pour éviter les doublons
seen_ids = set()

# ── GEMINI SETUP ─────────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── TELEGRAM ─────────────────────────────────────────────────────────────────
bot = Bot(token=TELEGRAM_TOKEN)

def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
        print(f"✅ Alerte envoyée : {message[:60]}...")
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

# ── VINTED SCRAPER ────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.vinted.fr/",
}

def fetch_vinted(query):
    try:
        url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={requests.utils.quote(query)}&price_to={BUDGET_MAX}&per_page=20&order=newest_first"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Vinted a répondu {resp.status_code} pour '{query}'")
            return []
        data = resp.json()
        return data.get("items", [])
    except Exception as e:
        print(f"❌ Erreur scraping Vinted : {e}")
        return []

# ── ANALYSE GEMINI ────────────────────────────────────────────────────────────
def analyse_article(item):
    titre = item.get("title", "")
    prix  = item.get("price", {}).get("amount", "?")
    marque = item.get("brand_title", "Inconnue")
    taille = item.get("size_title", "?")
    etat  = item.get("status", "?")

    prompt = f"""
Tu es un expert en revente de vêtements et chaussures en France (Vinted, Leboncoin, Depop).
Analyse cette annonce et dis-moi si c'est une bonne affaire à acheter pour revendre avec profit.

Annonce :
- Titre : {titre}
- Marque : {marque}
- Prix : {prix}€
- Taille : {taille}
- État : {etat}

Réponds en JSON uniquement, sans markdown, avec ce format exact :
{{"bonne_affaire": true/false, "score": 1-10, "prix_revente_estime": X, "raison": "explication courte"}}

Critères :
- Budget max achat : {BUDGET_MAX}€
- Une bonne affaire = marge de revente probable > 5€
- Privilégie les marques tendance (Nike, Adidas, Jordan, Stone Island, Ralph Lauren, Lacoste, Corteiz, etc.)
- Tiens compte de l'état et de la taille
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Nettoyer le JSON si besoin
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"❌ Erreur Gemini : {e}")
        return None

# ── BOUCLE PRINCIPALE ─────────────────────────────────────────────────────────
def check_vinted():
    print(f"\n🔍 Scan Vinted en cours... ({time.strftime('%H:%M:%S')})")
    new_items = 0

    for query in SEARCH_QUERIES:
        items = fetch_vinted(query)
        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            new_items += 1

            titre = item.get("title", "Sans titre")
            prix  = item.get("price", {}).get("amount", "?")
            marque = item.get("brand_title", "?")
            url   = f"https://www.vinted.fr/items/{item_id}"

            print(f"  → Analyse : {titre} ({prix}€)")
            analyse = analyse_article(item)

            if analyse and analyse.get("bonne_affaire") and analyse.get("score", 0) >= 7:
                score         = analyse.get("score", "?")
                prix_revente  = analyse.get("prix_revente_estime", "?")
                raison        = analyse.get("raison", "")

                message = (
                    f"🔥 <b>BONNE AFFAIRE DÉTECTÉE !</b>\n\n"
                    f"👕 <b>{titre}</b>\n"
                    f"🏷️ Marque : {marque}\n"
                    f"💶 Prix : {prix}€\n"
                    f"📈 Revente estimée : ~{prix_revente}€\n"
                    f"⭐ Score : {score}/10\n"
                    f"💡 {raison}\n\n"
                    f"🔗 <a href='{url}'>Voir l'annonce</a>"
                )
                send_alert(message)
                time.sleep(1)  # anti-spam Telegram

        time.sleep(2)  # anti-spam Vinted entre les requêtes

    print(f"✅ Scan terminé — {new_items} nouvelles annonces analysées")

# ── DÉMARRAGE ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Bot Vinted démarré !")

    if not TELEGRAM_CHAT_ID:
        print("⚠️  TELEGRAM_CHAT_ID manquant — envoie /start à ton bot Telegram puis récupère ton chat_id")

    # Premier scan immédiat
    check_vinted()

    # Scan toutes les 15 minutes
    schedule.every(15).minutes.do(check_vinted)

    while True:
        schedule.run_pending()
        time.sleep(1)
