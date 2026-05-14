"""
config/settings.py
Centralise toute la configuration du bot.
Persistée en JSON, rechargeable sans redémarrage.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "config.json"))


@dataclass
class Config:
    # ── Scan ─────────────────────────────────────────────────────────────────
    actif: bool = False
    cooldown_sec: int = 900          # 15 min par défaut
    prix_min: float = 3.0
    prix_max: float = 200.0
    score_min: int = 30              # score deal minimum (0-100) pour alerter

    # ── Marques actives ───────────────────────────────────────────────────────
    marques: Set[str] = field(default_factory=set)

    # ── Mode opératoire ───────────────────────────────────────────────────────
    # "safe"   → cooldown long, score élevé, peu d'alertes
    # "normal" → paramètres par défaut
    # "pro"    → cooldown court, score bas, toutes les opportunités
    mode: str = "normal"

    # ── Rate limiting Telegram ────────────────────────────────────────────────
    telegram_min_interval_sec: float = 0.5   # délai min entre 2 messages

    # ── Cache seen_ids ────────────────────────────────────────────────────────
    seen_ids_max: int = 50_000   # limite mémoire seen_ids

    def save(self) -> None:
        try:
            data = asdict(self)
            data["marques"] = list(self.marques)
            CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            logger.debug("Config sauvegardée → %s", CONFIG_PATH)
        except Exception as e:
            logger.error("Erreur sauvegarde config : %s", e)

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            logger.info("Pas de config.json, utilisation des valeurs par défaut.")
            cfg = cls()
            cfg.marques = set(DEFAULT_MARQUES)
            cfg.save()
            return cfg
        try:
            data = json.loads(CONFIG_PATH.read_text())
            data["marques"] = set(data.get("marques", DEFAULT_MARQUES))
            cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            logger.info("Config chargée depuis %s", CONFIG_PATH)
            return cfg
        except Exception as e:
            logger.warning("Config corrompue (%s), reset par défaut.", e)
            cfg = cls()
            cfg.marques = set(DEFAULT_MARQUES)
            return cfg

    def apply_mode(self, mode: str) -> None:
        """Applique un preset de mode."""
        mode = mode.lower()
        if mode == "safe":
            self.cooldown_sec = 1800
            self.score_min = 60
        elif mode == "pro":
            self.cooldown_sec = 300
            self.score_min = 20
        elif mode == "ultra":
            self.cooldown_sec = 120
            self.score_min = 15
        else:  # normal
            self.cooldown_sec = 900
            self.score_min = 30
        self.mode = mode
        self.save()


# ── Données statiques ─────────────────────────────────────────────────────────

DEFAULT_MARQUES: list[str] = [
    # Hype / Streetwear
    "chrome hearts", "hellstar", "denim tears", "gallery dept", "gallery dept.",
    "rick owens", "drkshdw", "broken planet", "minus two", "no faith studios",
    "corteiz", "crtz", "syna world", "trapstar", "vicinity", "represent",
    "fear of god", "essentials", "off-white", "palm angels", "misbhv",
    "a-cold-wall", "a cold wall", "vivienne westwood",
    # Sportswear premium
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
]

SEARCH_QUERIES: list[str] = [
    "nike", "adidas", "jordan", "new balance", "stone island",
    "lacoste", "ralph lauren", "tommy hilfiger", "supreme", "palace",
    "corteiz", "north face", "carhartt", "stussy", "yeezy",
    "arc'teryx", "moncler", "cp company", "napapijri", "hellstar",
    "chrome hearts", "rick owens", "broken planet", "trapstar",
    "represent", "fear of god", "off-white", "palm angels",
    "gallery dept", "vivienne westwood", "syna world", "minus two",
]

# Coefficients de revente et marge min par marque (coef, marge_min_€)
BRAND_RULES: dict[str, tuple[float, int]] = {
    "chrome hearts":     (2.5, 30), "hellstar":          (2.5, 25),
    "gallery dept":      (2.3, 25), "gallery dept.":     (2.3, 25),
    "rick owens":        (2.2, 25), "drkshdw":           (2.2, 25),
    "denim tears":       (2.2, 20), "broken planet":     (2.0, 20),
    "minus two":         (2.0, 20), "trapstar":          (2.0, 20),
    "represent":         (1.9, 18), "fear of god":       (1.9, 20),
    "essentials":        (1.8, 15), "off-white":         (2.0, 25),
    "palm angels":       (1.9, 20), "misbhv":            (1.8, 15),
    "a-cold-wall":       (1.8, 15), "vivienne westwood": (1.9, 20),
    "corteiz":           (2.2, 20), "crtz":              (2.2, 20),
    "syna world":        (2.0, 18), "vicinity":          (1.9, 15),
    "no faith studios":  (2.0, 15), "supreme":           (2.5, 20),
    "palace":            (2.2, 20), "jordan":            (1.8, 15),
    "air jordan":        (1.8, 15), "stone island":      (1.7, 15),
    "cp company":        (1.7, 15), "c.p. company":      (1.7, 15),
    "balenciaga":        (1.7, 20), "arc'teryx":         (1.7, 20),
    "arcteryx":          (1.7, 20), "moncler":           (1.7, 25),
    "canada goose":      (1.6, 20), "north face":        (1.5, 10),
    "the north face":    (1.5, 10), "napapijri":         (1.5, 10),
    "nike":              (1.5, 10), "adidas":            (1.5, 10),
    "new balance":       (1.5, 10), "ralph lauren":      (1.5, 10),
    "jacquemus":         (1.6, 12), "ami paris":         (1.5, 12),
    "sandro":            (1.5, 10), "maje":              (1.4,  8),
    "lacoste":           (1.4,  8), "tommy hilfiger":    (1.4,  8),
    "carhartt":          (1.4,  8), "levi's":            (1.3,  8),
    "levis":             (1.3,  8), "diesel":            (1.4,  8),
    "calvin klein":      (1.3,  6), "birkenstock":       (1.4,  8),
    "asics":             (1.4,  8), "zara":              (1.3,  5),
    "uniqlo":            (1.3,  5), "_default":          (1.4,  8),
}

KEYWORDS_HYPE: frozenset[str] = frozenset({
    "vintage", "deadstock", "ds", "vnds", "rare", "limited", "collab",
    "og", "retro", "dunk", "air max", "air force", "jordan 1", "jordan 4",
    "jordan 11", "350", "990", "2002r", "550", "travis", "sacai", "fragment",
})

KEYWORDS_EXCLUDED: frozenset[str] = frozenset({
    "lot de", "pack", "déguisement", "costume", "bébé", "enfant",
    "fille", "garçon", "chaussettes", "sous-vêtement",
})
