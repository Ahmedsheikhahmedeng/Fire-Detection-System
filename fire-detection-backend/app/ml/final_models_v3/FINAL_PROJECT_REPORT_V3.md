# Final Project Report V3

## Final V3 Kararı

V3 paketi, 2022 external verinin kontrollü şekilde eğitim verisine eklenmesiyle oluşturuldu. 2022'nin tamamı eğitime alınmadı; high-confidence pozitifler, düşük ağırlıklı approx pozitifler ve kontrollü negatif sampling kullanıldı. 2022 içinden ayrı `holdout_2022` seti ayrıldı.

## Final Mimari

```text
Primary Watch / Early Warning: V3 LightGBM full
Backup / Holdout-best Watch:   V3 CatBoost full
Stable Ensemble:               HGB + XGBoost + LightGBM + CatBoost average
Balanced Verifier:             V3 RF
Strict Verifier:               V3 ExtraTrees
```

## Thresholdlar

```json
{
  "version": "v3",
  "primary_watch_model": "v3_lightgbm_full",
  "holdout_best_watch_model": "v3_catboost_full",
  "stable_ensemble_model": "average_hgb_xgboost_lightgbm_catboost",
  "lightgbm_watch_threshold": 0.56,
  "catboost_watch_threshold": 0.64,
  "xgboost_watch_threshold": 0.68,
  "hgb_core_watch_threshold": 0.6,
  "ensemble_watch_threshold": 0.73,
  "rf_balanced_threshold": 0.46,
  "rf_recall90_threshold": 0.5,
  "extratrees_strict_threshold": 0.52,
  "extratrees_recall90_threshold": 0.5,
  "decision_system": {
    "level_0": "low_risk_no_fire",
    "level_1": "watch_early_warning",
    "level_2": "high_confidence_balanced_fire",
    "level_3": "strict_fire_alert",
    "level_4": "very_strict_fire_alert"
  },
  "notes": "Thresholds selected only from V3 validation split. test_2021 and holdout_2022 were used only for evaluation."
}
```

## V3 Dataset

```text
Toplam satır: 12397
Feature sayısı: 101
Splitler:
[
  {
    "split_v3": "holdout_2022",
    "fire": 0,
    "count": 600
  },
  {
    "split_v3": "holdout_2022",
    "fire": 1,
    "count": 188
  },
  {
    "split_v3": "test_2021",
    "fire": 0,
    "count": 1247
  },
  {
    "split_v3": "test_2021",
    "fire": 1,
    "count": 1430
  },
  {
    "split_v3": "train",
    "fire": 0,
    "count": 5567
  },
  {
    "split_v3": "train",
    "fire": 1,
    "count": 1690
  },
  {
    "split_v3": "valid",
    "fire": 0,
    "count": 1285
  },
  {
    "split_v3": "valid",
    "fire": 1,
    "count": 390
  }
]
```

## Ana Model Performansı

### V3 LightGBM Full

```text
test_2021:    precision 0.6951 | recall 0.9678 | F1 0.8091 | TN 640 | FP 607 | FN 46 | TP 1384
holdout_2022: precision 0.8763 | recall 0.8670 | F1 0.8717 | TN 577 | FP 23 | FN 25 | TP 163
```

### V3 CatBoost Full

```text
test_2021:    precision 0.6850 | recall 0.9399 | F1 0.7925 | TN 629 | FP 618 | FN 86 | TP 1344
holdout_2022: precision 0.8520 | recall 0.8883 | F1 0.8698 | TN 571 | FP 29 | FN 21 | TP 167
```

### V3 Boosting Ensemble

```text
test_2021:    precision 0.7083 | recall 0.9287 | F1 0.8036 | TN 700 | FP 547 | FN 102 | TP 1328
holdout_2022: precision 0.9017 | recall 0.8298 | F1 0.8643 | TN 583 | FP 17 | FN 32 | TP 156
```

## Verifier Modeller

### V3 RF Balanced Verifier

```text
test_2021:    precision 0.8968 | recall 0.5042 | F1 0.6455 | TN 1164 | FP 83 | FN 709 | TP 721
holdout_2022: precision 0.8384 | recall 0.8830 | F1 0.8601 | TN 568 | FP 32 | FN 22 | TP 166
```

### V3 ExtraTrees Strict Verifier

```text
test_2021:    precision 0.9427 | recall 0.2531 | F1 0.3991 | TN 1225 | FP 22 | FN 1068 | TP 362
holdout_2022: precision 0.8503 | recall 0.8457 | F1 0.8480 | TN 572 | FP 28 | FN 29 | TP 159
```

## Eski V2'ye Göre Ana İyileşme

Eski final model 2022 external testte:

```text
precision 0.3926 | recall 0.3646 | F1 0.3781 | FN 800
```

V3 holdout_2022 tarafında:

```text
LightGBM:  precision 0.8763 | recall 0.8670 | F1 0.8717 | TN 577 | FP 23 | FN 25 | TP 163
CatBoost:  precision 0.8520 | recall 0.8883 | F1 0.8698 | TN 571 | FP 29 | FN 21 | TP 167
Ensemble:  precision 0.9017 | recall 0.8298 | F1 0.8643 | TN 583 | FP 17 | FN 32 | TP 156
```

## Dürüst Değerlendirme

2022 önce external test olarak kullanıldı ve modelin düşük sezon / match-rule farklılıklarında zayıf kaldığı görüldü. Daha sonra 2022 verisi kontrollü şekilde V3 eğitim setine eklendi ve ayrı `holdout_2022` setinde değerlendirildi. Bu nedenle V3, production adayıdır; ancak ileride 2023/2024 gibi yeni bir yıl gerçek external test olarak kullanılmalıdır.
