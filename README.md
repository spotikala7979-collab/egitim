# 🎓 Fero Eğitim — Railway Build

Bu paket Railway üzerinde VPS kullanmadan tek servis olarak çalışacak şekilde düzenlendi.

## Ne yapar?

Binance 24 saatlik ticker verisini takip eder ve günlük yükselişi belirlenen eşiği geçen coinleri panele ekler.

Varsayılan eşik: `%20`

## Railway'e yükleme

1. Bu klasörü GitHub'a yükle.
2. Railway'de **New Project → Deploy from GitHub repo** seç.
3. Repo'yu seç ve deploy et.
4. Railway otomatik olarak `Dockerfile` ile build alır.
5. Deploy bitince Railway'in verdiği public domain üzerinden aç.

Dockerfile Railway'in verdiği `$PORT` değerini otomatik kullanır. Bu yüzden manuel port ayarı gerekmiyor.

## Railway Variables

Normalde ekstra ayar gerekmez. İstersen Railway → Variables bölümünde şunları kullanabilirsin:

```env
APP_NAME=Fero Eğitim
ENABLE_COLLECTORS=true
EGITIM_RISE_THRESHOLD_PCT=20.0
EGITIM_POLL_SECONDS=60
EGITIM_STORE_FILE=/app/data/egitim_store.json
LOG_LEVEL=INFO
```

## Kalıcı kayıt notu

Panel verisi varsayılan olarak `/app/data/egitim_store.json` dosyasına yazılır.

Railway'de servis yeniden deploy olunca dosya sistemi sıfırlanabilir. Panel geçmişinin kesin kalıcı olmasını istiyorsan Railway tarafında bir Volume oluşturup `/app/data` yoluna bağla.

Volume bağlamazsan uygulama yine çalışır, ama deploy/restart sonrası eski panel kayıtları kaybolabilir.

## Lokal çalıştırma

Python 3.12 önerilir.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Aç:

```text
http://localhost:6969
http://localhost:6969/health
```

## Docker lokal test

```bash
docker build -t fero-egitim .
docker run --rm -p 8000:8000 -e PORT=8000 fero-egitim
```

Aç:

```text
http://localhost:8000
```

## Önemli not

Railway bölgesinden Binance API'ye erişim engellenirse uygulama açılır ama veri gelmez. Böyle olursa `/health` endpoint'inde sistem offline görünebilir. Bu durumda Railway servisinde farklı region/location denemek gerekir.
