# Presentation Notes

## 1. Giris

Merhaba, bu projede NASA FIRMS uydu verilerini kullanarak yangin riski tasiyan sicak noktalari analiz eden yapay zeka destekli bir yangin izleme sistemi gelistirdim.

Projenin amaci, gelen bir hotspot kaydinin gercek yangin riski tasiyip tasimadigini backend ve makine ogrenmesi modeliyle degerlendirmektir.

---

## 2. Problem

Orman yanginlarinin erken tespiti cok onemlidir. Geleneksel sistemler her zaman genis alanlari surekli izleyemez. Dronlar ve kameralar faydali olsa da maliyetli olabilir ve her bolgede uygulanamayabilir.

Bu yuzden uydu tabanli, otomatik calisan ve yapay zeka ile desteklenen bir sistem gelistirdim.

---

## 3. Cozum

Sistem NASA FIRMS verisini alir, bu veriyi hava durumu ve yangin riskiyle ilgili ozelliklerle zenginlestirir, ardindan V3 makine ogrenmesi modeli ile yangin olasiligi uretir.

Sonuclar frontend harita/dashboard uzerinde gosterilir.

---

## 4. Sistem Akisi

Sistem akisi su sekildedir:

```text
NASA FIRMS -> Backend -> Weather Features -> ML Model -> Prediction -> Alert -> Frontend Map
```

---

## 5. Backend

Backend FastAPI ile gelistirildi.

Backend icinde:

- NASA veri cekme endpointleri
- Hotspot endpointleri
- Map endpointleri
- ML endpointleri
- Alert endpointleri
- Scheduler endpointleri
- Health endpointi

bulunmaktadir.

---

## 6. ML Model

V3 model sistemi birden fazla makine ogrenmesi algoritmasini kullanir.

Model her hotspot icin:

- yangin olasiligi
- risk seviyesi
- karar seviyesi

uretir.

---

## 7. Guvenlik

Operasyonel endpointler API key ile korunmustur.

Ornegin NASA veri cekme veya scheduler run-once endpointleri `X-API-Key` olmadan calismaz.

Public endpointler ise harita ve sistem durumu icin acik birakilmistir.

---

## 8. Frontend

Frontend backend'e `.env` uzerinden baglanmaktadir.

```env
VITE_API_BASE_URL=http://localhost:8000
```

Frontend tarafinda:

- hotspot verileri
- map status
- scheduler status
- health bilgisi
- dashboard/stat bilgileri

gosterilmektedir.

---

## 9. Test

Final test sonucunda backend tarafinda:

```text
137 passed
```

sonucu alinmistir.

Frontend build de basarili sekilde tamamlanmistir.

---

## 10. Sonuc

Proje; backend, frontend, ML modeli, NASA verisi, guvenlik, scheduler ve test altyapisiyla final demo icin hazir durumdadir.
