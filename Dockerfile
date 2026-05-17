FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_NAME="Fero Eğitim" \
    ENABLE_COLLECTORS=true \
    EGITIM_RISE_THRESHOLD_PCT=20.0 \
    EGITIM_POLL_SECONDS=60 \
    EGITIM_STORE_FILE=/app/data/egitim_store.json \
    LOG_LEVEL=INFO

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
