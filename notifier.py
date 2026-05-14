"""
filters/item_filter.py
Pipeline de filtres pur Python, sans IA.
Chaque filtre est une fonction indépendante → facile à tester / étendre.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..config.settings import (
    Config, KEYWORDS_HYPE, KEYWORDS_EXCLUDED,
)

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    passed: bool
    reason: str = ""


def _extract_price(item: dict) -> Optional[float]:
    try:
        raw = item.get("price", {})
        if isinstance(raw, dict):
            return float(raw.get("amount", 0))
        return float(raw)
    except (TypeError, ValueError):
        return None


def _detect_brand(titre: str, marque_vinted: str, active_brands: set[str]) -> Optional[str]:
    t = titre.lower()
    m = marque_vinted.lower().strip()
    for brand in active_brands:
        if brand in m or brand in t:
            return brand
    return None


def filter_price(item: dict, config: Config) -> FilterResult:
    prix = _extract_price(item)
    if prix is None:
        return FilterResult(False, "prix introuvable")
    if prix < config.prix_min:
        return FilterResult(False, f"prix trop bas ({prix}€ < {config.prix_min}€)")
    if prix > config.prix_max:
        return FilterResult(False, f"prix trop élevé ({prix}€ > {config.prix_max}€)")
    return FilterResult(True)


def filter_keywords(item: dict) -> FilterResult:
    t = (item.get("title", "") or "").lower()
    for kw in KEYWORDS_EXCLUDED:
        if kw in t:
            return FilterResult(False, f"mot-clé exclu: '{kw}'")
    return FilterResult(True)


def filter_brand(item: dict, config: Config) -> tuple[FilterResult, str]:
    """Retourne (FilterResult, brand_key)."""
    titre = item.get("title", "") or ""
    marque_raw = item.get("brand_title", "") or ""
    t = titre.lower()

    brand = _detect_brand(titre, marque_raw, config.marques)
    if brand:
        return FilterResult(True), brand

    # Fallback : mot-clé hype dans le titre
    if any(k in t for k in KEYWORDS_HYPE):
        return FilterResult(True), "_default"

    return FilterResult(False, "marque non cible et pas de mot-clé hype"), ""


def apply_all(item: dict, config: Config) -> tuple[bool, str, str]:
    """
    Applique tous les filtres séquentiellement.
    Retourne (passed, reject_reason, brand_key).
    """
    # 1. Prix
    r = filter_price(item, config)
    if not r.passed:
        return False, r.reason, ""

    # 2. Mots-clés exclus
    r = filter_keywords(item)
    if not r.passed:
        return False, r.reason, ""

    # 3. Marque
    r, brand = filter_brand(item, config)
    if not r.passed:
        return False, r.reason, ""

    return True, "", brand
