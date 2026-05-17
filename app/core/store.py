"""Fero Eğitim — State store.

Panel mantığı:
  - Bir coin günlük %20+ yükseldiğinde kalıcı panele girer.
  - Düşse bile panelde kalır.
  - Kalıcı panel ve raporlar JSON dosyasına yazılır; uygulama restart olunca silinmez.
  - Her gün tarih değişiminde daily_stats sıfırlanır ve günlük rapor kaydedilir.
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.config import egitim_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EgitimStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()

        # ── Kalıcı panel ────────────────────────────────────────────────────
        # symbol → dict bilgisi
        self.permanent_coins: dict[str, dict[str, Any]] = {}

        # ── Günlük takip ────────────────────────────────────────────────────
        # Bugün ilk kez %20+ olan coinler
        self.today_coins: dict[str, dict[str, Any]] = {}
        self._today_date: date = date.today()

        # ── Günlük raporlar ─────────────────────────────────────────────────
        self.daily_reports: deque[dict[str, Any]] = deque(
            maxlen=egitim_settings.max_daily_reports
        )

        # ── Sistem bilgisi ──────────────────────────────────────────────────
        self.last_heartbeat: float = 0.0
        self.total_pairs: int = 0
        self.last_error: str | None = None
        self.last_poll_ts: float = 0.0
        self.last_poll_count: int = 0

        self._load_from_disk()

    # ── Disk kayıt yardımcıları ─────────────────────────────────────────────

    @property
    def _store_path(self) -> Path:
        return Path(egitim_settings.store_file)

    def _load_from_disk(self) -> None:
        """Uygulama açılırken kalıcı paneli ve raporları geri yükle."""
        path = self._store_path
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.permanent_coins = dict(data.get("permanent_coins") or {})
            self.today_coins = dict(data.get("today_coins") or {})

            raw_today = data.get("today_date")
            if raw_today:
                self._today_date = date.fromisoformat(raw_today)

            reports = data.get("daily_reports") or []
            self.daily_reports = deque(reports, maxlen=egitim_settings.max_daily_reports)
            logger.info(
                "Store yüklendi — panel: %d, bugün: %d, rapor: %d",
                len(self.permanent_coins),
                len(self.today_coins),
                len(self.daily_reports),
            )
        except Exception as exc:
            logger.warning("Store okunamadı, boş state ile devam: %s", exc)

    def _save_to_disk_locked(self) -> None:
        """State'i JSON dosyasına atomik olarak yaz. Bu fonksiyon lock içinde çağrılır."""
        path = self._store_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "today_date": self._today_date.isoformat(),
                "permanent_coins": self.permanent_coins,
                "today_coins": self.today_coins,
                "daily_reports": list(self.daily_reports),
            }
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception as exc:
            logger.warning("Store yazılamadı: %s", exc)

    # ── İç yardımcılar ──────────────────────────────────────────────────────

    def _check_day_rollover(self) -> None:
        """Gece yarısı geçtiyse günlük raporu kaydet, today_coins'i sıfırla."""
        today = date.today()
        if today == self._today_date:
            return

        # Dünün raporunu oluştur
        self._save_daily_report(self._today_date)

        # Sıfırla
        self.today_coins = {}
        self._today_date = today
        self._save_to_disk_locked()
        logger.info("Günlük sıfırlama tamamlandı — yeni gün: %s", today)

    def _save_daily_report(self, report_date: date) -> None:
        coins = list(self.today_coins.values())
        sorted_coins = sorted(coins, key=lambda c: c["max_pct"], reverse=True)
        report = {
            "date": report_date.isoformat(),
            "count": len(sorted_coins),
            "threshold_pct": egitim_settings.rise_threshold_pct,
            "top": sorted_coins[:20],
            "all_symbols": [c["symbol"] for c in sorted_coins],
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.daily_reports.appendleft(report)

        if sorted_coins:
            logger.info(
                "📋 Günlük rapor [%s]: %d coin %%%.0f eşiğini aştı. En yüksek: %s (%%%.2f)",
                report_date,
                len(sorted_coins),
                egitim_settings.rise_threshold_pct,
                sorted_coins[0]["symbol"],
                sorted_coins[0]["max_pct"],
            )
        else:
            logger.info(
                "📋 Günlük rapor [%s]: 0 coin %%%.0f eşiğini aştı.",
                report_date,
                egitim_settings.rise_threshold_pct,
            )

    # ── Engine tarafından çağrılır ──────────────────────────────────────────

    def mark_heartbeat(self, total_pairs: int) -> None:
        with self.lock:
            self._check_day_rollover()
            self.last_heartbeat = time.time()
            self.total_pairs = total_pairs
            self.last_error = None

    def mark_error(self, message: str) -> None:
        with self.lock:
            self.last_error = message

    def process_ticker(self, symbol: str, pct: float, price: float, ts: float) -> bool:
        """
        Bir coinin %20+ yükseldiğini işle.
        Kalıcı panele yeni ekleme yapıldıysa True döner.
        """
        with self.lock:
            self._check_day_rollover()
            now_str = datetime.fromtimestamp(ts).strftime("%H:%M")
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

            is_new_to_panel = symbol not in self.permanent_coins
            is_new_today = symbol not in self.today_coins
            changed = False

            # Kalıcı panel: ilk kez ekle; sonradan daha yüksek % görürse max_pct güncelle
            if is_new_to_panel:
                self.permanent_coins[symbol] = {
                    "symbol": symbol,
                    "first_pct": round(pct, 2),
                    "max_pct": round(pct, 2),
                    "price_entry": price,
                    "price_now": price,
                    "first_seen": now_str,
                    "first_date": date_str,
                    "added_ts": ts,
                }
                changed = True
            else:
                entry = self.permanent_coins[symbol]
                if pct > entry.get("max_pct", 0):
                    entry["max_pct"] = round(pct, 2)
                    changed = True
                if entry.get("price_now") != price:
                    entry["price_now"] = price
                    changed = True

            # Bugünkü takip
            if is_new_today:
                self.today_coins[symbol] = {
                    "symbol": symbol,
                    "max_pct": round(pct, 2),
                    "price_entry": price,
                    "price_now": price,
                    "first_seen": now_str,
                    "added_ts": ts,
                }
                changed = True
            else:
                tc = self.today_coins[symbol]
                if pct > tc.get("max_pct", 0):
                    tc["max_pct"] = round(pct, 2)
                    changed = True
                if tc.get("price_now") != price:
                    tc["price_now"] = price
                    changed = True

            if changed:
                self._save_to_disk_locked()

            return is_new_to_panel

    def set_poll_result(self, count: int, ts: float) -> None:
        with self.lock:
            self.last_poll_ts = ts
            self.last_poll_count = count

    # ── API endpoint'leri için ──────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        now = time.time()
        with self.lock:
            self._check_day_rollover()
            panel = sorted(
                self.permanent_coins.values(),
                key=lambda c: c.get("added_ts", 0),
                reverse=True,
            )
            today_sorted = sorted(
                self.today_coins.values(),
                key=lambda c: c.get("max_pct", 0),
                reverse=True,
            )
            return {
                "live": (now - self.last_heartbeat) < 120,
                "total_pairs": self.total_pairs,
                "threshold_pct": egitim_settings.rise_threshold_pct,
                "panel_count": len(self.permanent_coins),
                "today_count": len(self.today_coins),
                "panel": panel,
                "today_top": today_sorted[:50],
                "last_poll_ts": self.last_poll_ts,
                "last_poll_count": self.last_poll_count,
                "last_error": self.last_error,
                "current_date": self._today_date.isoformat(),
            }

    def reports_status(self) -> dict[str, Any]:
        with self.lock:
            self._check_day_rollover()
            return {
                "reports": list(self.daily_reports),
                "total": len(self.daily_reports),
            }

    def generate_today_report(self) -> dict[str, Any]:
        """Manuel tetikleme için anlık bugün raporu."""
        with self.lock:
            self._check_day_rollover()
            coins = sorted(
                self.today_coins.values(),
                key=lambda c: c.get("max_pct", 0),
                reverse=True,
            )
            return {
                "date": self._today_date.isoformat(),
                "count": len(coins),
                "threshold_pct": egitim_settings.rise_threshold_pct,
                "top": coins[:50],
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "is_live": True,
            }


egitim_store = EgitimStore()
