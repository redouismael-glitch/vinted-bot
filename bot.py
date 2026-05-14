import requests
import time
import os
import asyncio
import sys
import re
from collections import deque
from urllib.parse import urlparse, parse_qs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

CONFIG
══════════════════════════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
if not TELEGRAM_TOKEN:
    raise EnvironmentError("❌ TELEGRAM_TOKEN manquant.")
if not TELEGRAM_CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquant.")

══════════════════════════════════════════════════════════════════════════════
🔥 BASE DE DONNÉES MARQUES PRO
══════════════════════════════════════════════════════════════════════════════
marques = [
    "Corteiz","Hellstar","Broken Planet","Stussy","Supreme","Palace","Carhartt","Dickies",
    "Off-White","Essentials","Fear of God","Trapstar","Represent","Bape","Kith",
    "Chrome Hearts","Amiri","Pleasures","Daily Paper","Hoodrich","CPFM",
    "Rhude","Palm Angels","Stone Island","The North Face","Arc'teryx",
    "Aime Leon Dore","Patta","Obey","Thrasher","Anti Social Social Club",
    "Nike","Adidas","Puma","Reebok","New Balance","Asics","Under Armour",
    "Jordan","Converse","Vans","Salomon","Mizuno","Champion","Fila",
    "Hoka","On Running","Columbia","Patagonia",
    "Louis Vuitton","Gucci","Prada","Balenciaga","Dior","Chanel","Burberry",
    "Givenchy","Moncler","YSL","Versace","Kenzo","Celine","Loewe","Margiela",
    "Rick Owens","Vetements","Acne Studios","Jacquemus","Ami Paris",
    "Valentino","Bottega Veneta","Hermès","Lanvin","Moschino",
    "Acronym","Mammut","Helly Hansen","Montbell","Millet","Haglöfs","Carinthia",
    "Ralph Lauren","Tommy Hilfiger","Lacoste","Levi's","Wrangler",
    "Timberland","Nautica","Kappa","Ellesse","Fred Perry","Benetton","Napapijri",
    "Ugg","Lululemon","Gallery Dept","Sp5der"
]

variantes = {
    "crt":"Corteiz","crtz":"Corteiz","stoney":"Stone Island","bp":"Broken Planet",
    "tnf":"The North Face","fog":"Fear of God","tech fleece":"Nike Tech Fleece",
    "nb":"New Balance","rl":"Ralph Lauren"
}

categories = {
    "Corteiz":"streetwear","Hellstar":"streetwear","Broken Planet":"streetwear",
    "Nike":"sportswear","Adidas":"sportswear",
    "Louis Vuitton":"luxe","Gucci":"luxe",
    "Arc'teryx":"techwear","Ralph Lauren":"vintage",
    "Zara":"fast_fashion","H&M":"fast_fashion"
}

priorite = {
    "streetwear": 3,"luxe": 3,"techwear": 3,
    "sportswear": 2,"vintage": 2,"tendance": 2,"fast_fashion": 0
}

══════════════════════════════════════════════════════════════════════════════
ÉTAT GLOBAL
══════════════════════════════════════════════════════════════════════════════
config = {
    "actif": False,
    "msg_cooldown": 1,
    "prix_min": 3.0,
    "prix_max": 200.0,
    "score_min": 60,
    "mode_flux": True,  # True = flux continu, False = un message par article
    "menu_actif": "main",
    "marques_page": 0,
    "search_query": "",
}

# Marques sélectionnées par l'utilisateur (par défaut: toutes sauf fast-fashion)
selected_brands = set(m for m in marques if categories.get(m) != "fast_fashion")

seen_ids: set = set()
historique_alertes: deque = deque(maxlen=50)
favoris: list = []

══════════════════════════════════════════════════════════════════════════════
🔥 DÉTECTION INTELLIGENTE DE MARQUE
══════════════════════════════════════════════════════════════════════════════
def detecter_marque_pro(titre: str, marque_vinted: str = None) -> dict | None:
    """Détecte marque via base PRO: titre → variantes → marques → catégorie → priorité"""
    t = titre.lower()
    
    # 1. Vérifier variantes d'abord
    for short, full in variantes.items():
        if short in t:
            marque = full
            break
    else:
        # 2. Vérifier marques complètes
        marque = None
        for m in marques:
            if m.lower() in t:
                marque = m
                break
        if not marque and marque_vinted:
            mv = marque_vinted.lower().strip()
            for m in marques:
                if m.lower() in mv:
                    marque = m
                    break
    
    if not marque:
        return None
    
    # 3. Déterminer catégorie et priorité
    categorie = categories.get(marque, "tendance")
    prio = priorite.get(categorie, 1)
    
    # Ignorer fast-fashion
    if categorie == "fast_fashion":
        return None
    
    return {"marque": marque, "categorie": categorie, "priorite": prio}

def extraire_modele(titre: str) -> str:
    """Extrait un modèle potentiel du titre"""
    # Patterns courants: "Nike Dunk Low", "Jordan 1 Retro", etc.
    patterns = [
        r'(dunk|air force|jordan\s*\d|yeezy\s*\d{3}|new balance\s*\d{3,4}|stone island.*badge)',
        r'(tech fleece|cargo|hoodie|sweat|tee|t-shirt|veste|blouson|pantalon|jean)',
    ]
    t = titre.lower()
    for p in patterns:
        match = re.search(p, t, re.I)
        if match:
            return match.group(0).title()
    return ""

def extraire_taille(titre: str, size_title: str = None) -> str:
    """Normalise la taille"""
    if size_title and size_title != "?":
        return size_title.strip()
    # Fallback: chercher dans le titre
    match = re.search(r'\b(XS|S|M|L|XL|XXL|XXXL|\d{2}|W\d{2})\b', titre, re.I)
    return match.group(1).upper() if match else "?"

def extraire_etat(status: str) -> str:
    """Normalise l'état"""
    etats = {"neuf avec étiquette": "neuf_avec_etiquette", "neuf sans étiquette": "neuf_sans_etiquette", 
             "très bon état": "tres_bon_etat", "bon état": "bon_etat", "état satisfaisant": "satisfaisant"}
    s = status.lower().strip() if status else ""
    for k, v in etats.items():
        if k in s:
            return v
    return "non_precise"

══════════════════════════════════════════════════════════════════════════════
🔥 SCRAPER INTELLIGENT
══════════════════════════════════════════════════════════════════════════════
def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": "https://www.vinted.fr/catalog",
        "X-Requested-With": "XMLHttpRequest",
    })
    try:
        s.get("https://www.vinted.fr", timeout=10)
    except:
        pass
    return s

_session = _make_session()

def _fetch_newest(page: int = 1, per_page: int = 48) -> list:
    """Fetch les NOUVEAUX articles via API Vinted"""
    global _session
    url = f"https://www.vinted.fr/api/v2/catalog/items?order=newest_first&per_page={per_page}&page={page}"
    try:
        resp = _session.get(url, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"❌ fetch newest: {e}")
        return []

def _fetch_similaires(marque: str, modele: str = None, taille: str = None, categorie: str = None, limit: int = 10) -> list:
    """Trouve 3-10 articles similaires pour comparaison"""
    # Construire query intelligente
    query_parts = [marque]
    if modele and len(modele) > 3:
        query_parts.append(modele.split()[0])  # Premier mot du modèle
    if taille and taille != "?":
        query_parts.append(f"taille {taille}")
    
    query = " ".join(query_parts)
    url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={requests.utils.quote(query)}&order=price_asc&per_page={limit}"
    
    try:
        resp = _session.get(url, timeout=15)
        if resp.status_code == 401:
            _session = _make_session()
            resp = _session.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        items = resp.json().get("items", [])
        # Filtrer: même marque détectée
        result = []
        for item in items:
            det = detecter_marque_pro(item.get("title", ""), item.get("brand_title"))
            if det and det["marque"] == marque:
                result.append(item)
                if len(result) >= limit:
                    break
        return result
    except Exception as e:
        print(f"❌ fetch similaires: {e}")
        return []

def extraire_prix(item: dict) -> float | None:
    try:
        raw = item.get("price", {})
        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        return None

══════════════════════════════════════════════════════════════════════════════
🔥 CALCUL MARGE RÉELLE & PROPAGATION
══════════════════════════════════════════════════════════════════════════════
def calculer_marge_reelle(prix_achat: float, articles_similaires: list) -> tuple[float, float, list]:
    """Calcule marge réelle et retourne (prix_moyen, marge, liste_comparaisons)"""
    prix_similaires = []
    comparaisons = []
    
    for item in articles_similaires:
        p = extraire_prix(item)
        if p and p > 0:
            prix_similaires.append(p)
            comparaisons.append({
                "prix": p,
                "url": f"https://www.vinted.fr/items/{item.get('id')}",
                "titre": item.get("title", "")[:40]
            })
    
    if not prix_similaires:
        return prix_achat * 1.4, round(prix_achat * 0.4, 2), []  # Fallback
    
    prix_moyen = sum(prix_similaires) / len(prix_similaires)
    marge = round(prix_moyen * 0.90 - prix_achat, 2)  # -10% frais
    return round(prix_moyen, 2), marge, comparaisons[:10]  # Max 10 comparaisons

def appliquer_propagation(article_principal: dict, articles_similaires: list) -> dict:
    """Si un similaire est moins cher → il devient l'article principal"""
    prix_principal = extraire_prix(article_principal)
    if not prix_principal:
        return article_principal
    
    meilleur = article_principal
    meilleur_prix = prix_principal
    
    for item in articles_similaires:
        p = extraire_prix(item)
        if p and p < meilleur_prix:
            # Vérifier que c'est vraiment similaire (même marque/taille)
            det_principal = detecter_marque_pro(article_principal.get("title", ""))
            det_item = detecter_marque_pro(item.get("title", ""))
            if det_principal and det_item and det_principal["marque"] == det_item["marque"]:
                meilleur = item
                meilleur_prix = p
    
    return meilleur

══════════════════════════════════════════════════════════════════════════════
🔥 SCORE INTELLIGENT /100
══════════════════════════════════════════════════════════════════════════════
def calculer_score_pro(prix: float, prix_moyen: float, marge: float, marque_info: dict, 
                       titre: str, taille: str, etat: str) -> int:
    """Score PRO basé sur marge réelle, priorité marque, état, etc."""
    score = 0
    t = titre.lower()
    
    # 1. Ratio marge/prix (0-35 pts)
    ratio = marge / prix if prix > 0 else 0
    score += min(35, int(ratio * 55))
    
    # 2. Marge absolue (0-20 pts)
    if marge >= 100: score += 20
    elif marge >= 50: score += 15
    elif marge >= 30: score += 10
    elif marge >= 20: score += 7
    elif marge >= 10: score += 4
    
    # 3. Sous-côte vs prix moyen (0-10 pts)
    if prix_moyen > 0:
        ratio_marche = prix / prix_moyen
        if ratio_marche <= 0.25: score += 10
        elif ratio_marche <= 0.40: score += 7
        elif ratio_marche <= 0.60: score += 4
    
    # 4. Bonus priorité marque (0-15 pts)
    if marque_info:
        prio = marque_info.get("priorite", 1)
        score += prio * 5
    
    # 5. Bonus keywords hype (0-8 pts)
    hype_keywords = ["vintage", "deadstock", "ds", "rare", "limited", "collab", "og", "retro"]
    hype_count = sum(1 for k in hype_keywords if k in t)
    score += min(8, hype_count * 3)
    
    # 6. Bonus état premium (0-4 pts)
    if etat in ["neuf_avec_etiquette", "neuf_sans_etiquette", "tres_bon_etat"]:
        score += 4
    
    # 7. Bonus taille rare (0-2 pts)
    if taille.lower().strip() in ["xxs", "xs", "3xl", "4xl", "5xl", "6", "6.5", "13", "14", "15"]:
        score += 2
    
    return min(100, score)

def niveau_affaire(score: int) -> str:
    if score >= 90: return "💎 PÉPITE EXTRÊME"
    if score >= 78: return "🔥🔥🔥 ÉNORME AFFAIRE"
    if score >= 65: return "🔥🔥 TRÈS BONNE AFFAIRE"
    if score >= 50: return "🔥 BONNE AFFAIRE"
    return "👍 AFFAIRE CORRECTE"

══════════════════════════════════════════════════════════════════════════════
🔥 FONCTION analyse_propagation(url) - OFFICIELLE
══════════════════════════════════════════════════════════════════════════════
def analyse_propagation(url: str) -> dict | None:
    """
    Fonction officielle: analyse un article via son URL avec propagation.
    Retourne un dict avec toutes les infos ou None si erreur.
    """
    try:
        # Extraire item_id depuis URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        item_id = path_parts[-1] if path_parts else None
        
        if not item_id or not item_id.isdigit():
            print(f"❌ URL invalide: {url}")
            return None
        
        # Fetch l'article spécifique
        fetch_url = f"https://www.vinted.fr/api/v2/catalog/items/{item_id}"
        resp = _session.get(fetch_url, timeout=15)
        if resp.status_code != 200:
            return None
        
        item = resp.json().get("item") or resp.json()
        if not item:
            return None
        
        # Détection marque PRO
        marque_info = detecter_marque_pro(item.get("title", ""), item.get("brand_title"))
        if not marque_info:
            print(f"⚠️ Marque non reconnue pour: {item.get('title')}")
            return None
        
        # Extraire métadonnées
        prix = extraire_prix(item)
        if not prix or prix < config["prix_min"] or prix > config["prix_max"]:
            return None
        
        modele = extraire_modele(item.get("title", ""))
        taille = extraire_taille(item.get("title", ""), item.get("size_title"))
        etat = extraire_etat(item.get("status"))
        
        # Fetch articles similaires
        similaires = _fetch_similaires(
            marque=marque_info["marque"],
            modele=modele,
            taille=taille if taille != "?" else None,
            categorie=marque_info["categorie"],
            limit=10
        )
        
        if len(similaires) < 3:
            print(f"⚠️ Pas assez de similaires trouvés pour: {marque_info['marque']}")
            return None
        
        # Calcul marge réelle
        prix_moyen, marge, comparaisons = calculer_marge_reelle(prix, similaires)
        
        # Appliquer propagation
        meilleur_item = appliquer_propagation(item, similaires)
        meilleur_prix = extraire_prix(meilleur_item)
        meilleur_url = f"https://www.vinted.fr/items/{meilleur_item.get('id')}"
        
        # Calcul score
        score = calculer_score_pro(prix, prix_moyen, marge, marque_info, 
                                   item.get("title", ""), taille, etat)
        
        if score < config["score_min"]:
            return None
        
        # Préparer photo
        photos = item.get("photos", [])
        photo_url = photos[0].get("url") if photos and isinstance(photos[0], dict) else None
        
        return {
            "id": item.get("id"),
            "titre": item.get("title", ""),
            "marque": marque_info["marque"],
            "categorie": marque_info["categorie"],
            "modele": modele,
            "taille": taille,
            "etat": etat,
            "prix_achat": prix,
            "prix_moyen": prix_moyen,
            "revente_conseillee": round(prix_moyen * 0.90, 2),
            "marge_reelle": marge,
            "score": score,
            "niveau": niveau_affaire(score),
            "url_principal": meilleur_url,
            "url_original": f"https://www.vinted.fr/items/{item.get('id')}",
            "photo": photo_url,
            "comparaisons": comparaisons,
            "heure": time.strftime("%H:%M:%S"),
        }
        
    except Exception as e:
        print(f"❌ analyse_propagation erreur: {e}")
        return None

══════════════════════════════════════════════════════════════════════════════
🔥 MESSAGE TELEGRAM PRO - UN SEUL MESSAGE PAR ARTICLE
══════════════════════════════════════════════════════════════════════════════
def formater_message_pro(d: dict) -> tuple[str, InlineKeyboardMarkup, str | None]:
    """Retourne (texte, keyboard, photo_url) pour un message PRO"""
    
    # Ligne comparaisons
    comp_lines = ""
    for c in d.get("comparaisons", [])[:5]:  # Afficher max 5
        comp_lines += f"• {c['prix']}€ — {c['url']}\n"
    if not comp_lines:
        comp_lines = "• Aucune comparaison disponible\n"
    
    texte = (
        f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
        f"👕 <b>{d['titre']}</b>\n"
        f"🏷️ {d['marque']} | 📐 {d['taille']} | ✨ {d['etat'].replace('_', ' ').title()}\n"
        f"💶 Achat: <b>{d['prix_achat']}€</b> | 📈 Revente: {d['revente_conseillee']}€\n"
        f"💰 Marge réelle: <b>{d['marge_reelle']}€</b>\n\n"
        f"🔍 Comparaisons:\n{comp_lines}\n"
        f"🔗 <a href='{d['url_principal']}'>Voir l'article principal</a>"
    )
    
    # Keyboard interactif
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip_{d['id']}"),
            InlineKeyboardButton("⭐ Favoris", callback_data=f"fav_add_{d['id']}"),
            InlineKeyboardButton("🛒 Acheter", callback_data=f"buy_{d['id']}"),
        ]
    ])
    
    return texte, keyboard, d.get("photo")

══════════════════════════════════════════════════════════════════════════════
🔥 BOUCLE DE SCAN INTELLIGENTE
══════════════════════════════════════════════════════════════════════════════
async def boucle_scan(app: Application):
    """Scan continu avec détection PRO et propagation"""
    alert_queue: asyncio.Queue = asyncio.Queue()
    
    async def expediteur():
        """Envoie les messages avec cooldown et gestion mode flux"""
        while True:
            d = await alert_queue.get()
            texte, keyboard, photo = formater_message_pro(d)
            
            try:
                if photo and config["mode_flux"]:
                    # Mode flux: envoyer avec photo
                    await app.bot.send_photo(
                        chat_id=TELEGRAM_CHAT_ID,
                        photo=photo,
                        caption=texte,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    # Mode un message ou pas de photo
                    await app.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=texte,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                        reply_markup=keyboard,
                    )
            except Exception as e:
                print(f"❌ Telegram send error: {e}")
            
            # Cooldown adaptatif
            qs = alert_queue.qsize()
            delay = config["msg_cooldown"] * (1 + qs // 5)
            await asyncio.sleep(min(delay, 5))
    
    asyncio.create_task(expediteur())
    
    while True:
        if not config["actif"]:
            await asyncio.sleep(3)
            continue
        
        print(f"\n🔍 Scan PRO — {time.strftime('%H:%M:%S')}")
        alertes = 0
        
        # Fetch nouveaux articles
        items = await asyncio.to_thread(_fetch_newest, page=1, per_page=48)
        
        for item in items:
            if not config["actif"]:
                break
                
            item_id = item.get("id")
            if not item_id or item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            if len(seen_ids) > 50_000:
                seen_ids.difference_update(list(seen_ids)[:25_000])
            
            # Détection marque PRO + filtre selected_brands
            marque_info = detecter_marque_pro(item.get("title", ""), item.get("brand_title"))
            if not marque_info or marque_info["marque"] not in selected_brands:
                continue
            
            # Filtres de base
            prix = extraire_prix(item)
            if not prix or prix < config["prix_min"] or prix > config["prix_max"]:
                continue
            
            # Fetch similaires + calcul marge
            similaires = _fetch_similaires(
                marque=marque_info["marque"],
                modele=extraire_modele(item.get("title", "")),
                limite=10
            )
            if len(similaires) < 3:
                continue
            
            prix_moyen, marge, comparaisons = calculer_marge_reelle(prix, similaires)
            if marge < 10:  # Marge minimale
                continue
            
            # Propagation
            meilleur = appliquer_propagation(item, similaires)
            
            # Score final
            score = calculer_score_pro(
                prix, prix_moyen, marge, marque_info,
                item.get("title", ""), 
                extraire_taille(item.get("title", ""), item.get("size_title")),
                extraire_etat(item.get("status"))
            )
            
            if score < config["score_min"]:
                continue
            
            # Préparer données alerte
            photos = item.get("photos", [])
            photo_url = photos[0].get("url") if photos and isinstance(photos[0], dict) else None
            
            data = {
                "id": item_id,
                "titre": item.get("title", ""),
                "marque": marque_info["marque"],
                "categorie": marque_info["categorie"],
                "taille": extraire_taille(item.get("title", ""), item.get("size_title")),
                "etat": extraire_etat(item.get("status")),
                "prix_achat": prix,
                "prix_moyen": prix_moyen,
                "revente_conseillee": round(prix_moyen * 0.90, 2),
                "marge_reelle": marge,
                "score": score,
                "niveau": niveau_affaire(score),
                "url_principal": f"https://www.vinted.fr/items/{meilleur.get('id')}",
                "url_original": f"https://www.vinted.fr/items/{item_id}",
                "photo": photo_url,
                "comparaisons": comparaisons,
                "heure": time.strftime("%H:%M:%S"),
            }
            
            alertes += 1
            historique_alertes.appendleft(data)
            await alert_queue.put(data)
            print(f"  🚨 {data['titre'][:40]} | {data['marque']} | {data['score']}/100 | {data['marge_reelle']}€")
        
        print(f"✅ Cycle terminé — {alertes} pépites")
        await asyncio.sleep(2)  # Respiration entre cycles

══════════════════════════════════════════════════════════════════════════════
🔥 PANEL /bot — MENU PRINCIPAL
══════════════════════════════════════════════════════════════════════════════
def build_main_text() -> str:
    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
    mode = "🌊 Flux continu" if config["mode_flux"] else "📦 Un par un"
    return (
        f"🤖 <b>Vinted Bot PRO — Panel</b>\n"
        f"{'─'*32}\n"
        f"{'🟢' if config['actif'] else '🔴'} État: <b>{etat}</b>\n"
        f"📡 Mode: <b>{mode}</b>\n"
        f"📨 Cooldown: <b>{config['msg_cooldown']}s</b>\n"
        f"💶 Budget: <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"🎯 Score min: <b>{config['score_min']}/100</b>\n"
        f"🏷️ Marques: <b>{len(selected_brands)}/{len(marques)}</b>\n"
        f"{'─'*32}\n"
        f"<i>Choisis une catégorie:</i>"
    )

def build_main_keyboard() -> InlineKeyboardMarkup:
    etat_btn = "⏸ Pause" if config["actif"] else "▶️ Démarrer"
    etat_cb = "panel_pause" if config["actif"] else "panel_start"
    mode_btn = "📦 Mode: Un par un" if config["mode_flux"] else "🌊 Mode: Flux"
    mode_cb = "toggle_flux"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(etat_btn, callback_data=etat_cb),
         InlineKeyboardButton("⏹ Stop", callback_data="panel_stop")],
        [InlineKeyboardButton(mode_btn, callback_data=mode_cb)],
        [InlineKeyboardButton("📡 Scan", callback_data="menu_scan"),
         InlineKeyboardButton("💶 Budget", callback_data="menu_budget"),
         InlineKeyboardButton("🎯 Score", callback_data="menu_score")],
        [InlineKeyboardButton("🏷️ Marques", callback_data="menu_marques"),
         InlineKeyboardButton("📋 Historique", callback_data="menu_historique"),
         InlineKeyboardButton("⭐ Favoris", callback_data="menu_favoris")],
        [InlineKeyboardButton("🔁 Reset", callback_data="panel_reset"),
         InlineKeyboardButton("🔄 Refresh", callback_data="menu_main")],
    ])

══════════════════════════════════════════════════════════════════════════════
🔥 SOUS-PANEL MARQUES AVEC RECHERCHE
══════════════════════════════════════════════════════════════════════════════
def build_marques_text() -> str:
    query = config.get("search_query", "")
    search_hint = f"\n🔍 Recherche: <b>'{query}'</b>" if query else ""
    return (
        f"🏷️ <b>Gestion des marques</b>{search_hint}\n"
        f"{'─'*30}\n"
        f"Sélectionnées: <b>{len(selected_brands)}/{len(marques)}</b>\n"
        f"{'─'*30}\n"
        f"<i>Tape une marque pour filtrer, ou clique pour sélectionner.\n"
        f>Utilise /search <mot> pour rechercher.</i>"
    )

def get_filtered_marques() -> list:
    """Retourne les marques filtrées par search_query"""
    query = config.get("search_query", "").lower()
    if not query:
        return marques
    return [m for m in marques if query in m.lower()]

def build_marques_keyboard(page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    filtered = get_filtered_marques()
    total_pages = (len(filtered) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    page_marques = filtered[start:end]
    
    buttons = []
    for m in page_marques:
        checked = "✔ " if m in selected_brands else "  "
        buttons.append([InlineKeyboardButton(
            f"{checked}{m}", 
            callback_data=f"marque_toggle_{m}"
        )])
    
    # Navigation pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"marques_page_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages or 1}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"marques_page_{page+1}"))
    if nav_row:
        buttons.append(nav_row)
    
    # Boutons globaux
    buttons.append([
        InlineKeyboardButton("✅ Tout sélectionner", callback_data="marques_select_all"),
        InlineKeyboardButton("❌ Tout désélectionner", callback_data="marques_deselect_all"),
    ])
    buttons.append([
        InlineKeyboardButton("💾 Valider", callback_data="marques_validate"),
        InlineKeyboardButton("◀️ Retour", callback_data="menu_main"),
    ])
    
    return InlineKeyboardMarkup(buttons)

══════════════════════════════════════════════════════════════════════════════
🔥 AUTRES SOUS-MENUS (Scan, Budget, Score, Historique, Favoris)
══════════════════════════════════════════════════════════════════════════════
# [Les fonctions build_scan_text/keyboard, build_budget_text/keyboard, etc. 
#  sont conservées similaires à l'original avec adaptations mineures]

def build_scan_text() -> str:
    mode = "🌊 Flux continu" if config["mode_flux"] else "📦 Un message par article"
    return (
        f"📡 <b>Paramètres de scan</b>\n"
        f"{'─'*30}\n"
        f"Mode d'envoi: <b>{mode}</b>\n"
        f"Cooldown entre messages: <b>{config['msg_cooldown']}s</b>\n"
        f"{'─'*30}\n"
        f"<i>Choisis le délai:</i>"
    )

def build_scan_keyboard() -> InlineKeyboardMarkup:
    cd = config["msg_cooldown"]
    def mark(v): return f"✅ {v}s" if cd == v else f"{v}s"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(1), callback_data="msgcd_1"),
         InlineKeyboardButton(mark(2), callback_data="msgcd_2"),
         InlineKeyboardButton(mark(3), callback_data="msgcd_3")],
        [InlineKeyboardButton(mark(5), callback_data="msgcd_5"),
         InlineKeyboardButton(mark(10), callback_data="msgcd_10"),
         InlineKeyboardButton(mark(30), callback_data="msgcd_30")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

def build_budget_text() -> str:
    return (
        f"💶 <b>Filtre budget</b>\n"
        f"{'─'*30}\n"
        f"Actuel: <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
        f"{'─'*30}\n"
        f"<i>Choisis une plage:</i>"
    )

def build_budget_keyboard() -> InlineKeyboardMarkup:
    cur = (config["prix_min"], config["prix_max"])
    def mark(a, b): return f"✅ {a}–{b}€" if cur == (float(a), float(b)) else f"{a}–{b}€"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(3,30), callback_data="budget_3_30"),
         InlineKeyboardButton(mark(3,50), callback_data="budget_3_50"),
         InlineKeyboardButton(mark(5,50), callback_data="budget_5_50")],
        [InlineKeyboardButton(mark(5,100), callback_data="budget_5_100"),
         InlineKeyboardButton(mark(5,150), callback_data="budget_5_150"),
         InlineKeyboardButton(mark(5,200), callback_data="budget_5_200")],
        [InlineKeyboardButton(mark(10,300), callback_data="budget_10_300"),
         InlineKeyboardButton(mark(10,500), callback_data="budget_10_500")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

def build_score_text() -> str:
    s = config["score_min"]
    desc = "🟡 Large" if s < 50 else "🟠 Équilibré" if s < 65 else "🔴 Strict" if s < 80 else "💎 Expert"
    return (
        f"🎯 <b>Score minimum</b>\n"
        f"{'─'*30}\n"
        f"Actuel: <b>{s}/100</b> ({desc})\n"
        f"{'─'*30}\n"
        f"<i>Ajuste le seuil:</i>"
    )

def build_score_keyboard() -> InlineKeyboardMarkup:
    s = config["score_min"]
    def mark(v): return f"✅ {v}" if s == v else str(v)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(mark(40), callback_data="score_set_40"),
         InlineKeyboardButton(mark(50), callback_data="score_set_50"),
         InlineKeyboardButton(mark(55), callback_data="score_set_55"),
         InlineKeyboardButton(mark(60), callback_data="score_set_60")],
        [InlineKeyboardButton(mark(65), callback_data="score_set_65"),
         InlineKeyboardButton(mark(70), callback_data="score_set_70"),
         InlineKeyboardButton(mark(75), callback_data="score_set_75"),
         InlineKeyboardButton(mark(80), callback_data="score_set_80")],
        [InlineKeyboardButton("▼ -5", callback_data="score_down"),
         InlineKeyboardButton(f" {s}/100 ", callback_data="noop"),
         InlineKeyboardButton("▲ +5", callback_data="score_up")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

def build_historique_text() -> str:
    if not historique_alertes:
        return "📋 <b>Historique</b>\n\nAucune alerte."
    lines = [f"📋 <b>Historique — {len(historique_alertes)} alertes</b>\n{'─'*30}"]
    for i, d in enumerate(list(historique_alertes)[:10], 1):
        lines.append(f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
                    f"   {d['titre'][:35]} | {d['prix_achat']}€ → {d['marge_reelle']}€\n"
                    f"   <a href='{d['url_principal']}'>Voir</a>")
    if len(historique_alertes) > 10:
        lines.append(f"\n<i>... et {len(historique_alertes)-10} de plus</i>")
    return "\n".join(lines)

def build_historique_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Vider", callback_data="historique_clear")],
        [InlineKeyboardButton("◀️ Retour", callback_data="menu_main")],
    ])

def build_favoris_text() -> str:
    if not favoris:
        return "⭐ <b>Favoris</b>\n\nAucun favori.\n<i>Clique ⭐ dans une alerte pour ajouter.</i>"
    lines = [f"⭐ <b>Favoris — {len(favoris)} annonces</b>\n{'─'*30}"]
    for i, d in enumerate(favoris, 1):
        lines.append(f"\n<b>{i}.</b> {d['niveau']} <b>{d['score']}/100</b>\n"
                    f"   {d['titre'][:35]}\n"
                    f"   💶 {d['prix_achat']}€ | 💰 {d['marge_reelle']}€\n"
                    f"   <a href='{d['url_principal']}'>Voir</a>")
    return "\n".join(lines)

def build_favoris_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for i, d in enumerate(favoris[:8]):
        buttons.append([InlineKeyboardButton(
            f"🗑️ Supprimer #{i+1} — {d['titre'][:25]}",
            callback_data=f"fav_del_{i}"
        )])
    buttons.append([InlineKeyboardButton("🗑️ Vider tous", callback_data="fav_clear")])
    buttons.append([InlineKeyboardButton("◀️ Retour", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)

══════════════════════════════════════════════════════════════════════════════
ROUTEUR DE MENUS
══════════════════════════════════════════════════════════════════════════════
MENUS = {
    "main": (build_main_text, build_main_keyboard),
    "scan": (build_scan_text, build_scan_keyboard),
    "budget": (build_budget_text, build_budget_keyboard),
    "score": (build_score_text, build_score_keyboard),
    "marques": (build_marques_text, build_marques_keyboard),
    "historique": (build_historique_text, build_historique_keyboard),
    "favoris": (build_favoris_text, build_favoris_keyboard),
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

══════════════════════════════════════════════════════════════════════════════
🔥 COMMANDES TELEGRAM
══════════════════════════════════════════════════════════════════════════════
async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text_fn, kb_fn = MENUS["main"]
    await update.message.reply_text(text_fn(), reply_markup=kb_fn(), parse_mode="HTML")

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = True
    await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config["actif"] = False
    await update.message.reply_text("⏸ <b>Scan en pause.</b> Tape /start pour relancer.", parse_mode="HTML")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_main_text() + "\n\n👉 /bot pour le panel", parse_mode="HTML")

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
        assert pmin >= 0 and pmax > pmin
        config["prix_min"], config["prix_max"] = pmin, pmax
        await update.message.reply_text(f"💶 Budget: <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
    except:
        await update.message.reply_text("❌ Usage: /budget <min> <max> ex: /budget 5 150")

async def cmd_analyse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """🔥 COMMANDE OFFICIELLE /analyse <url>"""
    if not ctx.args:
        await update.message.reply_text("❌ Usage: /analyse <url_vinted>")
        return
    
    url = ctx.args[0]
    msg = await update.message.reply_text("🔍 Analyse en cours...")
    
    result = analyse_propagation(url)
    
    if not result:
        await msg.edit_text("❌ Impossible d'analyser cet article.\nVérifie l'URL ou la marque.")
        return
    
    texte, keyboard, photo = formater_message_pro(result)
    
    try:
        if photo:
            await msg.edit_media(InputMediaPhoto(media=photo, caption=texte, parse_mode="HTML"), reply_markup=keyboard)
        else:
            await msg.edit_text(texte, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=False)
    except:
        # Fallback si edit_media échoue
        await msg.delete()
        if photo:
            await update.message.reply_photo(photo=photo, caption=texte, parse_mode="HTML", reply_markup=keyboard)
        else:
            await update.message.reply_text(texte, parse_mode="HTML", reply_markup=keyboard)

async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Recherche de marques dans le panel"""
    if not ctx.args:
        config["search_query"] = ""
        await update.message.reply_text("🔍 Recherche effacée. Tape /search <mot> pour filtrer.")
        return
    query = " ".join(ctx.args).lower()
    config["search_query"] = query
    filtered = [m for m in marques if query in m.lower()]
    await update.message.reply_text(f"🔍 Résultats pour '{query}': {len(filtered)} marques\n\n👉 /bot → Marques pour gérer.")

══════════════════════════════════════════════════════════════════════════════
🔥 CALLBACK HANDLER
══════════════════════════════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Navigation menus
    if data.startswith("menu_"):
        menu = data.split("_", 1)[1]
        await afficher_menu(query, menu)
        return
    
    # Contrôle scan
    if data == "panel_start":
        config["actif"] = True
    elif data == "panel_pause":
        config["actif"] = False
    elif data == "panel_stop":
        config["actif"] = False
        await query.edit_message_text("⛔ Bot stoppé.")
        sys.exit(0)
    elif data == "toggle_flux":
        config["mode_flux"] = not config["mode_flux"]
    elif data == "panel_reset":
        config.update({"msg_cooldown": 1, "prix_min": 3.0, "prix_max": 200.0, "score_min": 60, "mode_flux": True})
        await afficher_menu(query, "main")
        return
    
    # Cooldown
    elif data.startswith("msgcd_"):
        config["msg_cooldown"] = int(data.split("_")[1])
        await afficher_menu(query, "scan")
        return
    
    # Budget
    elif data.startswith("budget_"):
        _, pmin, pmax = data.split("_")
        config["prix_min"], config["prix_max"] = float(pmin), float(pmax)
        await afficher_menu(query, "budget")
        return
    
    # Score
    elif data == "score_up":
        config["score_min"] = min(95, config["score_min"] + 5)
    elif data == "score_down":
        config["score_min"] = max(30, config["score_min"] - 5)
    elif data.startswith("score_set_"):
        config["score_min"] = int(data.split("_")[2])
    if data.startswith("score_"):
        await afficher_menu(query, "score")
        return
    
    # Marques - Gestion sélection
    elif data.startswith("marque_toggle_"):
        marque = data.replace("marque_toggle_", "")
        if marque in selected_brands:
            selected_brands.remove(marque)
        else:
            selected_brands.add(marque)
        await afficher_menu(query, "marques")
        return
    elif data.startswith("marques_page_"):
        config["marques_page"] = int(data.split("_")[2])
        await afficher_menu(query, "marques")
        return
    elif data == "marques_select_all":
        selected_brands.update(marques)
        await afficher_menu(query, "marques")
        return
    elif data == "marques_deselect_all":
        selected_brands.clear()
        await afficher_menu(query, "marques")
        return
    elif data == "marques_validate":
        await query.answer("✅ Marques sauvegardées !")
        await afficher_menu(query, "main")
        return
    
    # Historique
    elif data == "historique_clear":
        historique_alertes.clear()
        await afficher_menu(query, "historique")
        return
    
    # Favoris
    elif data.startswith("fav_add_"):
        item_id = data.split("_")[2]
        trouve = next((d for d in historique_alertes if str(d.get("id")) == item_id), None)
        if trouve and trouve not in favoris:
            favoris.append(trouve)
            await query.answer("⭐ Ajouté aux favoris !", show_alert=True)
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
    
    # Actions Skip/Buy (placeholder - à étendre)
    elif data.startswith("skip_") or data.startswith("buy_"):
        await query.answer("✅ Action enregistrée")
        return
    
    elif data == "noop":
        return
    
    # Refresh main
    await afficher_menu(query, "main")

══════════════════════════════════════════════════════════════════════════════
DÉMARRAGE
══════════════════════════════════════════════════════════════════════════════
async def post_init(app: Application):
    asyncio.create_task(boucle_scan(app))
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=(
            "🤖 <b>Bot Vinted PRO prêt !</b>\n\n"
            f"🏷️ {len(selected_brands)}/{len(marques)} marques actives\n"
            f"📡 Mode: {'Flux continu' if config['mode_flux'] else 'Un par un'}\n"
            f"📨 Cooldown: {config['msg_cooldown']}s\n"
            f"💶 Budget: {config['prix_min']}€ – {config['prix_max']}€\n"
            f"🎯 Score min: {config['score_min']}/100\n\n"
            "🔥 NOUVEAU:\n"
            "• /analyse <url> pour analyser un lien\n"
            "• /search <mot> pour filtrer les marques\n"
            "• Propagation intelligente activée\n\n"
            "👉 /bot pour le panel\n👉 /start pour lancer"
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
    
    # Commandes
    app.add_handler(CommandHandler("bot", cmd_bot))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("analyse", cmd_analyse))  # 🔥 Nouvelle commande
    app.add_handler(CommandHandler("search", cmd_search))     # 🔥 Recherche marques
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("📡 Bot Vinted PRO en écoute…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
