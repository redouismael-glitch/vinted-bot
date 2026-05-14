"""
analytics/scoring.py
Système de scoring avancé (0–100) basé sur :
- marge brute estimée
- ratio marge/prix (rentabilité relative)
- hype factor (marque premium vs marque commune)
- bonus mots-clés rares
- pénalités (état, prix anormal)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..config.settings import BRAND_RULES, KEYWORDS_HYPE

logger = logging.getLogger(__name__)

# Hype tier : plus la marque est rare, plus le bonus est élevé
HYPE_TIER: dict[str, int] = {
    # Tier S — hype maximum
    "chrome hearts": 30, "hellstar": 28, "gallery dept": 25,
    "rick owens": 25, "denim tears": 22, "off-white": 22,
    "corteiz": 22, "crtz": 22, "trapstar": 20, "syna world": 20,
    "broken planet": 18, "minus two": 18, "represent": 18,
    "supreme": 25, "palace": 22,
    # Tier A
    "jordan": 15, "air jordan": 15, "stone island": 15,
    "moncler": 15, "balenciaga": 15, "arc'teryx": 15,
    "canada goose": 12, "fear of god": 15, "essentials": 12,
    # Tier B
    "nike": 8, "adidas": 8, "new balance": 8, "north face": 8,
    "napapijri": 8, "ralph lauren": 7, "lacoste": 6,
    # Tier C
    "zara": 2, "h&m": 1, "uniqlo": 2,
}

# Bonus mots-clés rares dans le titre
HYPE_KEYWORDS_BONUS: dict[str, int] = {
    "deadstock": 15, "ds": 12, "vnds": 10, "rare": 8,
    "limited": 8, "collab": 10, "og": 8, "fragment": 12,
    "travis scott": 15, "sacai": 12, "vintage": 5,
}

# Mapping état Vinted → malus score
CONDITION_PENALTY: dict[str, int] = {
    "new_with_tags": 0,
    "new_without_tags": 0,
    "very_good": -2,
    "good": -8,
    "satisfactory": -15,
    # valeur inconnue → malus modéré
    "_unknown": -5,
}


@dataclass
class DealScore:
    score: int                       # 0–100
    marge_nette: float               # €
    prix_revente_estime: float       # €
    label: str                       # emoji + texte
    details: dict                    # breakdown pour debug


def compute_score(
    prix: float,
    brand_key: str,
    titre: str,
    condition_key: Optional[str] = None,
) -> DealScore:
    """
    Calcule un score de deal de 0 à 100.
    """
    titre_low = titre.lower()
    coef, marge_min = BRAND_RULES.get(brand_key, BRAND_RULES["_default"])

    # ── Calcul financier ─────────────────────────────────────────────────────
    prix_revente = round(prix * coef, 2)
    frais_plateforme = round(prix_revente * 0.10, 2)   # ~10% Vinted/Depop
    marge_nette = round(prix_revente - frais_plateforme - prix, 2)

    details: dict = {
        "prix_achat": prix,
        "prix_revente": prix_revente,
        "frais": frais_plateforme,
        "marge_nette": marge_nette,
        "coef": coef,
        "marge_min": marge_min,
    }

    # ── Score de base : ratio marge/prix (0–40 pts) ──────────────────────────
    if prix > 0:
        ratio = marge_nette / prix
    else:
        ratio = 0.0

    base_score = min(40, int(ratio * 80))
    details["base_score"] = base_score

    # ── Bonus hype marque (0–30 pts) ─────────────────────────────────────────
    hype_bonus = HYPE_TIER.get(brand_key, 3)
    details["hype_bonus"] = hype_bonus

    # ── Bonus mots-clés rares (0–15 pts) ─────────────────────────────────────
    kw_bonus = 0
    matched_kw: list[str] = []
    for kw, pts in HYPE_KEYWORDS_BONUS.items():
        if kw in titre_low:
            kw_bonus = max(kw_bonus, pts)   # on prend le meilleur, pas la somme
            matched_kw.append(kw)
    kw_bonus = min(kw_bonus, 15)
    details["kw_bonus"] = kw_bonus
    details["matched_keywords"] = matched_kw

    # ── Pénalité état ─────────────────────────────────────────────────────────
    condition_key = condition_key or "_unknown"
    cond_penalty = CONDITION_PENALTY.get(condition_key, CONDITION_PENALTY["_unknown"])
    details["condition_penalty"] = cond_penalty

    # ── Pénalité marge insuffisante ───────────────────────────────────────────
    marge_penalty = 0
    if marge_nette < marge_min:
        marge_penalty = -20
    details["marge_penalty"] = marge_penalty

    # ── Score final ───────────────────────────────────────────────────────────
    score = max(0, min(100, base_score + hype_bonus + kw_bonus + cond_penalty + marge_penalty))
    details["score_final"] = score

    # ── Label ─────────────────────────────────────────────────────────────────
    if score >= 75:
        label = "💎 Deal exceptionnel"
    elif score >= 60:
        label = "🔥🔥🔥 Excellente affaire"
    elif score >= 45:
        label = "🔥🔥 Très bonne affaire"
    elif score >= 30:
        label = "🔥 Bonne affaire"
    else:
        label = "👍 Affaire correcte"

    return DealScore(
        score=score,
        marge_nette=marge_nette,
        prix_revente_estime=prix_revente,
        label=label,
        details=details,
    )
