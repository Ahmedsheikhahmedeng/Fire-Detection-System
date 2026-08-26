# 🔥 Yangın Tespit Sistemi - Backend

Bu proje, NASA FIRMS sıcak nokta (hotspot) verilerini ve meteorolojik bilgileri kullanarak orman yangını riskini tahmin eden yapay zeka destekli sistemin **arka plan (Backend)** servisidir.

Sistem; uydudan gelen verileri toplar, bu verileri güncel hava durumu (Open-Meteo) özellikleriyle zenginleştirir ve eğitilmiş makine öğrenmesi modellerinden geçirerek her bir bölge için bir "Yangın Riski Olasılığı" üretir. Yüksek risk tespit edildiğinde anlık uyarılar oluşturarak frontend (arayüz) katmanına iletir.

## 🌟 Öne Çıkan Özellikler

- **Çoklu Uydu Verisi Çekimi:** NASA FIRMS üzerinden VIIRS (SNPP, NOAA20, NOAA21) sensörlerinden güncel sıcak nokta verilerini toplar.
- **Dinamik Hava Durumu Entegrasyonu:** Koordinat bazlı güncel hava durumu (sıcaklık, rüzgar hızı, nem, FWI) verilerini eşleştirir.
- **Ensemble Makine Öğrenmesi (ML):** Scikit-learn, XGBoost, LightGBM ve CatBoost tabanlı modeller kullanılarak yüksek doğruluklu (V3 Modeli) yangın riski tahmini yapar.
- **Yangın Kümeleme (Clustering):** Birbirine yakın noktaları belirli bir zaman aralığında gruplayarak "Yangın Kümeleri" oluşturur, böylece uyarı karmaşasını azaltır.
- **Ayrı Scheduler (İş Planlayıcı) Mimarisi:** Arka planda çalışan periyodik görevleri (NASA verisi çekme, tahmin üretme vb.) bağımsız bir Worker servisi üzerinden yürütür.
- **Güvenli API:** Operasyonel ve yönetimsel uç noktaları (endpoint) `X-API-Key` ile korur.
- **Gelişmiş Veritabanı Yönetimi:** PostgreSQL, SQLAlchemy ve Alembic (Migration) ile sürdürülebilir bir veri katmanı sunar.

## 🛠 Kullanılan Teknolojiler

- **Dil & Framework:** Python 3.11/3.12, FastAPI
- **Veritabanı & ORM:** PostgreSQL, SQLAlchemy, Alembic (Migration), Psycopg2
- **Makine Öğrenmesi:** Scikit-learn, XGBoost, LightGBM, CatBoost, Pandas, Numpy, Joblib
- **HTTP/API Bağlantıları:** Httpx, Requests
- **Zamanlanmış Görevler:** APScheduler
- **Test:** Pytest (Resmi test suite: 140+ test geçer)
- **Konteynerleştirme:** Docker & Docker Compose

## 📁 Proje Yapısı

```bash
fire-detection-backend/
├── app/
│   ├── api/         # FastAPI Route tanımları (endpoints)
│   ├── core/        # Temel ayarlar (Settings, Security, Database)
│   ├── ml/          # Makine öğrenmesi modelleri ve tahmin mantığı (.joblib)
│   ├── models/      # SQLAlchemy veritabanı tabloları
│   ├── schemas/     # Pydantic veri doğrulama şemaları
│   ├── services/    # İş mantığı (NASA Service, ML Service, Weather Service)
│   └── main.py      # Uygulamanın giriş noktası (Entrypoint)
├── migrations/      # Alembic migration dosyaları
├── scripts/         # Bakım, kontrol (artifact checker) ve migration scriptleri
├── tests/           # Pytest ile yazılmış birim (unit) testler
├── requirements.txt # Python bağımlılıkları
├── Dockerfile       # Production için Docker imaj talimatı
└── alembic.ini      # Alembic yapılandırması
```

## ⚙️ Kurulum ve Çalıştırma (Lokal)

Projeyi geliştirme ortamında çalıştırmak için aşağıdaki adımları izleyin. (Lokalde boş bir PostgreSQL veritabanı hazırlamanız gereklidir).

### 1. Sanal Ortam (Virtual Environment) Oluşturma
```bash
cd fire-detection-backend
python -m venv .venv
source .venv/bin/activate  # Windows için: .venv\Scripts\activate
```

### 2. Bağımlılıkları Yükleme
```bash
pip install -r requirements.txt
```

### 3. Çevre Değişkenleri (.env)
`.env.example` dosyasını `.env` olarak kopyalayın ve içerisindeki değerleri kendi sisteminize göre düzenleyin:
```bash
cp .env.example .env
```
Önemli `.env` değişkenleri:
- `DB_USER`, `DB_PASSWORD`, `DB_NAME` (Postgres bilgileri)
- `NASA_API_KEY` (NASA FIRMS portalından alınacak)
- `API_KEY` (Kendi belirleyeceğiniz, operasyonel işlemleri koruyan güvenlik anahtarı)

### 4. Veritabanı ve Uygulamayı Başlatma
*Mevcut konfigürasyonda tablo oluşturma işlemleri `main.py` içinde otomatik yapılabilir (Alembic'e tam geçiş süreci devam etmektedir).*
```bash
uvicorn app.main:app --reload
```
API dökümantasyonuna (Swagger UI) `http://localhost:8000/docs` adresinden erişebilirsiniz.

## 🐳 Docker ile Çalıştırma

Proje hem geliştirme (dev) hem de canlı (prod) ortamlar için Docker Compose mimarisine sahiptir. Backend, Frontend ve PostgreSQL birlikte entegre çalışır.

### Geliştirme (Dev) Ortamı
```bash
cp .env.example .env
# .env dosyasını düzenleyin
docker compose -p fire-dev up -d --build
```
*Bu komut Backend API (8000), Frontend (5173) ve Postgres (5432) servislerini başlatır.*

### Scheduler (Zamanlayıcı) Servisini Başlatma
Verilerin periyodik olarak çekilmesi için ayrı profilde olan worker servisini çalıştırın:
```bash
docker compose -p fire-dev --profile scheduler up -d --build
```

### Canlı (Production) Ortam
```bash
cp .env.production.example .env.production
docker compose -p fire-prod --env-file .env.production -f docker-compose.prod.yml up -d --build
```
*Production ortamında `--reload` çalışmaz, uygulama root kullanıcısıyla çalıştırılmaz ve model dosyalarının bütünlüğü (artifact check) başlangıçta otomatik doğrulanır.*

## 🔌 Temel API Uç Noktaları

Backend, genel veri gösterimi ve operasyonel yönetim için çeşitli endpoint'ler sunar.

**Public (Açık) Endpoint'ler (API Key İstemez):**
- `GET /health` : Sistem sağlık durumunu ve servislerin ayakta olup olmadığını döner.
- `GET /map/hotspots` : Harita üzerinde gösterilecek aktif yangın riski noktalarını döner.
- `GET /alerts/active` : Frontend'de gösterilecek aktif yüksek risk uyarılarını döner.

**Protected (Korumalı) Endpoint'ler (Header: `X-API-Key: {API_KEY}`):**
- `POST /nasa/fetch-hotspots` : NASA üzerinden verileri çeker.
- `POST /scheduler/run-once` : Zamanlanmış veri boru hattını (Pipeline) manuel olarak bir kez tetikler.
- `POST /api/ml/predict-engineered` : Seçilen kayıtlar üzerinden makine öğrenmesi tahminini zorlar.

## 🤖 Makine Öğrenmesi (ML) Artifact'leri

`app/ml/final_models_v3` klasöründe yer alan makine öğrenmesi modelleri boyutları nedeniyle genellikle git deposuna eklenmez. Sistemin düzgün çalışabilmesi için `.joblib` model dosyalarının ilgili klasörde bulunması gerekir.
Docker veya CI/CD akışlarında bu modeller bir kontrol betiği ile doğrulanır:
```bash
python scripts/check_model_artifacts.py
```

## 📜 Lisans

Bu proje akademik bir proje olup açık kaynak geliştirilmiştir. İzinsiz ticari amaçla kullanılamaz.
