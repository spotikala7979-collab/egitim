"""Fero Eğitim — uygulama ayarları."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def _get_env(name: str, default: T, cast: Callable[[str], T]) -> T:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except Exception:
        return default


def _get_bool(name: str, default: bool) -> bool:
    return _get_env(name, default, lambda v: v.strip().lower() in {"1", "true", "yes", "on"})


def _get_float(name: str, default: float) -> float:
    return _get_env(name, default, float)


def _get_int(name: str, default: int) -> int:
    return _get_env(name, default, int)


class AppSettings(BaseModel):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "Fero Eğitim"))
    debug: bool = Field(default_factory=lambda: _get_bool("APP_DEBUG", False))
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    enable_collectors: bool = Field(default_factory=lambda: _get_bool("ENABLE_COLLECTORS", True))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: _get_int("PORT", 6969))


class EgitimSettings(BaseModel):
    # %20 eşiği — bu seviyeye ulaşan coin kalıcı panele girer
    rise_threshold_pct: float = Field(
        default_factory=lambda: _get_float("EGITIM_RISE_THRESHOLD_PCT", 20.0)
    )
    # Binance Futures 24hr ticker polling süresi (saniye)
    poll_seconds: float = Field(
        default_factory=lambda: _get_float("EGITIM_POLL_SECONDS", 60.0)
    )
    # Sadece USDT pair'ler
    quote_asset: str = "USDT"
    # Günlük rapor kaç tane tutulsun
    max_daily_reports: int = Field(
        default_factory=lambda: _get_int("EGITIM_MAX_DAILY_REPORTS", 30)
    )
    # Panel/raporların restart sonrası silinmemesi için dosya bazlı kayıt
    store_file: str = Field(
        default_factory=lambda: os.getenv("EGITIM_STORE_FILE", "data/egitim_store.json")
    )


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def get_egitim_settings() -> EgitimSettings:
    return EgitimSettings()


app_settings = get_app_settings()
egitim_settings = get_egitim_settings()
