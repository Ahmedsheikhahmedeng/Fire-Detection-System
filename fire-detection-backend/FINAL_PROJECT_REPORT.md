# Fire Detection System - Final Project Report

## 1. Proje Ozeti

Bu proje, NASA FIRMS uydu sicak nokta verilerini kullanarak yangin riski tasiyan bolgeleri tespit etmeyi amaclayan yapay zeka destekli bir yangin izleme sistemidir.

Sistem; uydu verisi, hava durumu ozellikleri, makine ogrenmesi modeli, backend API, canli harita/dashboard ve uyari mekanizmasini bir araya getirir.

---

## 2. Problem Tanimi

Orman yanginlarinin erken tespiti, can ve mal kaybini azaltmak icin kritik oneme sahiptir. Geleneksel yontemler genis alanlarda her zaman yeterli olmayabilir. Dronlar, kameralar veya sensorler belirli bolgelerde etkili olsa da maliyet, erisim ve kapsama acisindan sinirlidir.

Bu nedenle sistem, NASA FIRMS uzerinden gelen sicak nokta verilerini analiz ederek her noktanin gercek yangin riski tasiyip tasimadigini degerlendirmeyi hedefler.

---

## 3. Cozum Yaklasimi

Sistem su akisla calisir:

```text
NASA FIRMS Hotspot
        |
        v
Backend API
        |
        v
Weather + FWI Feature Pipeline
        |
        v
V3 ML Model
        |
        v
Fire Probability / Risk Level
        |
        v
Database
        |
        v
Map Dashboard + Alert System
```

---

## 4. Kullanilan Teknolojiler

### Backend

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pytest

### Machine Learning

- HistGradientBoosting
- XGBoost
- LightGBM
- CatBoost
- RandomForest
- ExtraTrees

### Data Sources

- NASA FIRMS
- Weather API / Open-Meteo tarzi hava durumu kaynaklari

### Frontend

- React / Vite
- Merkezi API service yapisi
- Harita ve dashboard bilesenleri

### DevOps

- Dockerfile
- Docker Compose
- PostgreSQL volume
- Environment-based configuration

---

## 5. Backend Mimarisi

Backend FastAPI ile gelistirilmistir. API yapisi farkli routerlara ayrilmistir:

- Health
- NASA
- Hotspots
- Map
- ML
- Weather
- Alerts
- Scheduler

Backend ayrica API key guvenligi, CORS kontrolu, health check, scheduler status ve run-once endpointleri icerir.

---

## 6. NASA FIRMS Entegrasyonu

NASA FIRMS endpoint'i sicak nokta verilerini cekmek icin kullanilir.

Endpoint:

```text
POST /nasa/fetch-hotspots?country=turkey&days=3
```

Ozellikler:

- API key korumasi vardir.
- `country` parametresi desteklenir.
- `days` parametresi 1-10 arasi dogrulanir.
- Gecersiz country icin 400 doner.
- Gecersiz days icin 422 doner.

Desteklenen ulke degerleri:

- turkey
- turkiye
- türkiye
- greece
- cyprus

---

## 7. ML Pipeline

Makine ogrenmesi sistemi, her hotspot icin yangin olasiligi uretir.

Model girdileri genel olarak sunlardan olusur:

- FIRMS uydu ozellikleri
- Konum bilgisi
- Zaman bilgisi
- Hava durumu ozellikleri
- FWI ve yangin riskiyle iliskili turetilmis ozellikler

Model ciktisi:

```text
fire_probability
decision_level
risk_category
```

V3 model servisi backend'e entegre edilmistir ve health endpoint uzerinden modelin yuklu olup olmadigi gorulebilir.

---

## 8. Scheduler Sistemi

Scheduler sistemi NASA + weather + ML akisini otomatik veya manuel calistirmak icin kullanilir.

Eklenen endpointler:

```text
GET /scheduler/status
POST /scheduler/run-once
```

- `/scheduler/status` public endpointtir.
- `/scheduler/run-once` API key gerektirir.
- Ayni anda iki cycle calismasi 409 Conflict ile engellenir.
- Varsayilan olarak Docker ortaminda `ENABLE_SCHEDULER=false` birakilmistir.

---

## 9. Guvenlik

API guvenligi kapsaminda asagidaki duzenlemeler yapilmistir:

- CORS ayari `FRONTEND_URL` uzerinden yonetilir.
- `allow_origins=["*"]` kaldirilmistir.
- Operasyonel endpointler `X-API-Key` ile korunmustur.
- Public GET endpointler acik birakilmistir.

Public endpoint ornekleri:

```text
GET /health
GET /map/status
GET /map/stats
GET /map/hotspots
GET /scheduler/status
```

Protected endpoint ornekleri:

```text
POST /nasa/fetch-hotspots
POST /scheduler/run-once
POST /weather/...
PATCH /alerts/...
```

---

## 10. Health Check

`/health` endpoint'i sistemin temel durumlarini gosterir.

Ornek response:

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

---

## 11. Frontend Entegrasyonu

Frontend tarafinda backend baglantisi environment variable uzerinden yonetilir.

```env
VITE_API_BASE_URL=http://localhost:8000
```

Merkezi API service dosyasi:

```text
src/services/api.js
```

Frontend public endpointleri kullanir:

- `/health`
- `/map/status`
- `/map/stats`
- `/map/hotspots`
- `/scheduler/status`

Protected endpointler frontend'den bu asamada cagrilmamaktadir.

---

## 12. Docker ve Calistirma

Backend icin Dockerfile ve Docker Compose yapilandirmasi hazirlanmistir.

Servisler:

- backend
- postgres

Docker Compose icinde:

- PostgreSQL volume vardir.
- PostgreSQL healthcheck vardir.
- Backend, PostgreSQL healthy olduktan sonra baslar.
- Scheduler varsayilan olarak disabled birakilmistir.

Calistirma komutu:

```bash
docker compose up --build
```

Not:
Final test ortaminda Docker CLI bulunmadigi icin docker compose build dogrulanamamistir. Docker dosyalari hazirlanmis, ancak build testi bu ortamda calistirilamamistir.

---

## 13. Alembic Migration Altyapisi

Alembic migration altyapisi eklenmistir.

Eklenen dosyalar:

```text
alembic.ini
migrations/env.py
migrations/script.py.mako
migrations/versions/0001_baseline.py
```

Bu asamada:

- `create_all` kaldirilmamistir.
- Database schema degistirilmemistir.
- `alembic upgrade head` otomatik calistirilmamistir.
- Bos baseline migration eklenmistir.

---

## 14. Test Sonuclari

Final test sonucu:

```text
Backend pytest: 137 passed
Frontend build: passed
```

Kontrol edilenler:

- Backend compile
- `/health`
- Public endpointler
- Protected endpoint guvenligi
- NASA validation
- CORS
- Frontend build
- Frontend API base URL
- Alembic history

---

## 15. Final Degerlendirme

Proje final dogrulama acisindan iyi durumdadir. Backend testleri gecmekte, frontend build basarili olmakta, API guvenligi calismakta, CORS dogru yapilandirilmistir ve NASA/ML/Scheduler akislari kontrollu hale getirilmistir.

Bu proje, bitirme projesi/demo seviyesi icin guclu ve sunulabilir bir yangin izleme sistemidir.

---

## 16. Gelecek Gelistirmeler

Ileride yapilabilecek gelistirmeler:

- Alembic ile gercek schema migration surecine gecmek
- Production deployment yapmak
- Admin paneli eklemek
- Alert yonetimini kullanici bazli hale getirmek
- Gercek zamanli WebSocket dashboard gelistirmek
- Model izleme ve performans loglari eklemek
- Daha genis yangin dogrulama veri setiyle modeli guncellemek
