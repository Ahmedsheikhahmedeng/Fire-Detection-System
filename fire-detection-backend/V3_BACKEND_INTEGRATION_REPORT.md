# V3 Fire Hotspot Validation Model — Backend Integration Report

## Summary

V3 production-candidate model, FastAPI backend pipeline'ina uctan uca entegre edilmistir.

Sistem NASA FIRMS hotspot verisini alir, hotspot'u veritabanina kaydeder, V3 feature pipeline ile temporal, spatial, weather ve FWI proxy ozelliklerini uretir, ML prediction yapar, sonucu veritabanina kaydeder ve yuksek risk durumunda alert olusturur.

## Final Pipeline

```text
NASA FIRMS
-> Hotspot DB
-> V3 Feature Pipeline
-> V3 Model Prediction
-> Prediction DB
-> Alert DB
-> WebSocket Notification Queue
```

## Backend Flow

NASA FIRMS hotspot verisi alindiginda sistem su adimlari calistirir:

1. Hotspot verisini NASA FIRMS CSV row'dan okur.
2. Hotspot'u veritabanina kaydeder.
3. NASA row'dan V3 model icin zengin payload uretir.
4. DB'den son 72 saatlik yakin hotspot context cikarir.
5. Spatial nearby feature'lari uretir.
6. Open-Meteo uzerinden 24h / 3d / 7d weather feature'lari uretir.
7. VPD, dryness ve FWI proxy feature'lari hesaplar.
8. V3 modellerle prediction yapar.
9. Prediction sonucunu DB'ye kaydeder.
10. `decision_level >= 2` ise alert olusturur.
11. Alert icin WebSocket broadcast queue olusturur.

## V3 Model Architecture

Final V3 sistemi tek modelden olusmaz. Cok asamali karar mimarisi kullanir:

- Primary Watch Model: V3 LightGBM
- Backup / Holdout-best Model: V3 CatBoost
- Stable Ensemble: HGB + XGBoost + LightGBM + CatBoost average
- Balanced Verifier: V3 Random Forest
- Strict Verifier: V3 ExtraTrees

Model ciktisi sadece binary fire/no-fire degildir. Sistem decision level uretir.

## Decision Levels

| Level | Name | Meaning |
|---|---|---|
| 0 | low_risk_no_fire | Dusuk risk, alert yok |
| 1 | watch_early_warning | Erken uyari / izleme |
| 2 | high_confidence_balanced_fire | Yuksek guvenli yangin adayi |
| 3 | strict_fire_alert | Ciddi yangin alarmi |
| 4 | very_strict_fire_alert | Cok yuksek guvenli yangin alarmi |

Alert uretme kurali:

```text
decision_level >= 2 ise alert olusturulur.
```

## Updated Backend Files

### Model Package

- `app/ml/final_models_v3/`

### Core ML Integration

- `app/services/ml_service.py`
- `app/services/feature_pipeline.py`
- `app/services/spatial_context_service.py`
- `app/services/weather_service.py`
- `app/services/prediction_service.py`
- `app/services/alert_service.py`
- `app/services/websocket_alert_service.py`

### API Layer

- `app/api/ml.py`
- `app/schemas/ml.py`

### NASA / Scheduler Integration

- `app/services/nasa_service.py`
- `app/services/scheduler.py`
- `app/api/nasa.py`

### Config

- `app/core/config.py`
- `.env`
- `requirements.txt`

## ML API Endpoints

### Health

```http
GET /health
```

### ML Status

```http
GET /api/ml/status
```

### Validate Engineered Features

```http
POST /api/ml/validate-engineered
```

### Predict with Engineered Features

```http
POST /api/ml/predict-engineered
```

### Predict Raw Hotspot

```http
POST /api/ml/predict-hotspot
```

### Predict Raw Hotspot with DB Context

```http
POST /api/ml/predict-hotspot-db-context
```

## Test Commands

### Model package check

```bash
python check_v3_model_package.py
```

### Model load test

```bash
python test_load_v3_models.py
```

### ML service test

```bash
python test_v3_ml_service.py
```

### Engineered prediction API test

```bash
python test_api_predict_engineered.py
```

### Raw hotspot prediction API test

```bash
python test_api_predict_hotspot.py
```

### Spatial context test

```bash
python test_spatial_context_pipeline.py
```

### Weather pipeline test

```bash
python test_weather_pipeline.py
```

### DB-context prediction test

```bash
python test_api_predict_hotspot_db_context.py
```

### NASA fetch V3 integration test

```bash
python test_nasa_fetch_v3_integration.py
```

### Mock NASA full integration test

```bash
python test_mock_nasa_v3_integration.py
```

## Mock NASA Integration Test Result

Mock NASA row ile uctan uca test basariyla gecmistir.

Test sonucu:

- `hotspot_id`: 645
- `saved_prediction_id`: 40945
- `created_alert_id`: 246
- `decision_level`: 4
- `decision_name`: `very_strict_fire_alert`

Bu test su akisi dogrulamistir:

```text
Mock NASA row
-> Hotspot DB insert
-> V3 payload generation
-> DB-context prediction
-> Prediction DB save
-> Alert DB save
```

## Known Notes

1. Gercek NASA fetch testinde duplicate korumasi nedeniyle yeni kayit eklenmedi. Bu yuzden `inserted_count`, `v3_prediction_count` ve `v3_alert_count` degerleri 0 dondu.

2. Uctan uca entegrasyon mock NASA row ile test edilmis ve basariyla dogrulanmistir.

3. LightGBM tarafinda su warning gorulebilir:

```text
UserWarning: X does not have valid feature names, but LGBMClassifier was fitted with feature names
```

Bu warning prediction akisini engellememektedir.

4. Mevcut Hotspot DB semasi V1 seviyesindedir. V3 icin onerilen ek kolonlar:

- `frp`
- `bright_ti4`
- `bright_ti5`
- `scan`
- `track`
- `daynight`
- `instrument`
- `acq_datetime`

Bu kolonlar ileride eklendiginde spatial context ve history feature kalitesi daha da artacaktir.

## Final Status

V3 production-candidate model backend'e basariyla entegre edilmistir.

Sistem artik NASA FIRMS hotspot verisini isleyebilir, V3 feature pipeline ile model input'u uretebilir, ML tahmini yapabilir, prediction sonucunu DB'ye kaydedebilir, yuksek riskli durumlarda alert olusturabilir ve WebSocket notification queue uzerinden frontend'e anlik bildirim gonderebilir.

Backend entegrasyonu mock NASA uctan uca test ile dogrulanmistir.
