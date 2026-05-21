# Demo Scenario

## Amac

Bu demo, yangin tespit sisteminin backend, frontend, API guvenligi ve dashboard akisini gostermek icin hazirlanmistir.

---

## 1. Backend'i Baslat

```bash
cd /Users/deneme/Desktop/bitirmeprojesifull/fire-detection-backend
uvicorn app.main:app --reload
```

---

## 2. Health Check Goster

```bash
curl http://localhost:8000/health
```

Beklenen:

```json
{
  "status": "ok",
  "database": "connected",
  "ml_model": "loaded",
  "scheduler": "disabled",
  "security": "enabled"
}
```

Anlatilacak:
Sistemin database, ML model, scheduler ve security durumlari buradan gorulebilir.

---

## 3. Public Endpointleri Goster

```bash
curl http://localhost:8000/map/status
curl http://localhost:8000/map/stats
curl http://localhost:8000/map/hotspots
curl http://localhost:8000/scheduler/status
```

Anlatilacak:
Harita ve sistem durumu icin gerekli public endpointler API key istemeden calisir.

---

## 4. API Key Guvenligini Goster

API key olmadan:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=turkey&days=3"
```

Beklenen:

```text
401 Invalid or missing API key
```

API key ile:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=turkey&days=3" \
  -H "X-API-Key: change_this_api_key"
```

Anlatilacak:
Operasyonel endpointler korunur.

---

## 5. NASA Validation Goster

Gecersiz ulke:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=france&days=3" \
  -H "X-API-Key: change_this_api_key"
```

Beklenen:

```text
400 Unsupported country
```

Gecersiz gun sayisi:

```bash
curl -X POST "http://localhost:8000/nasa/fetch-hotspots?country=turkey&days=100" \
  -H "X-API-Key: change_this_api_key"
```

Beklenen:

```text
422 validation error
```

---

## 6. Frontend'i Baslat

```bash
cd /Users/deneme/Desktop/bitirmeprojesifull/bitirmeprojesi_frontend
npm run dev
```

Tarayici:

```text
http://localhost:5173
```

Anlatilacak:
Frontend backend'e `.env` uzerinden baglanir ve harita/dashboard verilerini gosterir.

---

## 7. Test Sonucunu Goster

```bash
cd /Users/deneme/Desktop/bitirmeprojesifull/fire-detection-backend
TEST_DATABASE_URL='postgresql://deneme:@localhost:5432/fire_detection_test' python -m pytest tests -q
```

Beklenen:

```text
137 passed
```

---

## 8. Final Kapanis

Anlatilacak:
Bu sistem NASA FIRMS verisini alip, hava durumu ve ML modeliyle yangin riski tahmini yapabilen, frontend dashboard ile sonuclari gosteren, API guvenligi ve test altyapisi bulunan final proje seviyesinde bir sistemdir.
