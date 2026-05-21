# API Overview

## Genel Bilgi

Bu dosya yangin tespit backend sistemindeki ana API endpoint gruplarini aciklar.

Backend FastAPI ile gelistirilmistir.

---

## Ana Endpoint Gruplari

### 1. Health

Sistemin calisip calismadigini kontrol eder.

```text
GET /health
```

Amac:

```text
Backend ayakta mi?
```

---

### 2. Hotspots

NASA FIRMS uzerinden gelen sicak nokta kayitlarini yonetir.

Ornek endpointler:

```text
GET /hotspots
GET /hotspots/{id}
```

Amac:

```text
Hotspot verilerini listelemek ve detaylarini almak.
```

---

### 3. NASA

NASA FIRMS uzerinden sicak nokta verisi cekmek icin kullanilir.

```text
POST /nasa/fetch-hotspots?country=turkey&days=3
```

Bu endpoint API key gerektirir.

Parametreler:

```text
country: Veri cekilecek ulke.
days: Kac gunluk gecmis verinin cekilecegi.
```

Validasyon:

```text
days degeri 1 ile 10 arasinda olmalidir.
Desteklenmeyen country degerleri icin 400 hata doner.
```

---

### 4. Weather

Hotspot verilerini hava durumu bilgileriyle zenginlestirir.

Ornek endpoint:

```text
POST /weather/enrich/{hotspot_id}
```

Amac:

```text
Yangin tahmini icin gerekli meteorolojik ozellikleri uretmek.
```

---

### 5. ML

Makine ogrenmesi tahminleri icin kullanilir.

Ornek endpointler:

```text
GET /api/ml/status
POST /api/ml/validate-engineered
POST /api/ml/predict-engineered
POST /api/ml/predict-hotspot
POST /api/ml/predict-hotspot-db-context
```

Amac:

```text
Hotspot kayitlari icin yangin olasiligi uretmek.
```

---

### 6. Alerts

Yuksek riskli hotspotlar icin alarm kayitlarini yonetir.

Ornek islemler:

```text
GET /alerts
GET /alerts/active
POST /alerts/check/{hotspot_id}
PATCH /alerts/{alert_id}/status
POST /alerts/{alert_id}/close
WebSocket /alerts/ws
```

---

### 7. Map

Frontend harita sayfasi icin veri saglar.

Ornek endpointler:

```text
GET /map/hotspots
GET /map/stats
GET /map/status
```

Amac:

```text
Canli yangin risk haritasinda gosterilecek verileri saglamak.
```

---

### 8. Scheduler

Otomatik NASA + weather + ML akisinin durumunu gormek ve manuel tek seferlik cycle calistirmak icin kullanilir.

```text
GET /scheduler/status
POST /scheduler/run-once
```

- `GET /scheduler/status`: Public endpointtir, scheduler durumunu dondurur.
- `POST /scheduler/run-once`: API key gerektirir ve tek seferlik full cycle calistirir.

Mevcut harita status endpointi de scheduler durumunu okuyabilir:

```text
GET /map/status
```

---

## Genel API Akisi

```text
NASA endpoint
      |
      v
Hotspot database
      |
      v
Weather enrichment
      |
      v
ML prediction
      |
      v
Alert
      |
      v
Map API
      |
      v
Frontend
```

---

## Error Handling

API hata cevaplari FastAPI `HTTPException` formatina uygun olarak doner.

Ornek:

```json
{
  "detail": "Alert not found"
}
```

Kayit bulunamadiginda `404`, yetkisiz isteklerde `401`, gecersiz parametrelerde `400` veya `422`, islem cakismalarinda `409` doner.

---

## Final Not

API yapisi genel olarak bitirme projesi icin yeterli seviyededir. Final asamasinda endpoint guvenligi, parametre validasyonu ve hata cevaplari iyilestirilecektir.
