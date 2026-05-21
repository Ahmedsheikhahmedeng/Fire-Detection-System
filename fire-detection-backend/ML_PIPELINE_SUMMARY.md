# ML Pipeline Summary

## Genel Amac

Bu projedeki makine ogrenmesi pipeline'inin amaci, NASA FIRMS uzerinden gelen bir hotspot kaydinin gercek yangin riski tasiyip tasimadigini tahmin etmektir.

Model su soruya cevap verir:

```text
Bu hotspot gercek yangin riski tasiyor mu?
```

---

## Girdi Verisi

Modelin ana girdisi NASA FIRMS hotspot verisidir.

Temel FIRMS ozellikleri:

- Latitude
- Longitude
- Brightness
- FRP
- Confidence
- Satellite
- Instrument
- Day/Night
- Acquisition date
- Acquisition time

---

## Feature Engineering

Hotspot verileri hava durumu ve zamansal ozelliklerle zenginlestirilir.

Ornek feature gruplari:

### 1. FIRMS Ozellikleri

- Brightness
- FRP
- Confidence
- Scan
- Track
- Day/Night

### 2. Konum Ozellikleri

- Latitude
- Longitude
- Country
- Region bilgileri

### 3. Zaman Ozellikleri

- Ay
- Gun
- Saat
- Mevsim
- Gunduz/gece bilgisi

### 4. Weather Ozellikleri

- Sicaklik
- Nem
- Ruzgar hizi
- Yagis
- 24 saatlik hava durumu
- 3 gunluk hava durumu
- 7 gunluk hava durumu

### 5. Fire Weather Index Turevi Ozellikler

- FFMC
- DMC
- DC
- ISI
- BUI
- FWI
- Dryness score
- Wind dryness index

---

## Model Yapisi

V3 model sistemi birden fazla makine ogrenmesi algoritmasini kullanir.

Kullanilan modeller:

- HistGradientBoosting
- XGBoost
- LightGBM
- CatBoost
- RandomForest
- ExtraTrees

Bu modellerin ciktilari birlikte degerlendirilerek yangin riski tahmini yapilir.

---

## Model Ciktisi

Model her hotspot icin su ciktilari uretir:

```text
- Fire probability
- Prediction label
- Decision level
- Risk category
```

Ornek karar seviyeleri:

```text
0 -> Cok dusuk risk
1 -> Dusuk risk
2 -> Orta risk
3 -> Yuksek risk
4 -> Cok yuksek risk
```

---

## Backend Icindeki Akis

Genel ML akisi:

```text
Hotspot verisi
      |
      v
Feature pipeline
      |
      v
Weather enrichment
      |
      v
V3 ML model
      |
      v
Fire probability
      |
      v
Risk level
      |
      v
Prediction kaydi
      |
      v
Alert sistemi
```

---

## Final Sunum Cumlesi

Makine ogrenmesi modeli, NASA FIRMS sicak nokta verilerini hava durumu ve yangin davranisiyla iliskili ozelliklerle zenginlestirerek her nokta icin yangin olasiligi uretmektedir.
