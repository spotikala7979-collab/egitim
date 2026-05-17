"""Fero Eğitim — Ana Engine.

Her EGITIM_POLL_SECONDS saniyede bir Binance Futures 24hr ticker'ı çeker.
priceChangePercent >= EGITIM_RISE_THRESHOLD_PCT olan coinleri kalıcı panele ekler.
"""
from __future__ import annotations

import asyncio
import sys
import threading
import time
from typing import Any

import httpx

from app.core.config import EgitimSettings, egitim_settings
from app.core.logging import get_logger
from app.core.store import EgitimStore, egitim_store

FUTURES_TICKER_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
SPOT_TICKER_URL    = "https://api.binance.com/api/v3/ticker/24hr"

logger = get_logger(__name__)


class EgitimEngine:
    def __init__(self, store: EgitimStore, settings: EgitimSettings) -> None:
        self.store    = store
        self.settings = settings
        self._started     = False
        self._stop_event  = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock        = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_in_thread,
                name="egitim-engine",
                daemon=True,
            )
            self._thread.start()
            logger.info("EgitimEngine başlatıldı — eşik: %%%.0f, polling: %ds",
                        self.settings.rise_threshold_pct, self.settings.poll_seconds)

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            if not self._started:
                return
            self._stop_event.set()
            thread = self._thread
            self._started = False
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        logger.info("EgitimEngine durduruldu")

    def _run_in_thread(self) -> None:
        if sys.platform == "win32":
            loop = asyncio.SelectorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run())
        finally:
            loop.close()

    async def run(self) -> None:
        logger.info("EgitimEngine polling başlıyor…")
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "FeroEgitimBot/1.0"}) as client:
            while not self._stop_event.is_set():
                await self._poll(client)
                await self._sleep(self.settings.poll_seconds)

    async def _poll(self, client: httpx.AsyncClient) -> None:
        """Binance ticker'ı çek, %%20+ coinleri işle."""
        try:
            # Önce Futures, hata olursa Spot'a geç
            try:
                resp = await client.get(FUTURES_TICKER_URL)
                resp.raise_for_status()
            except Exception:
                resp = await client.get(SPOT_TICKER_URL)
                resp.raise_for_status()

            payload: list[dict[str, Any]] = resp.json()
            if not isinstance(payload, list):
                self.store.mark_error("Beklenmeyen Binance yanıtı")
                return

            now = time.time()
            self.store.mark_heartbeat(total_pairs=len(payload))

            threshold = self.settings.rise_threshold_pct
            new_this_poll = 0

            for item in payload:
                symbol = str(item.get("symbol", ""))
                if not symbol.endswith("USDT"):
                    continue
                try:
                    pct   = float(item["priceChangePercent"])
                    price = float(item["lastPrice"])
                except (KeyError, TypeError, ValueError):
                    continue

                if pct >= threshold:
                    added = self.store.process_ticker(
                        symbol=symbol.replace("USDT", ""),
                        pct=pct,
                        price=price,
                        ts=now,
                    )
                    if added:
                        new_this_poll += 1
                        logger.info("🚀 YENİ: %s | %%+%.2f | $%.4f", symbol, pct, price)

            self.store.set_poll_result(count=new_this_poll, ts=now)
            logger.debug(
                "Poll tamamlandı — %d pair tarandı, %d yeni %%%.0f+ coin",
                len(payload), new_this_poll, threshold,
            )

        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            self.store.mark_error(msg)
            logger.warning("Polling hatası: %s", msg)

    async def _sleep(self, seconds: float) -> None:
        end = time.time() + seconds
        while not self._stop_event.is_set() and time.time() < end:
            await asyncio.sleep(min(1.0, max(0.0, end - time.time())))


egitim_engine = EgitimEngine(egitim_store, egitim_settings)
