#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "Fero Eğitim başlatılıyor..."
export ENABLE_COLLECTORS=${ENABLE_COLLECTORS:-true}
export EGITIM_RISE_THRESHOLD_PCT=${EGITIM_RISE_THRESHOLD_PCT:-20.0}
export EGITIM_POLL_SECONDS=${EGITIM_POLL_SECONDS:-60}
export EGITIM_STORE_FILE=${EGITIM_STORE_FILE:-data/egitim_store.json}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-6969}" --reload
