# Model Artifacts

V3 prediction runtime su model paketini bekler:

```txt
app/ml/final_models_v3
```

Bu dizin `V3_MODEL_DIR` environment degiskeniyle degistirilebilir.

## Git Stratejisi

`.joblib` model dosyalari buyuk oldugu icin Git'e alinmaz. `.gitignore` icinde `*.joblib` ignore edilir.

Repo icinde kucuk JSON metadata dosyalari, feature listeleri ve manifest tutulur. Buyuk model dosyalari deployment ortaminda ayrica saglanmalidir.

Not: `full_feature_columns.json` icinde okunabilirlik icin `//` yorumlari bulunabilir. Backend loader ve artifact checker bu dosyayi normalize ederek okur; `.joblib` dosyalari ise byte-level SHA-256 ile dogrulanmaya devam eder.

## Gerekli Dosyalar

Model paketinin dogrulanabilir listesi:

```txt
app/ml/final_models_v3/model_artifacts_manifest.json
```

Beklenen buyuk model dosyalari:

```txt
v3_hgb_core_model.joblib
v3_xgboost_full_model.joblib
v3_lightgbm_watch_model.joblib
v3_catboost_watch_model.joblib
v3_rf_balanced_verifier_model.joblib
v3_extratrees_strict_verifier_model.joblib
```

Beklenen metadata dosyalari:

```txt
hgb_core_feature_columns.json
full_feature_columns.json
threshold_config_v3.json
model_package_metadata_v3.json
```

Toplam artifact boyutu yaklasik 149 MB'dir.

## Dogrulama

Local veya deployment ortaminda model paketi hazirlandiktan sonra:

```bash
python scripts/check_model_artifacts.py
```

Farkli model dizini kullaniliyorsa:

```bash
python scripts/check_model_artifacts.py --model-dir /models/final_models_v3
```

Sadece dosya varligi ve boyut kontrolu icin:

```bash
python scripts/check_model_artifacts.py --skip-checksum
```

## Docker Kullanimi

Development Docker build mevcut local `app/ml/final_models_v3` dizinini image icine alir. Fresh clone veya CI ortaminda build almadan once model artifact paketi bu dizine konulmalidir.

Production icin onerilen yontem:

1. Model paketini release artifact, object storage veya deployment secret/artifact sistemi uzerinden sagla.
2. Paket dosyalarini `app/ml/final_models_v3` altina yerlestir veya `V3_MODEL_DIR` ile farkli bir path kullan.
3. `python scripts/check_model_artifacts.py` ile manifest dogrula.
4. Docker image'i build et veya runtime volume mount ile `V3_MODEL_DIR` path'ini container'a bagla.

Model dosyalari degistiginde manifest yeniden uretilmeli ve checksum'lar guncellenmelidir.

Feature listesi degistiginde `full_feature_columns.json` icin normalize edilmis hash de manifest icinde guncellenmelidir.
