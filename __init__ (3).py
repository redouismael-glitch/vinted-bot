"""
analytics/stats.py
Statistiques live du bot, accumulées en mémoire.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class BotStats:
    start_time: float = field(default_factory=time.monotonic)
    scans_total: int = 0
    items_fetched: int = 0
    items_filtered: int = 0
    items_analyzed: int = 0
    alerts_sent: int = 0
    errors: int = 0
    last_scan_ts: float = 0.0
    last_scan_duration_sec: float = 0.0

    def uptime_str(self) -> str:
        secs = int(time.monotonic() - self.start_time)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h{m:02d}m{s:02d}s"

    def last_scan_str(self) -> str:
        if not self.last_scan_ts:
            return "jamais"
        elapsed = int(time.monotonic() - self.last_scan_ts)
        if elapsed < 60:
            return f"il y a {elapsed}s"
        return f"il y a {elapsed // 60}min"

    def summary(self) -> str:
        return (
            f"⏱️ Uptime : {self.uptime_str()}\n"
            f"🔍 Scans : {self.scans_total}\n"
            f"📦 Articles récupérés : {self.items_fetched}\n"
            f"🚫 Filtrés : {self.items_filtered}\n"
            f"🔥 Alertes envoyées : {self.alerts_sent}\n"
            f"❌ Erreurs : {self.errors}\n"
            f"🕐 Dernier scan : {self.last_scan_str()}"
        )
