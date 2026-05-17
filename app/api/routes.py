from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.store import egitim_store

router = APIRouter()


@router.get("/api/egitim")
def get_egitim():
    """Ana panel + bugünkü özet."""
    return egitim_store.status()


@router.get("/api/reports")
def get_reports():
    """Geçmiş günlük raporlar."""
    return egitim_store.reports_status()


@router.get("/api/today")
def get_today():
    """Bugünün anlık raporu."""
    return egitim_store.generate_today_report()


@router.get("/health")
def health():
    s = egitim_store.status()
    return {
        "ok":          s["live"],
        "panel_count": s["panel_count"],
        "today_count": s["today_count"],
        "threshold":   s["threshold_pct"],
    }
