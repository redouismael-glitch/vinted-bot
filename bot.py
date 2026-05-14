diff --git a/bot.py b/bot.py
index 27a88c012e2839dc580292e5e428f9c169fcacf8..6435d543a4271a7394876c9ff0e50686592fa5d9 100644
--- a/bot.py
+++ b/bot.py
@@ -1,551 +1,771 @@
-import requests
-import time
-import os
 import asyncio
+import html
+import os
+import re
 import sys
-from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
-from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
+import time
+from collections import deque
+from typing import Any
+
+import requests
+from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
+from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  CONFIG
 # ══════════════════════════════════════════════════════════════════════════════
-TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
+TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
 TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
 
 if not TELEGRAM_TOKEN:
     raise EnvironmentError("❌ TELEGRAM_TOKEN manquant.")
 if not TELEGRAM_CHAT_ID:
     raise EnvironmentError("❌ TELEGRAM_CHAT_ID manquant.")
 
 # ══════════════════════════════════════════════════════════════════════════════
-#  MARQUES & RÈGLES
+#  MARQUES & RÈGLES BUSINESS
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
 
+MARQUE_ALIASES = {
+    "crtz": "corteiz",
+    "stüssy": "stussy",
+    "levis": "levi's",
+    "arcteryx": "arc'teryx",
+    "c.p. company": "cp company",
+    "the north face": "north face",
+    "polo ralph lauren": "ralph lauren",
+    "a bathing ape": "bape",
+    "a cold wall": "a-cold-wall",
+    "gallery dept.": "gallery dept",
+    "sézane": "sezane",
+}
+
 KEYWORDS_HYPE = {
-    "vintage", "deadstock", "ds", "vnds", "rare", "limited", "collab",
-    "og", "retro", "dunk", "air max", "air force", "jordan 1", "jordan 4",
-    "jordan 11", "350", "990", "2002r", "550", "travis", "sacai", "fragment",
+    "vintage", "deadstock", "vnds", "rare", "limited", "collab", "og", "retro",
+    "dunk", "air max", "air force", "jordan 1", "jordan 4", "jordan 11", "350",
+    "990", "2002r", "550", "travis", "sacai", "fragment", "gorpcore", "archive",
 }
 
 KEYWORDS_EXCLUS = {
-    "lot de", "pack", "déguisement", "costume", "bébé", "enfant",
-    "fille", "garçon", "chaussettes", "sous-vêtement",
+    "lot de", "pack", "déguisement", "deguisement", "costume", "bébé", "bebe",
+    "enfant", "fille", "garçon", "garcon", "chaussettes", "sous-vêtement",
+    "sous vetement", "réplique", "replica", "fake", "contrefaçon", "contrefacon",
 }
 
-# Marques avec bonus hype pour le score /100
 MARQUES_HYPE_BONUS = {
-    "chrome hearts", "hellstar", "gallery dept", "gallery dept.",
-    "rick owens", "drkshdw", "corteiz", "crtz", "supreme", "palace",
-    "off-white", "fear of god", "trapstar", "broken planet", "syna world",
-    "yeezy", "bape", "jordan", "air jordan", "represent", "minus two",
+    "chrome hearts", "hellstar", "gallery dept", "rick owens", "drkshdw", "corteiz",
+    "supreme", "palace", "off-white", "fear of god", "trapstar", "broken planet",
+    "syna world", "yeezy", "bape", "jordan", "air jordan", "represent", "minus two",
+}
+
+# Prix moyens statiques par marque pour mesurer la sous-côte avant d'alerter.
+PRIX_MOYEN_MARQUE = {
+    "chrome hearts": 260, "hellstar": 120, "gallery dept": 150, "rick owens": 280,
+    "drkshdw": 210, "denim tears": 140, "broken planet": 95, "minus two": 85,
+    "trapstar": 90, "represent": 80, "fear of god": 110, "essentials": 55,
+    "off-white": 160, "palm angels": 140, "corteiz": 110, "syna world": 90,
+    "supreme": 120, "palace": 95, "jordan": 115, "air jordan": 130,
+    "stone island": 120, "cp company": 95, "balenciaga": 260, "arc'teryx": 170,
+    "moncler": 260, "canada goose": 300, "north face": 85, "napapijri": 70,
+    "nike": 55, "adidas": 45, "new balance": 75, "ralph lauren": 55,
+    "jacquemus": 125, "ami paris": 115, "sandro": 70, "maje": 65,
+    "lacoste": 45, "tommy hilfiger": 45, "carhartt": 45, "levi's": 40,
+    "diesel": 55, "calvin klein": 35, "birkenstock": 60, "asics": 65,
+    "zara": 25, "uniqlo": 25, "_defaut": 45,
 }
 
 REGLES_MARGE = {
-    "chrome hearts":     (2.5, 30), "hellstar":          (2.5, 25),
-    "gallery dept":      (2.3, 25), "gallery dept.":     (2.3, 25),
-    "rick owens":        (2.2, 25), "drkshdw":           (2.2, 25),
-    "denim tears":       (2.2, 20), "broken planet":     (2.0, 20),
-    "minus two":         (2.0, 20), "trapstar":          (2.0, 20),
-    "represent":         (1.9, 18), "fear of god":       (1.9, 20),
-    "essentials":        (1.8, 15), "off-white":         (2.0, 25),
-    "palm angels":       (1.9, 20), "misbhv":            (1.8, 15),
-    "a-cold-wall":       (1.8, 15), "a cold wall":       (1.8, 15),
-    "vivienne westwood": (1.9, 20), "corteiz":           (2.2, 20),
-    "crtz":              (2.2, 20), "syna world":        (2.0, 18),
-    "vicinity":          (1.9, 15), "no faith studios":  (2.0, 15),
-    "supreme":           (2.5, 20), "palace":            (2.2, 20),
-    "jordan":            (1.8, 15), "air jordan":        (1.8, 15),
-    "stone island":      (1.7, 15), "cp company":        (1.7, 15),
-    "c.p. company":      (1.7, 15), "balenciaga":        (1.7, 20),
-    "arc'teryx":         (1.7, 20), "arcteryx":          (1.7, 20),
-    "moncler":           (1.7, 25), "canada goose":      (1.6, 20),
-    "north face":        (1.5, 10), "the north face":    (1.5, 10),
-    "napapijri":         (1.5, 10), "nike":              (1.5, 10),
-    "adidas":            (1.5, 10), "new balance":       (1.5, 10),
-    "ralph lauren":      (1.5, 10), "jacquemus":         (1.6, 12),
-    "ami paris":         (1.5, 12), "sandro":            (1.5, 10),
-    "maje":              (1.4,  8), "lacoste":           (1.4,  8),
-    "tommy hilfiger":    (1.4,  8), "carhartt":          (1.4,  8),
-    "levi's":            (1.3,  8), "levis":             (1.3,  8),
-    "diesel":            (1.4,  8), "calvin klein":      (1.3,  6),
-    "birkenstock":       (1.4,  8), "asics":             (1.4,  8),
-    "zara":              (1.3,  5), "uniqlo":            (1.3,  5),
-    "_defaut":           (1.4,  8),
+    "chrome hearts": (2.5, 30), "hellstar": (2.5, 25), "gallery dept": (2.3, 25),
+    "rick owens": (2.2, 25), "drkshdw": (2.2, 25), "denim tears": (2.2, 20),
+    "broken planet": (2.0, 20), "minus two": (2.0, 20), "trapstar": (2.0, 20),
+    "represent": (1.9, 18), "fear of god": (1.9, 20), "essentials": (1.8, 15),
+    "off-white": (2.0, 25), "palm angels": (1.9, 20), "misbhv": (1.8, 15),
+    "a-cold-wall": (1.8, 15), "vivienne westwood": (1.9, 20), "corteiz": (2.2, 20),
+    "syna world": (2.0, 18), "vicinity": (1.9, 15), "no faith studios": (2.0, 15),
+    "supreme": (2.5, 20), "palace": (2.2, 20), "jordan": (1.8, 15),
+    "air jordan": (1.8, 15), "stone island": (1.7, 15), "cp company": (1.7, 15),
+    "balenciaga": (1.7, 20), "arc'teryx": (1.7, 20), "moncler": (1.7, 25),
+    "canada goose": (1.6, 20), "north face": (1.5, 10), "napapijri": (1.5, 10),
+    "nike": (1.5, 10), "adidas": (1.5, 10), "new balance": (1.5, 10),
+    "ralph lauren": (1.5, 10), "jacquemus": (1.6, 12), "ami paris": (1.5, 12),
+    "sandro": (1.5, 10), "maje": (1.4, 8), "lacoste": (1.4, 8),
+    "tommy hilfiger": (1.4, 8), "carhartt": (1.4, 8), "levi's": (1.3, 8),
+    "diesel": (1.4, 8), "calvin klein": (1.3, 6), "birkenstock": (1.4, 8),
+    "asics": (1.4, 8), "zara": (1.3, 5), "uniqlo": (1.3, 5), "_defaut": (1.4, 8),
 }
 
+TAILLES_RARES = {"xxs", "xs", "xl", "xxl", "2xl", "46", "47", "48", "w28", "w29", "w34", "w36"}
+TAILLES_LIQUIDES = {"s", "m", "l", "40", "41", "42", "43", "44", "w30", "w31", "w32"}
+ETATS_PREMIUM = {"neuf avec étiquette", "neuf sans étiquette", "neuf", "très bon état", "tres bon etat"}
+
 SEARCH_QUERIES = [
-    "nike", "adidas", "jordan", "new balance", "stone island",
-    "lacoste", "ralph lauren", "tommy hilfiger", "supreme", "palace",
-    "corteiz", "north face", "carhartt", "stussy", "yeezy",
-    "arc'teryx", "moncler", "cp company", "napapijri", "hellstar",
-    "chrome hearts", "rick owens", "broken planet", "trapstar",
-    "represent", "fear of god", "off-white", "palm angels",
-    "gallery dept", "vivienne westwood", "syna world", "minus two",
+    "nike", "adidas", "jordan", "new balance", "stone island", "lacoste",
+    "ralph lauren", "tommy hilfiger", "supreme", "palace", "corteiz", "north face",
+    "carhartt", "stussy", "yeezy", "arc'teryx", "moncler", "cp company", "napapijri",
+    "hellstar", "chrome hearts", "rick owens", "broken planet", "trapstar", "represent",
+    "fear of god", "off-white", "palm angels", "gallery dept", "vivienne westwood",
+    "syna world", "minus two",
 ]
 
-# ══════════════════════════════════════════════════════════════════════════════
-#  ÉTAT GLOBAL
-# ══════════════════════════════════════════════════════════════════════════════
-config = {
-    "actif":        False,
-    "cooldown":     30,       # secondes
-    "prix_min":     3.0,
-    "prix_max":     200.0,
-    "score_min":    60,       # score /100 minimum pour alerter
-    "marques":      set(TOUTES_LES_MARQUES),
+DEFAULT_CONFIG = {
+    "actif": False,
+    "message_cooldown": 1.0,
+    "prix_min": 3.0,
+    "prix_max": 200.0,
+    "score_min": 60,
+    "marques": set(TOUTES_LES_MARQUES),
+    "scan_pause_query": 0.7,
 }
-seen_ids: set = set()
+config = DEFAULT_CONFIG | {"marques": set(DEFAULT_CONFIG["marques"])}
+
+MAX_SEEN_IDS = 30000
+MAX_ALERT_HISTORY = 30
+seen_ids = set()
+seen_queue = deque(maxlen=MAX_SEEN_IDS)
+favoris = []
+favoris_ids = set()
+alert_history = deque(maxlen=MAX_ALERT_HISTORY)
+last_alerts_by_id = {}
+
+BRANDS_BY_LENGTH = sorted(TOUTES_LES_MARQUES, key=len, reverse=True)
 
 # ══════════════════════════════════════════════════════════════════════════════
 #  SCRAPER
 # ══════════════════════════════════════════════════════════════════════════════
 def _make_session():
-    s = requests.Session()
-    s.headers.update({
+    session = requests.Session()
+    session.headers.update({
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
         "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
         "Accept-Language": "fr-FR,fr;q=0.9",
     })
     try:
-        s.get("https://www.vinted.fr", timeout=10)
+        session.get("https://www.vinted.fr", timeout=10)
     except Exception:
         pass
-    return s
+    return session
 
 _session = _make_session()
 
+
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
-        f"https://www.vinted.fr/api/v2/catalog/items"
+        "https://www.vinted.fr/api/v2/catalog/items"
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
-    except Exception as e:
-        print(f"❌ fetch '{query}': {e}")
+    except Exception as exc:
+        print(f"❌ fetch '{query}': {exc}")
         return []
 
 # ══════════════════════════════════════════════════════════════════════════════
-#  SCORE /100 INTELLIGENT
+#  FILTRAGE & SCORE
 # ══════════════════════════════════════════════════════════════════════════════
-def calculer_score(prix, revente, marge, marque, titre) -> int:
-    """
-    Score /100 basé sur :
-    - ratio marge/prix          → 0-45 pts
-    - marge absolue             → 0-20 pts
-    - bonus marque hype         → 0-15 pts
-    - bonus keywords hype       → 0-10 pts
-    - bonus sous-côte extrême   → 0-10 pts
-    """
-    t = titre.lower()
-    score = 0
+def normaliser_texte(value: Any) -> str:
+    return str(value or "").lower().strip()
+
+
+def extraire_prix(item):
+    try:
+        raw = item.get("price", {})
+        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
+    except (TypeError, ValueError):
+        return None
 
-    # 1. Ratio marge/prix (plus c'est sous-côté, plus le score monte)
-    ratio = marge / prix if prix > 0 else 0
-    score += min(45, int(ratio * 70))
 
-    # 2. Marge absolue
-    if marge >= 100: score += 20
-    elif marge >= 50: score += 15
-    elif marge >= 30: score += 10
-    elif marge >= 20: score += 7
-    elif marge >= 10: score += 4
+def extraire_etat(item) -> str:
+    for key in ("status", "status_title", "item_condition", "condition"):
+        value = item.get(key)
+        if isinstance(value, dict):
+            value = value.get("title") or value.get("name")
+        if value:
+            return str(value)
+    return "?"
+
+
+def contient_mot(texte: str, mot: str) -> bool:
+    if len(mot) <= 2:
+        return re.search(rf"(?<![\w-]){re.escape(mot)}(?![\w-])", texte) is not None
+    return re.search(rf"(?<!\w){re.escape(mot)}(?!\w)", texte) is not None
+
+
+def marque_canonique(marque: str) -> str:
+    return MARQUE_ALIASES.get(marque, marque)
+
+
+def detecter_marque(titre, marque_vinted):
+    texte_marque = normaliser_texte(marque_vinted)
+    texte_titre = normaliser_texte(titre)
+    marques_actives = {marque_canonique(m) for m in config["marques"]}
+
+    for marque in BRANDS_BY_LENGTH:
+        canon = marque_canonique(marque)
+        if canon not in marques_actives:
+            continue
+        if contient_mot(texte_marque, marque) or contient_mot(texte_titre, marque):
+            return canon
+    return None
+
+
+def calculer_confiance(prix, prix_moyen, marque, titre, taille, etat) -> int:
+    confiance = 45
+    if prix_moyen and prix <= prix_moyen * 0.35:
+        confiance += 25
+    elif prix_moyen and prix <= prix_moyen * 0.50:
+        confiance += 18
+    elif prix_moyen and prix <= prix_moyen * 0.70:
+        confiance += 10
 
-    # 3. Bonus marque hype
     if marque in MARQUES_HYPE_BONUS:
+        confiance += 12
+    if any(contient_mot(titre, keyword) for keyword in KEYWORDS_HYPE):
+        confiance += 10
+    if normaliser_texte(taille) in TAILLES_RARES:
+        confiance += 8
+    if normaliser_texte(etat) in ETATS_PREMIUM:
+        confiance += 8
+    return min(100, confiance)
+
+
+def calculer_score(prix, revente, marge, marque, titre, taille="?", etat="?", prix_moyen=None) -> int:
+    texte = normaliser_texte(titre)
+    taille_norm = normaliser_texte(taille)
+    etat_norm = normaliser_texte(etat)
+    score = 0
+
+    ratio_marge = marge / prix if prix > 0 else 0
+    score += min(32, int(ratio_marge * 55))
+
+    decote = ((prix_moyen - prix) / prix_moyen) if prix_moyen else 0
+    score += min(22, max(0, int(decote * 34)))
+
+    if marge >= 120:
+        score += 18
+    elif marge >= 70:
         score += 15
-    elif marque in REGLES_MARGE and REGLES_MARGE[marque][0] >= 1.8:
+    elif marge >= 40:
+        score += 11
+    elif marge >= 25:
         score += 8
+    elif marge >= 12:
+        score += 5
 
-    # 4. Bonus keywords hype dans le titre
-    hype_count = sum(1 for k in KEYWORDS_HYPE if k in t)
+    if marque in MARQUES_HYPE_BONUS:
+        score += 12
+    elif REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])[0] >= 1.8:
+        score += 7
+
+    hype_count = sum(1 for keyword in KEYWORDS_HYPE if contient_mot(texte, keyword))
     score += min(10, hype_count * 4)
 
-    # 5. Bonus sous-côte extrême (prix très bas par rapport à revente)
-    if revente > prix * 3:
+    if taille_norm in TAILLES_RARES:
+        score += 7
+    elif taille_norm in TAILLES_LIQUIDES:
+        score += 4
+
+    if etat_norm in ETATS_PREMIUM:
+        score += 7
+
+    if marge >= prix * 1.6:
         score += 10
-    elif revente > prix * 2.5:
+    elif marge >= prix:
         score += 6
 
     return min(100, score)
 
+
 def niveau_affaire(score: int) -> str:
-    if score >= 90: return "💎 PÉPITE EXTRÊME"
-    if score >= 78: return "🔥🔥🔥 ÉNORME AFFAIRE"
-    if score >= 65: return "🔥🔥 TRÈS BONNE AFFAIRE"
-    if score >= 50: return "🔥 BONNE AFFAIRE"
+    if score >= 90:
+        return "💎 PÉPITE EXTRÊME"
+    if score >= 78:
+        return "🔥🔥🔥 ÉNORME AFFAIRE"
+    if score >= 65:
+        return "🔥🔥 TRÈS BONNE AFFAIRE"
+    if score >= 50:
+        return "🔥 BONNE AFFAIRE"
     return "👍 AFFAIRE CORRECTE"
 
-# ══════════════════════════════════════════════════════════════════════════════
-#  FILTRAGE & ANALYSE
-# ══════════════════════════════════════════════════════════════════════════════
-def extraire_prix(item):
-    try:
-        raw = item.get("price", {})
-        return float(raw.get("amount", 0) if isinstance(raw, dict) else raw)
-    except (TypeError, ValueError):
-        return None
-
-def detecter_marque(titre, marque_vinted):
-    t = titre.lower()
-    m = marque_vinted.lower().strip()
-    for marque in config["marques"]:
-        if marque in m or marque in t:
-            return marque
-    return None
 
 def analyser(item):
-    titre      = item.get("title", "") or ""
+    titre = item.get("title", "") or ""
     marque_raw = item.get("brand_title", "") or ""
-    taille     = item.get("size_title", "?")
-    prix       = extraire_prix(item)
-    item_id    = item.get("id")
-    t          = titre.lower()
+    taille = item.get("size_title", "?") or "?"
+    etat = extraire_etat(item)
+    prix = extraire_prix(item)
+    item_id = item.get("id")
+    texte = normaliser_texte(f"{titre} {marque_raw}")
 
     if prix is None or prix < config["prix_min"] or prix > config["prix_max"]:
         return False, {}
-    if any(mot in t for mot in KEYWORDS_EXCLUS):
+    if any(mot in texte for mot in KEYWORDS_EXCLUS):
         return False, {}
 
     marque = detecter_marque(titre, marque_raw)
     if marque is None:
-        if not any(k in t for k in KEYWORDS_HYPE):
+        if not any(contient_mot(texte, keyword) for keyword in KEYWORDS_HYPE):
             return False, {}
         marque = "_defaut"
 
     coef, marge_min = REGLES_MARGE.get(marque, REGLES_MARGE["_defaut"])
-    revente = round(prix * coef, 2)
-    marge   = round(revente * 0.90 - prix, 2)
-    if marge < marge_min:
-        return False, {}
+    prix_moyen = PRIX_MOYEN_MARQUE.get(marque, PRIX_MOYEN_MARQUE["_defaut"])
+    revente = round(max(prix * coef, prix_moyen * 0.82), 2)
+    marge = round(revente * 0.90 - prix, 2)
+    confiance = calculer_confiance(prix, prix_moyen, marque, texte, taille, etat)
 
-    score = calculer_score(prix, revente, marge, marque, titre)
+    if marge < marge_min or confiance < 50:
+        return False, {}
 
+    score = calculer_score(prix, revente, marge, marque, titre, taille, etat, prix_moyen)
     if score < config["score_min"]:
         return False, {}
 
-    return True, {
-        "titre":   titre,
-        "marque":  marque_raw or marque,
-        "taille":  taille,
-        "prix":    prix,
+    data = {
+        "id": str(item_id),
+        "titre": titre,
+        "marque": marque_raw or marque,
+        "marque_detectee": marque,
+        "taille": taille,
+        "etat": etat,
+        "prix": prix,
+        "prix_moyen": prix_moyen,
         "revente": revente,
-        "marge":   marge,
-        "score":   score,
-        "niveau":  niveau_affaire(score),
-        "url":     f"https://www.vinted.fr/items/{item_id}",
+        "marge": marge,
+        "score": score,
+        "confiance": confiance,
+        "niveau": niveau_affaire(score),
+        "url": f"https://www.vinted.fr/items/{item_id}",
+        "date": time.strftime("%d/%m %H:%M"),
     }
+    return True, data
+
+# ══════════════════════════════════════════════════════════════════════════════
+#  ALERTES, FAVORIS & MÉMOIRE
+# ══════════════════════════════════════════════════════════════════════════════
+def memoriser_id(item_id) -> bool:
+    item_id = str(item_id)
+    if item_id in seen_ids:
+        return False
+    if len(seen_queue) == MAX_SEEN_IDS:
+        old_id = seen_queue.popleft()
+        seen_ids.discard(old_id)
+    seen_ids.add(item_id)
+    seen_queue.append(item_id)
+    return True
+
+
+def format_euros(value) -> str:
+    return f"{float(value):.2f}".rstrip("0").rstrip(".") + "€"
+
+
+def format_alert_message(data: dict) -> str:
+    return (
+        f"{data['niveau']} — <b>{data['score']}/100</b> · confiance <b>{data['confiance']}%</b>\n\n"
+        f"👕 <b>{html.escape(data['titre'])}</b>\n"
+        f"🏷️ Marque : {html.escape(data['marque'])}\n"
+        f"📐 Taille : {html.escape(str(data['taille']))}\n"
+        f"✨ État : {html.escape(str(data['etat']))}\n"
+        f"💶 Prix achat : <b>{format_euros(data['prix'])}</b>\n"
+        f"📊 Prix moyen marque : ~{format_euros(data['prix_moyen'])}\n"
+        f"📈 Revente estimée : ~{format_euros(data['revente'])}\n"
+        f"💰 Marge nette : ~<b>{format_euros(data['marge'])}</b>\n\n"
+        f"🔗 <a href='{html.escape(data['url'])}'>Voir l'annonce</a>"
+    )
+
+
+def alert_keyboard(item_id: str) -> InlineKeyboardMarkup:
+    return InlineKeyboardMarkup([
+        [InlineKeyboardButton("⭐ Ajouter aux favoris", callback_data=f"fav_add_{item_id}")],
+        [InlineKeyboardButton("📁 Voir les favoris", callback_data="fav_list")],
+    ])
+
+
+def ajouter_favori(item_id: str) -> bool:
+    data = last_alerts_by_id.get(str(item_id))
+    if not data or str(item_id) in favoris_ids:
+        return False
+    favoris.append(data)
+    favoris_ids.add(str(item_id))
+    return True
+
+
+def liste_annonces(items, titre: str) -> str:
+    if not items:
+        return f"{titre}\n\nAucune annonce pour le moment."
+    lignes = [titre, ""]
+    for index, data in enumerate(reversed(items), start=1):
+        lignes.append(
+            f"{index}. <b>{html.escape(data['titre'][:70])}</b>\n"
+            f"   {data['niveau']} · {data['score']}/100 · {format_euros(data['prix'])} → marge ~{format_euros(data['marge'])}\n"
+            f"   🏷️ {html.escape(data['marque'])} · 📐 {html.escape(str(data['taille']))}\n"
+            f"   🔗 {html.escape(data['url'])}"
+        )
+    return "\n\n".join(lignes)[:3900]
+
+
+def cooldown_messages_adaptatif(alertes_batch: int) -> float:
+    return config["message_cooldown"] + min(4.0, max(0, alertes_batch - 1) * 0.25)
+
+
+async def envoyer_alerte(app: Application, data: dict, alertes_batch: int):
+    last_alerts_by_id[data["id"]] = data
+    alert_history.append(data)
+    await app.bot.send_message(
+        chat_id=TELEGRAM_CHAT_ID,
+        text=format_alert_message(data),
+        parse_mode="HTML",
+        disable_web_page_preview=False,
+        reply_markup=alert_keyboard(data["id"]),
+    )
+    await asyncio.sleep(cooldown_messages_adaptatif(alertes_batch))
 
 # ══════════════════════════════════════════════════════════════════════════════
-#  BOUCLE DE SCAN
+#  BOUCLE DE SCAN CONTINU
 # ══════════════════════════════════════════════════════════════════════════════
 async def boucle_scan(app: Application):
-    loop = asyncio.get_event_loop()
+    loop = asyncio.get_running_loop()
 
     while True:
         if not config["actif"]:
-            await asyncio.sleep(3)
+            await asyncio.sleep(1.5)
             continue
 
-        print(f"\n🔍 Scan — {time.strftime('%H:%M:%S')}")
+        print(f"\n🔍 Scan continu — {time.strftime('%H:%M:%S')}")
         alertes = 0
 
         for query in SEARCH_QUERIES:
             if not config["actif"]:
                 break
+
             try:
                 items = await loop.run_in_executor(None, _fetch_sync, query)
-            except Exception as e:
-                print(f"❌ Executor: {e}")
+            except Exception as exc:
+                print(f"❌ Executor: {exc}")
                 items = []
 
             for item in items:
                 item_id = item.get("id")
-                if not item_id or item_id in seen_ids:
+                if not item_id or not memoriser_id(item_id):
                     continue
-                seen_ids.add(item_id)
-
-                # Libère mémoire si trop d'IDs
-                if len(seen_ids) > 50000:
-                    seen_ids.clear()
 
-                ok, d = analyser(item)
+                ok, data = analyser(item)
                 if not ok:
                     continue
 
                 alertes += 1
-                msg = (
-                    f"{d['niveau']} — <b>{d['score']}/100</b>\n\n"
-                    f"👕 <b>{d['titre']}</b>\n"
-                    f"🏷️ Marque : {d['marque']}\n"
-                    f"📐 Taille : {d['taille']}\n"
-                    f"💶 Prix achat : {d['prix']}€\n"
-                    f"📈 Revente estimée : ~{d['revente']}€\n"
-                    f"💰 Marge nette : ~{d['marge']}€\n\n"
-                    f"🔗 <a href='{d['url']}'>Voir l'annonce</a>"
-                )
-                print(f"  🚨 {d['titre'][:45]} | score {d['score']}/100 | marge ~{d['marge']}€")
+                print(f"  🚨 {data['titre'][:45]} | score {data['score']}/100 | marge ~{format_euros(data['marge'])}")
                 try:
-                    await app.bot.send_message(
-                        chat_id=TELEGRAM_CHAT_ID,
-                        text=msg,
-                        parse_mode="HTML",
-                        disable_web_page_preview=False,
-                    )
-                except Exception as e:
-                    print(f"❌ Telegram: {e}")
-                await asyncio.sleep(0.5)
-
-            await asyncio.sleep(2)
-
-        print(f"✅ Scan terminé — {alertes} alertes | prochain dans {config['cooldown']}s")
-
-        # Cooldown en secondes — réactif au stop/pause
-        elapsed = 0
-        while elapsed < config["cooldown"]:
-            if not config["actif"]:
-                break
-            await asyncio.sleep(1)
-            elapsed += 1
+                    await envoyer_alerte(app, data, alertes)
+                except Exception as exc:
+                    print(f"❌ Telegram: {exc}")
+
+            await asyncio.sleep(config["scan_pause_query"])
+
+        print(f"✅ Cycle terminé — {alertes} alertes | reprise immédiate")
+        await asyncio.sleep(0.2)
 
 # ══════════════════════════════════════════════════════════════════════════════
-#  PANEL /bot — BOUTONS INLINE
+#  PANEL /bot
 # ══════════════════════════════════════════════════════════════════════════════
-def build_panel_keyboard():
-    etat_btn  = "⏸ Pause" if config["actif"] else "▶️ Start"
-    etat_cb   = "panel_pause" if config["actif"] else "panel_start"
-    score_min = config["score_min"]
-
-    keyboard = [
-        [
-            InlineKeyboardButton(etat_btn, callback_data=etat_cb),
-            InlineKeyboardButton("⏹ Stop", callback_data="panel_stop"),
-        ],
-        [
-            InlineKeyboardButton("⏱ Cooldown 10s",  callback_data="cd_10"),
-            InlineKeyboardButton("⏱ Cooldown 30s",  callback_data="cd_30"),
-            InlineKeyboardButton("⏱ Cooldown 60s",  callback_data="cd_60"),
-        ],
-        [
-            InlineKeyboardButton("⏱ Cooldown 2min", callback_data="cd_120"),
-            InlineKeyboardButton("⏱ Cooldown 5min", callback_data="cd_300"),
-        ],
-        [
-            InlineKeyboardButton("💶 Budget 5–50€",   callback_data="budget_5_50"),
-            InlineKeyboardButton("💶 Budget 5–100€",  callback_data="budget_5_100"),
-            InlineKeyboardButton("💶 Budget 5–200€",  callback_data="budget_5_200"),
-        ],
-        [
-            InlineKeyboardButton(f"🎯 Score min: {score_min}/100 ▼", callback_data="score_down"),
-            InlineKeyboardButton(f"🎯 Score min: {score_min}/100 ▲", callback_data="score_up"),
-        ],
-        [
-            InlineKeyboardButton("🔄 Actualiser", callback_data="panel_refresh"),
-        ],
-    ]
+def build_panel_text(menu="main"):
+    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
+    header = (
+        "🤖 <b>Panel Vinted Bot</b>\n"
+        "━━━━━━━━━━━━━━━━━━━━\n"
+        f"🔎 Scan : <b>{etat}</b> · continu, sans cooldown global\n"
+        f"📨 Délai Telegram : <b>{config['message_cooldown']}s</b> par message\n"
+        f"💶 Budget : <b>{format_euros(config['prix_min'])} – {format_euros(config['prix_max'])}</b>\n"
+        f"🎯 Score minimum : <b>{config['score_min']}/100</b>\n"
+        f"🏷️ Marques actives : <b>{len(config['marques'])}</b>/{len(TOUTES_LES_MARQUES)}\n"
+        f"⭐ Favoris : <b>{len(favoris)}</b> · 🕘 Alertes : <b>{len(alert_history)}</b>\n"
+        "━━━━━━━━━━━━━━━━━━━━\n"
+    )
+    descriptions = {
+        "main": "Choisis une catégorie ci-dessous : scan, budget, score, messages, marques ou favoris.",
+        "scan": "🔎 <b>Scan</b>\nLe scan tourne en continu. Seuls les messages Telegram ont un délai.",
+        "budget": "💶 <b>Budget</b>\nFiltre les annonces hors fourchette avant le score pour réduire le bruit.",
+        "score": "🎯 <b>Score</b>\nPlus le seuil est haut, moins tu reçois d'alertes mais elles sont plus sélectives.",
+        "messages": "📨 <b>Cooldown Telegram</b>\nDélai indépendant entre deux alertes envoyées à Telegram.",
+        "marques": "🏷️ <b>Marques</b>\nActive toutes les marques ou concentre-toi sur les marques hype.",
+    }
+    return header + descriptions.get(menu, descriptions["main"])
+
+
+def build_panel_keyboard(menu="main"):
+    etat_btn = "⏸ Pause scan" if config["actif"] else "▶️ Start scan"
+    etat_cb = "panel_pause" if config["actif"] else "panel_start"
+
+    if menu == "scan":
+        keyboard = [
+            [InlineKeyboardButton(etat_btn, callback_data=etat_cb), InlineKeyboardButton("⏹ Stop app", callback_data="panel_stop")],
+            [InlineKeyboardButton("🔄 Actualiser", callback_data="menu_scan"), InlineKeyboardButton("🏠 Accueil", callback_data="menu_main")],
+        ]
+    elif menu == "budget":
+        keyboard = [
+            [InlineKeyboardButton("💶 3–50€", callback_data="budget_3_50"), InlineKeyboardButton("💶 5–100€", callback_data="budget_5_100")],
+            [InlineKeyboardButton("💶 5–200€", callback_data="budget_5_200"), InlineKeyboardButton("💎 20–500€", callback_data="budget_20_500")],
+            [InlineKeyboardButton("⬅️ Retour", callback_data="menu_main")],
+        ]
+    elif menu == "score":
+        keyboard = [
+            [InlineKeyboardButton("➖ -5", callback_data="score_down"), InlineKeyboardButton(f"🎯 {config['score_min']}/100", callback_data="menu_score"), InlineKeyboardButton("➕ +5", callback_data="score_up")],
+            [InlineKeyboardButton("🟢 Large 50", callback_data="score_set_50"), InlineKeyboardButton("🟠 Sélectif 70", callback_data="score_set_70")],
+            [InlineKeyboardButton("🔴 Elite 85", callback_data="score_set_85"), InlineKeyboardButton("⬅️ Retour", callback_data="menu_main")],
+        ]
+    elif menu == "messages":
+        keyboard = [
+            [InlineKeyboardButton("⚡ 0.5s", callback_data="msgcd_0.5"), InlineKeyboardButton("✅ 1s", callback_data="msgcd_1")],
+            [InlineKeyboardButton("🧘 2s", callback_data="msgcd_2"), InlineKeyboardButton("🐢 5s", callback_data="msgcd_5")],
+            [InlineKeyboardButton("⬅️ Retour", callback_data="menu_main")],
+        ]
+    elif menu == "marques":
+        keyboard = [
+            [InlineKeyboardButton("🔥 Hype only", callback_data="brands_hype"), InlineKeyboardButton("🏷️ Toutes", callback_data="brands_all")],
+            [InlineKeyboardButton("📋 Voir marques", callback_data="brands_list"), InlineKeyboardButton("⬅️ Retour", callback_data="menu_main")],
+        ]
+    else:
+        keyboard = [
+            [InlineKeyboardButton(etat_btn, callback_data=etat_cb), InlineKeyboardButton("🔄 Actualiser", callback_data="menu_main")],
+            [InlineKeyboardButton("🔎 Scan", callback_data="menu_scan"), InlineKeyboardButton("💶 Budget", callback_data="menu_budget")],
+            [InlineKeyboardButton("🎯 Score", callback_data="menu_score"), InlineKeyboardButton("📨 Cooldown messages", callback_data="menu_messages")],
+            [InlineKeyboardButton("🏷️ Marques", callback_data="menu_marques"), InlineKeyboardButton("⭐ Favoris", callback_data="fav_list")],
+            [InlineKeyboardButton("🕘 Historique des alertes", callback_data="history_list")],
+            [InlineKeyboardButton("♻️ Reset configuration", callback_data="config_reset")],
+        ]
     return InlineKeyboardMarkup(keyboard)
 
-def build_panel_text():
-    etat   = "✅ Actif" if config["actif"] else "⏸ En pause"
-    return (
-        f"🤖 <b>Panel Vinted Bot</b>\n\n"
-        f"État : {etat}\n"
-        f"⏱️ Cooldown : <b>{config['cooldown']}s</b>\n"
-        f"💶 Budget : <b>{config['prix_min']}€ – {config['prix_max']}€</b>\n"
-        f"🎯 Score minimum : <b>{config['score_min']}/100</b>\n"
-        f"🏷️ Marques actives : <b>{len(config['marques'])}</b>\n\n"
-        f"<i>Utilise les boutons pour tout contrôler.</i>"
+
+async def afficher_panel(query, menu="main"):
+    await query.edit_message_text(
+        build_panel_text(menu),
+        reply_markup=build_panel_keyboard(menu),
+        parse_mode="HTML",
     )
 
+
 async def cmd_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     await update.message.reply_text(
         build_panel_text(),
         reply_markup=build_panel_keyboard(),
         parse_mode="HTML",
     )
 
+
 async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     query = update.callback_query
     await query.answer()
-    data  = query.data
+    data = query.data
+    menu = "main"
+
+    if data.startswith("menu_"):
+        await afficher_panel(query, data.replace("menu_", ""))
+        return
 
     if data == "panel_start":
         config["actif"] = True
-
     elif data == "panel_pause":
         config["actif"] = False
-
     elif data == "panel_stop":
         config["actif"] = False
         await query.edit_message_text("⛔ Bot arrêté. Railway va le redémarrer automatiquement.")
         sys.exit(0)
-
-    elif data == "panel_refresh":
-        pass  # juste rafraîchir l'affichage
-
-    elif data.startswith("cd_"):
-        config["cooldown"] = int(data.split("_")[1])
-
     elif data.startswith("budget_"):
         _, pmin, pmax = data.split("_")
         config["prix_min"] = float(pmin)
         config["prix_max"] = float(pmax)
-
+        menu = "budget"
     elif data == "score_up":
         config["score_min"] = min(95, config["score_min"] + 5)
-
+        menu = "score"
     elif data == "score_down":
         config["score_min"] = max(30, config["score_min"] - 5)
+        menu = "score"
+    elif data.startswith("score_set_"):
+        config["score_min"] = int(data.rsplit("_", 1)[1])
+        menu = "score"
+    elif data.startswith("msgcd_"):
+        config["message_cooldown"] = float(data.split("_", 1)[1])
+        menu = "messages"
+    elif data == "brands_hype":
+        config["marques"] = set(MARQUES_HYPE_BONUS)
+        menu = "marques"
+    elif data == "brands_all":
+        config["marques"] = set(TOUTES_LES_MARQUES)
+        menu = "marques"
+    elif data == "brands_list":
+        text = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"]))
+        await query.edit_message_text(text[:3900], reply_markup=build_back_keyboard(), parse_mode="HTML")
+        return
+    elif data == "config_reset":
+        reset_config()
+    elif data == "fav_list":
+        await query.edit_message_text(liste_annonces(favoris, "⭐ <b>Favoris</b>"), reply_markup=build_back_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
+        return
+    elif data == "history_list":
+        await query.edit_message_text(liste_annonces(list(alert_history), "🕘 <b>Historique des alertes</b>"), reply_markup=build_back_keyboard(), parse_mode="HTML", disable_web_page_preview=True)
+        return
+    elif data.startswith("fav_add_"):
+        item_id = data.replace("fav_add_", "", 1)
+        added = ajouter_favori(item_id)
+        await query.answer("⭐ Ajouté aux favoris" if added else "Déjà en favoris ou annonce introuvable", show_alert=False)
+        return
+
+    await afficher_panel(query, menu)
+
+
+def build_back_keyboard():
+    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Retour panel", callback_data="menu_main")]])
 
-    # Mise à jour du panel
-    try:
-        await query.edit_message_text(
-            build_panel_text(),
-            reply_markup=build_panel_keyboard(),
-            parse_mode="HTML",
-        )
-    except Exception:
-        pass
+
+def reset_config():
+    config.clear()
+    config.update(DEFAULT_CONFIG | {"marques": set(DEFAULT_CONFIG["marques"])})
 
 # ══════════════════════════════════════════════════════════════════════════════
-#  COMMANDES TEXTE (gardées pour compatibilité)
+#  COMMANDES TEXTE
 # ══════════════════════════════════════════════════════════════════════════════
 async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     config["actif"] = True
-    await update.message.reply_text("✅ <b>Scan activé !</b>", parse_mode="HTML")
+    await update.message.reply_text("✅ <b>Scan continu activé !</b>", parse_mode="HTML")
+
 
 async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     config["actif"] = False
     await update.message.reply_text("⏸ <b>Scan mis en pause.</b>\nTape /start pour relancer.", parse_mode="HTML")
 
+
 async def cmd_cooldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     try:
-        secondes = int(ctx.args[0])
-        assert secondes >= 1
-        config["cooldown"] = secondes
-        await update.message.reply_text(f"⏱️ Cooldown : <b>{secondes}s</b>", parse_mode="HTML")
+        secondes = float(ctx.args[0])
+        assert secondes >= 0.1
+        config["message_cooldown"] = secondes
+        await update.message.reply_text(f"📨 Cooldown Telegram : <b>{secondes}s</b>", parse_mode="HTML")
     except Exception:
-        await update.message.reply_text("❌ Usage : /cooldown &lt;secondes&gt;  ex: /cooldown 30")
+        await update.message.reply_text("❌ Usage : /cooldown &lt;secondes&gt;  ex: /cooldown 1")
+
 
 async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     try:
         pmin, pmax = float(ctx.args[0]), float(ctx.args[1])
         assert pmin >= 0 and pmax > pmin
         config["prix_min"], config["prix_max"] = pmin, pmax
-        await update.message.reply_text(f"💶 Budget : <b>{pmin}€ – {pmax}€</b>", parse_mode="HTML")
+        await update.message.reply_text(f"💶 Budget : <b>{format_euros(pmin)} – {format_euros(pmax)}</b>", parse_mode="HTML")
     except Exception:
         await update.message.reply_text("❌ Usage : /budget &lt;min&gt; &lt;max&gt;  ex: /budget 5 150")
 
+
 async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
-    etat = "✅ Actif" if config["actif"] else "⏸ En pause"
-    await update.message.reply_text(
-        f"<b>📊 Status</b>\n\n"
-        f"État : {etat}\n"
-        f"⏱️ Cooldown : {config['cooldown']}s\n"
-        f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
-        f"🎯 Score min : {config['score_min']}/100\n"
-        f"🏷️ Marques : {len(config['marques'])}\n\n"
-        "👉 Tape /bot pour le panel interactif",
-        parse_mode="HTML"
-    )
+    await update.message.reply_text(build_panel_text(), parse_mode="HTML")
+
+
+async def cmd_favoris(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
+    await update.message.reply_text(liste_annonces(favoris, "⭐ <b>Favoris</b>"), parse_mode="HTML", disable_web_page_preview=True)
+
+
+async def cmd_historique(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
+    await update.message.reply_text(liste_annonces(list(alert_history), "🕘 <b>Historique des alertes</b>"), parse_mode="HTML", disable_web_page_preview=True)
+
 
 async def cmd_marque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
     try:
         action = ctx.args[0].lower()
     except IndexError:
-        await update.message.reply_text("Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n/marque reset\n/marque list")
+        await update.message.reply_text("Usage :\n/marque add &lt;nom&gt;\n/marque remove &lt;nom&gt;\n/marque reset\n/marque hype\n/marque list")
         return
 
     if action == "reset":
         config["marques"] = set(TOUTES_LES_MARQUES)
         await update.message.reply_text(f"✅ {len(config['marques'])} marques réactivées.")
+    elif action == "hype":
+        config["marques"] = set(MARQUES_HYPE_BONUS)
+        await update.message.reply_text(f"🔥 Mode hype : {len(config['marques'])} marques actives.")
     elif action == "list":
         texte = "🏷️ <b>Marques actives :</b>\n" + ", ".join(sorted(config["marques"]))
-        await update.message.reply_text(texte[:4000], parse_mode="HTML")
+        await update.message.reply_text(texte[:3900], parse_mode="HTML")
     elif action in ("add", "remove"):
-        nom = " ".join(ctx.args[1:]).lower().strip()
+        nom = normaliser_texte(" ".join(ctx.args[1:]))
         if not nom:
             await update.message.reply_text(f"❌ Usage : /marque {action} &lt;nom&gt;")
             return
         if action == "add":
             config["marques"].add(nom)
-            await update.message.reply_text(f"✅ Ajouté : <b>{nom}</b>", parse_mode="HTML")
+            await update.message.reply_text(f"✅ Ajouté : <b>{html.escape(nom)}</b>", parse_mode="HTML")
         else:
             config["marques"].discard(nom)
-            await update.message.reply_text(f"🗑️ Retiré : <b>{nom}</b>", parse_mode="HTML")
+            await update.message.reply_text(f"🗑️ Retiré : <b>{html.escape(nom)}</b>", parse_mode="HTML")
     else:
-        await update.message.reply_text("❌ Action inconnue : add / remove / reset / list")
+        await update.message.reply_text("❌ Action inconnue : add / remove / reset / hype / list")
 
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
-            f"⏱️ Cooldown : {config['cooldown']}s\n"
-            f"💶 Budget : {config['prix_min']}€ – {config['prix_max']}€\n"
+            "🔎 Scan continu, sans cooldown global\n"
+            f"📨 Cooldown Telegram : {config['message_cooldown']}s\n"
+            f"💶 Budget : {format_euros(config['prix_min'])} – {format_euros(config['prix_max'])}\n"
             f"🎯 Score min : {config['score_min']}/100\n\n"
             "👉 Tape /bot pour ouvrir le panel\n"
             "👉 Tape /start pour lancer le scan"
         ),
         parse_mode="HTML",
     )
 
+
 def main():
-    app = (
-        Application.builder()
-        .token(TELEGRAM_TOKEN)
-        .post_init(post_init)
-        .build()
-    )
-    app.add_handler(CommandHandler("bot",      cmd_bot))
-    app.add_handler(CommandHandler("start",    cmd_start))
-    app.add_handler(CommandHandler("stop",     cmd_stop))
+    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
+    app.add_handler(CommandHandler("bot", cmd_bot))
+    app.add_handler(CommandHandler("start", cmd_start))
+    app.add_handler(CommandHandler("stop", cmd_stop))
     app.add_handler(CommandHandler("cooldown", cmd_cooldown))
-    app.add_handler(CommandHandler("budget",   cmd_budget))
-    app.add_handler(CommandHandler("marque",   cmd_marque))
-    app.add_handler(CommandHandler("status",   cmd_status))
+    app.add_handler(CommandHandler("budget", cmd_budget))
+    app.add_handler(CommandHandler("marque", cmd_marque))
+    app.add_handler(CommandHandler("status", cmd_status))
+    app.add_handler(CommandHandler("favoris", cmd_favoris))
+    app.add_handler(CommandHandler("historique", cmd_historique))
     app.add_handler(CallbackQueryHandler(handle_callback))
 
     print("📡 Bot en écoute…")
     app.run_polling(drop_pending_updates=True)
 
+
 if __name__ == "__main__":
     main()
