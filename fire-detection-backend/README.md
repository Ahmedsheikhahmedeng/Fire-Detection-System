# Fire Detection Backend

Bu proje, NASA FIRMS sicak nokta verilerini kullanarak orman yangini riskini tahmin eden yapay zeka destekli bir backend sistemidir.

Sistem; uydu verisi, hava durumu ozellikleri ve makine ogrenmesi modeli kullanarak her sicak nokta icin yangin olasiligi uretir. Yuksek riskli durumlarda alarm kaydi olusturur ve harita uzerinde gosterilmek uzere API endpointleri saglar.

---

## Projenin Amaci

Bu backend sisteminin amaci, NASA FIRMS uzerinden gelen sicak nokta verilerini analiz ederek gercek yangin riski tasiyan bolgeleri tespit etmektir.

Sistem su soruya cevap verir:

> Gelen bir FIRMS hotspot gercekten yangin riski tasiyor mu?

---

## Kullanilan Teknolojiler

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- NASA FIRMS API
- Open-Meteo Weather API
- Scikit-learn
- XGBoost
- LightGBM
- CatBoost
- RandomForest
- ExtraTrees
- Pytest

---

## Genel Sistem Akisi

1. NASA FIRMS uzerinden hotspot verileri alinir.
2. Hotspot verileri veritabanina kaydedilir.
3. Her hotspot icin hava durumu ozellikleri hazirlanir.
4. V3 makine ogrenmesi modeli calistirilir.
5. Her hotspot icin yangin olasiligi hesaplanir.
6. Risk seviyesi belirlenir.
7. Yuksek riskli kayitlar icin alert olusturulur.
8. Harita ve frontend icin API uzerinden veri sunulur.

---

## Coklu Uydu Kaynagi ve Yangin Kumesi Sistemi

Sistem NASA FIRMS uzerinden uc VIIRS kaynagini kullanir:

- `VIIRS_SNPP_NRT`
- `VIIRS_NOAA20_NRT`
- `VIIRS_NOAA21_NRT`

`MODIS_NRT` bilincli olarak eklenmemistir. MODIS farkli cozunurluk ve farkli kolon yapisina sahip oldugu icin mevcut VIIRS tabanli ML feature yapisini karistirabilir. NOAA20 ve NOAA21 de VIIRS ailesinde kaldigi icin model input kolonlari korunur.

Hotspotlar yangin kumesi mantigiyla gruplanir. Baslangic kuralina gore 5 km icinde ve 6 saatlik zaman penceresinde kalan hotspotlar ayni `fire_cluster` kaydina baglanir. Bu sayede ayni yangin bolgesi icin tekrar eden alert uretimi azaltilir.

Cluster status kurallari:

- 0-24 saat: `active`
- 24-72 saat: `monitoring`
- 72+ saat: `resolved`

Kaynak, cluster ve sistem sagligi icin kullanilan ana endpointler:

- `GET /api/hotspots/source-stats`
- `GET /api/hotspots/clusters`
- `GET /api/hotspots/clusters?status=all&limit=3`
- `GET /api/system/health`

Sistem saglik paneli son NASA fetch sonucunu, kaynak bazli veri durumunu, cluster sayilarini, prediction limitini ve weather fallback sayaclarini gosterir.

---

## Backend Modulleri

### app/main.py

FastAPI uygulamasinin baslangic dosyasidir. API routerlari burada baglanir ve uygulama baslatilir.

### app/api/

API endpoint dosyalarini icerir.

Ornek endpoint gruplari:

- NASA veri cekme
- Hotspot listeleme
- Harita verileri
- ML tahminleri
- Alert islemleri

### app/services/

Is mantiginin bulundugu klasordur.

Ornek servisler:

- NASA service
- Weather service
- ML service
- Scheduler service
- Alert service

### app/models/

Veritabani modellerini icerir.

### app/schemas/

Request ve response semalarini icerir.

### tests/

Backend testlerini icerir.

---

## Test Durumu

Mevcut resmi test sonucu:

```bash
141 passed
```

Bu sonuc `tests/` altindaki resmi pytest suite'inin basariyla calistigini gosterir.

---

## Development / Test Dependencies

Test ve gelistirme bagimliliklarini kurmak icin:

```bash
pip install -r requirements-dev.txt
```

Testleri calistirmak icin `TEST_DATABASE_URL` tanimli olmalidir. Guvenlik nedeniyle database adinda `test` kelimesi gecmelidir.

```bash
export TEST_DATABASE_URL="postgresql://fire_user:replace_with_test_database_password@localhost:5432/fire_detection_test"
pytest
```

Not: Eski manuel dogrulama scriptleri `scripts/legacy_checks/` altindadir ve pytest suite'ine dahil degildir. Resmi otomatik testler `tests/` klasoru altindadir.

---

## Calistirma

Once gerekli paketleri yukleyin:

```bash
pip install -r requirements.txt
```

Backend'i calistirin:

```bash
uvicorn app.main:app --reload
```

Gercek secret degerleri repo icine yazilmaz. Local calisma icin `.env.example` dosyasini `.env` olarak kopyalayip `API_KEY`, `DB_PASSWORD`, `NASA_API_KEY` ve `OPENWEATHER_API_KEY` degerlerini kendi ortaminda doldurun. Docker Compose bu degerleri environment uzerinden okur.

```bash
cp .env.example .env
# .env icindeki secret degerlerini doldurun
```

Docker Compose ile backend, frontend ve Postgres'i birlikte calistirmak icin:

```bash
docker compose -p fire-dev up -d --build
```

Varsayilan adresler:

- Frontend: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`

Production Docker Compose ile calistirmak icin:

```bash
cp .env.production.example .env.production
# .env.production icindeki secret ve domain degerlerini doldurun
docker compose -p fire-prod --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Production compose `--reload` kullanmaz, backend kodunu volume olarak mount etmez ve uygulama baslamadan once `alembic upgrade head` calistirir. Web backend servisinde scheduler kapali tutulur; NASA/Weather/ML dongusu ayri `scheduler` worker servisinde calisir. Bu worker tek kopya calismalidir.

Production backend container root kullanicisiyle calismaz. Backend ve frontend servislerinde healthcheck vardir; frontend ve scheduler backend'in healthy olmasini bekler. Backend ve scheduler baslamadan once model artifact paketi `scripts/check_model_artifacts.py` ile dogrulanir.

Development ortaminda ayri scheduler worker'i denemek icin:

```bash
docker compose -p fire-dev --profile scheduler up -d --build
```

Varsayilan dev project adi `fire-dev`, production project adi `fire-prod` olarak ayrilmistir. Compose dosyalarinda bu adlar tanimli olsa da komutlarda `-p` kullanmak niyeti acik tutar.

Dev ortami kapatmak icin:

```bash
docker compose -p fire-dev down
```

Prod ortami kapatmak icin:

```bash
docker compose -p fire-prod -f docker-compose.prod.yml down
```

Varsayilan dev calistirma Postgres, web backend ve frontend servislerini baslatir; scheduler worker profili manuel acilir.

## Model Artifacts

V3 ML modeli `app/ml/final_models_v3` altindaki artifact paketini kullanir. Buyuk `.joblib` dosyalari Git'e alinmaz; fresh clone, CI veya production deploy oncesinde ayrica saglanmalidir.

Model paketini dogrulamak icin:

```bash
python scripts/check_model_artifacts.py
```

Detayli artifact stratejisi icin [MODEL_ARTIFACTS.md](MODEL_ARTIFACTS.md) dosyasina bakin.

Kok teslim dokumani icin:

```txt
../TESLIM_DOKUMANTASYONU.md
```

Testleri calistirin:

```bash
TEST_DATABASE_URL='postgresql://fire_user:replace_with_test_database_password@localhost:5432/fire_detection_test' pytest
```

---

## API Key Security

Bazi operasyonel endpointler API key ile korunmaktadir.

Korunan endpointlere istek atarken asagidaki header gonderilmelidir:

```bash
X-API-Key: your_api_key_here
```

Ornek:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots" \
  -H "X-API-Key: $API_KEY"
```

API key `.env` dosyasinda asagidaki degiskenle tanimlanir:

```env
API_KEY=replace_with_strong_backend_api_key
```

Public endpointler API key istemez:

- GET /health
- GET /map/hotspots
- GET /map/stats
- GET /map/status
- GET /hotspots
- GET /hotspots/{id}
- GET /alerts
- GET /alerts/active
- GET /api/ml/status

---

## Health Check

Backend saglik durumunu kontrol etmek icin:

```bash
curl http://localhost:8000/health
```

Ornek cevap:

```json
{
  "status": "ok",
  "app": "Fire Detection Backend",
  "environment": "development",
  "version": "v3",
  "database": "connected",
  "ml_model": "loaded",
  "scheduler": "disabled",
  "security": "enabled"
}
```

Alan aciklamalari:

- `status`: Genel sistem durumu. `ok` veya `degraded` olabilir.
- `database`: Veritabani baglanti durumu.
- `ml_model`: ML model yuklenme durumu.
- `scheduler`: Otomatik veri cekme sisteminin durumu.
- `security`: API key guvenliginin yapilandirilip yapilandirilmadigi.

---

## NASA FIRMS Fetch

NASA FIRMS sicak nokta verilerini cekmek icin:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=turkey&days=3" \
  -H "X-API-Key: $API_KEY"
```

Parametreler:

- `country`: Veri cekilecek ulke. Varsayilan: `turkey`
- `days`: Kac gunluk gecmis veri cekilecegi. Varsayilan: `5`, aralik: `1-10`

Desteklenen ulke degerleri:

- `turkey`
- `turkiye`
- `türkiye`
- `greece`
- `cyprus`

Not:
Bu endpoint operasyonel bir endpoint oldugu icin `X-API-Key` header zorunludur.

---

## Scheduler Management

Scheduler durumunu gormek icin:

```bash
curl http://localhost:8000/scheduler/status
```

Ornek response:

```json
{
  "status": "ok",
  "scheduler": "disabled",
  "enabled": false,
  "is_running": false,
  "last_run_at": null,
  "last_success_at": null,
  "last_error": null
}
```

Manuel tek seferlik scheduler cycle calistirmak icin:

```bash
curl -X POST "http://localhost:8000/scheduler/run-once" \
  -H "X-API-Key: $API_KEY"
```

Sadece sehir bilgisi eksik olan hotspot kayitlarini manuel cozmek icin:

```bash
curl -X POST "http://localhost:8000/scheduler/resolve-cities-once?batch_size=20" \
  -H "X-API-Key: $API_KEY"
```

Bu endpoint NASA fetch, Weather veya ML akisini calistirmaz. Yalnizca `city` alani bos olan kayitlar icin reverse geocoding yapar. Sehir bulunamazsa kayit `Bilinmiyor` olarak isaretlenir ve tekrar tekrar ayni kayda takilmaz.

Not:
`POST /scheduler/run-once` ve `POST /scheduler/resolve-cities-once` operasyonel endpointler oldugu icin `X-API-Key` header zorunludur.

---

## API Error Responses

Backend API hata cevaplari standart HTTP status kodlariyla doner.

Ornek hata cevabi:

```json
{
  "detail": "Hotspot not found"
}
```

Genel hata kodlari:

- `400 Bad Request`: Gecersiz istek veya desteklenmeyen parametre
- `401 Unauthorized`: Eksik veya yanlis API key
- `404 Not Found`: Kayit bulunamadi
- `409 Conflict`: Ayni anda calisan islem cakismasi
- `422 Validation Error`: Query/body validation hatasi
- `500 Internal Server Error`: Beklenmeyen sunucu hatasi

---

## Timezone Handling

Backend icinde UTC zaman kullanimi modernlestirilmistir. Deprecated `datetime.utcnow()` kullanimi yerine timezone-aware UTC yaklasimi tercih edilmistir.

Kullanilan temel yaklasim:

```python
datetime.now(timezone.utc)
```

Veritabani kolonlari timezone-naive `DateTime` yapisini korudugu icin DB yazimlari ve DB datetime karsilastirmalari uyumlu UTC helper ile naive UTC olarak tutulur. Bu sayede schema veya migration degisikligi yapmadan Python 3.12+ deprecated datetime uyarilari azaltilmistir.

---

## Database Migrations

Bu projede Alembic migration altyapisi eklenmistir.

Migration dosyalari:

```text
migrations/
├── env.py
├── script.py.mako
└── versions/
```

Mevcut asamada Alembic altyapisi eklenmis, ancak `create_all` davranisi kaldirilmamistir. Bu sayede mevcut local/test calisma duzeni bozulmadan migration sistemine gecis hazirlanmistir.

Alembic komutlari:

```bash
alembic current
alembic history
alembic upgrade head
```

Yeni migration olusturmak icin:

```bash
alembic revision --autogenerate -m "description"
```

Not:
Production veya mevcut dolu veritabanlarinda migration calistirmadan once yedek alinmalidir.

---

## Docker Compose ile Calistirma

Backend ve PostgreSQL servislerini birlikte calistirmak icin:

```bash
docker compose up --build
```

Backend calistiktan sonra health kontrolu:

```bash
curl http://localhost:8000/health
```

Beklenen ornek cevap:

```json
{
  "status": "ok",
  "app": "Fire Detection API",
  "environment": "development",
  "version": "v3",
  "database": "connected",
  "ml_model": "loaded",
  "scheduler": "disabled",
  "security": "enabled"
}
```

Scheduler durumunu kontrol etmek icin:

```bash
curl http://localhost:8000/scheduler/status
```

NASA veri cekme endpoint'i API key gerektirir:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=turkey&days=3" \
  -H "X-API-Key: $API_KEY"
```

Containerlari durdurmak icin:

```bash
docker compose down
```

Volume ile birlikte tamamen temizlemek icin:

```bash
docker compose down -v
```

Notlar:

- Docker Compose icinde PostgreSQL host adi `postgres` olarak kullanilir.
- Local calistirmada PostgreSQL host genelde `localhost` olur.
- `postgres_data` volume sayesinde container kapatilsa bile veritabani verileri korunur.
- `API_KEY` production ortaminda mutlaka degistirilmelidir.
- `ENABLE_SCHEDULER=false` varsayilan birakilmistir. Boylece container acilir acilmaz dis API cagrilari baslamaz.

---

## Onemli Not

Bu proje bitirme projesi ve local demo icin guclu bir seviyededir. Production kullanimi icin guvenlik, migration, scheduler yonetimi, rate limit ve deployment tarafinda gelistirmeler yapilmalidir.

---

## Final Project Status

Final dogrulama sonucunda:

- Backend testleri: `137 passed`
- Frontend build: basarili
- Public endpointler: calisiyor
- Protected endpointler: API key ile korunuyor
- CORS: `http://localhost:5173` icin dogrulandi
- Alembic baseline: mevcut
- Docker Compose dosyalari: hazir
- Docker CLI bu ortamda bulunmadigi icin build testi calistirilamadi

Detayli bilgi icin:

- `FINAL_PROJECT_REPORT.md`
- `FINAL_TEST_REPORT.md`
- `PRESENTATION_NOTES.md`
- `DEMO_SCENARIO.md`
- `PROJECT_SUMMARY.md`
