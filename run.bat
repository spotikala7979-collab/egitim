@echo off
REM Always run from this file's folder so Python can import app.main
cd /d "%~dp0"

echo Fero Egitim baslatiliyor (port 6969)...
echo Proje klasoru: %CD%

set ENABLE_COLLECTORS=true
set EGITIM_RISE_THRESHOLD_PCT=20.0
set EGITIM_POLL_SECONDS=60
set LOG_LEVEL=INFO
set PYTHONPATH=%CD%

python -m uvicorn app.main:app --host 0.0.0.0 --port 6969 --reload

if errorlevel 1 (
    echo.
    echo Bot baslatilirken hata olustu. Yukaridaki hata mesajini kontrol et.
    pause
)
