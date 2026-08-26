<div align="center">
  <img src="logo.png" alt="Fire Detection Logo" width="200" />
  
  # 🔥 Yangın Tespit Sistemi (Fire Detection System)
  
  **NASA FIRMS Uydu Verileri ve Makine Öğrenmesi (ML) Destekli, Eş Zamanlı Orman Yangını Erken Uyarı ve Risk İzleme Sistemi**

  [![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
  [![XGBoost](https://img.shields.io/badge/ML-XGBoost%20%7C%20LightGBM-FF9900)](https://xgboost.readthedocs.io/)
</div>

---

## 📖 Proje Hakkında

Bu proje, orman yangınlarının yıkıcı etkilerini en aza indirmek ve erken müdahale imkanı sunmak amacıyla tasarlanmış **kapsamlı bir akademik bitirme projesidir**. Sistem uçtan uca çalışarak; NASA'nın sunduğu uydu (FIRMS) sıcak nokta (hotspot) verilerini toplar, anlık hava durumu ve Orman Yangını Tehlike Endeksi (FWI) parametreleriyle zenginleştirir. Elde edilen veri setini gelişmiş **Makine Öğrenmesi (ML)** algoritmalarından geçirerek bölgesel yangın olasılıklarını hesaplar.

Çıkan risk sonuçları, kullanıcı dostu modern bir web arayüzünde canlı harita üzerinde (Leaflet) gösterilir ve kritik tehlike seviyesine sahip noktalar için sistem tarafından **dinamik alarmlar** üretilir.

---

## ✨ Temel Özellikler

- 🛰️ **Canlı Uydu Entegrasyonu:** NASA FIRMS API üzerinden periyodik olarak hotspot (sıcak nokta) verilerinin çekilmesi.
- 🌦️ **Meteorolojik Analiz:** Open-Meteo verileri ile anlık hava durumu ve FWI (Fire Weather Index) hesaplaması.
- 🧠 **Gelişmiş Makine Öğrenmesi:** XGBoost, LightGBM, CatBoost ve Random Forest modelleriyle ensemble (topluluk) risk analizi.
- 🗺️ **Gerçek Zamanlı İzleme:** React ve Leaflet tabanlı, GSAP animasyonlarıyla güçlendirilmiş modern harita arayüzü.
- ⏱️ **Otomatize Görevler:** APScheduler tabanlı Worker mimarisi ile düzenli periyodik veri güncellemeleri.
- 🚨 **Dinamik Uyarı Sistemi:** Yüksek risk barındıran sıcak noktalar için otomatik alarm üretimi ve yönetimi.
- 🐳 **Tam Konteynerizasyon:** Docker ve Docker Compose ile "Development" ve "Production" ortamlarının ayrıştırılması.

---

## 🧩 Sistem Mimarisi ve Teknolojiler

Proje, tam yığın (full-stack) mimari standartlarında, mikroservis mantığına yakın modüler bir yapıda geliştirilmiştir:

### 1. [Frontend (Arayüz Katmanı)](bitirmeprojesi_frontend/README.md)
Kullanıcıların canlı harita üzerinden risk analizi yapabildiği, görselleştirilmiş istatistikleri ve alarmları takip edebildiği modern önyüz.
- **Çatı:** React (v19) & Vite (v7)
- **Stil & Animasyon:** Tailwind CSS v4, GSAP, Framer Motion
- **Harita & Grafik:** Leaflet, React-Leaflet, Recharts
- **Ağ İstekleri:** Axios, React Router v7

### 2. [Backend (Arka Plan Katmanı)](fire-detection-backend/README.md)
Veri toplama, orkestrasyon, veritabanı yönetimi ve ML modellerinin (Inference) çalıştırıldığı API ve Worker servisi.
- **Çatı:** Python (3.11+), FastAPI, Uvicorn
- **Veritabanı & ORM:** PostgreSQL, SQLAlchemy, Alembic
- **Makine Öğrenmesi:** Scikit-learn, XGBoost, LightGBM, CatBoost, Pandas, Numpy
- **Zamanlanmış Görevler:** APScheduler

---

## 🚀 Hızlı Başlangıç (Docker ile Kurulum)

Projeyi bilgisayarınızda tüm bileşenleriyle (Backend, Frontend, Veritabanı) ayağa kaldırmanın en kolay yolu **Docker Compose** kullanmaktır.

### Ön Koşullar
- Bilgisayarınızda [Docker](https://www.docker.com/) ve [Docker Compose](https://docs.docker.com/compose/) yüklü olmalıdır.

### 1. Depoyu Klonlayın
```bash
git clone https://github.com/kullaniciadi/bitirmeprojesifull.git
cd bitirmeprojesifull
```

### 2. Çevre Değişkenlerini (Environment Variables) Ayarlayın
Projenin çalışması için backend klasöründe `.env` dosyasını oluşturmalısınız.
```bash
cd fire-detection-backend
cp .env.example .env
```
`.env` dosyasını bir metin editörü ile açın ve gerekli keyleri doldurun:
- `DB_PASSWORD`: PostgreSQL veritabanı şifreniz.
- `API_KEY`: API isteklerini korumak için belirleyeceğiniz özel şifre.
- `NASA_API_KEY`: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) API Anahtarınız.
- `OPENWEATHER_API_KEY`: Hava durumu verileri için API anahtarınız (kullanılıyorsa).

### 3. Geliştirme (Development) Modunda Başlatın
Aynı `fire-detection-backend` dizini altındayken tüm servisleri başlatın:
```bash
docker compose -p fire-dev up -d --build
```
Bu komut sonrası sistem ayağa kalkacaktır:
- 🌐 **Frontend Arayüzü:** [http://localhost:5173](http://localhost:5173)
- ⚙️ **Backend API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🗄️ **PostgreSQL:** `localhost:5432`

**Not:** Arka planda periyodik veri çeken zamanlayıcıyı (scheduler) aktif etmek için:
```bash
docker compose -p fire-dev --profile scheduler up -d --build
```

---

## ⚙️ Production (Canlı) Dağıtım

Sistem canlı ortama alınırken (production) güvenlik ve performans artışı için ayrı bir konfigürasyona sahiptir. Frontend Nginx ile servis edilir ve Backend `reload` özelliği kapatılarak çalışır.

1. `fire-detection-backend` klasörüne gidin:
```bash
cd fire-detection-backend
cp .env.production.example .env.production
```
2. `.env.production` içerisine gerçek sunucu URL'lerinizi (`FRONTEND_URL`, `VITE_API_BASE_URL` vb.) girin.
3. Production versiyonunu başlatın:
```bash
docker compose -p fire-prod --env-file .env.production -f docker-compose.prod.yml up -d --build
```

---

## 📁 Ana Dizin (Root) Yapısı

```text
bitirmeprojesifull/
├── bitirmeprojesi_frontend/   # React & Vite tabanlı İstemci (Client) Projesi
├── fire-detection-backend/    # FastAPI, PostgreSQL & ML API Sunucusu
├── docker-compose.prod.yml    # Production (Canlı) ortam Docker Compose konfigürasyonu
├── TESLIM_DOKUMANTASYONU.md   # Proje final teslim detayları ve teknik operasyon notları
├── start.sh                   # Genel proje başlatıcı betiği
└── README.md                  # Ana proje dökümantasyonu (Görüntülediğiniz dosya)
```

*(Detaylı ML pipeline süreçleri, model artifact kuralları ve frontend/backend detayları için klasörlerin içerisindeki README ve dokümanları inceleyebilirsiniz.)*

---

## 📊 Örnek API Endpointleri

API, Swagger UI (OpenAPI) üzerinden otomatik dokümante edilir (`/docs`). Öne çıkan bazı endpointler:
- `GET /health` - Servislerin genel durumunu (DB, ML, Scheduler) gösterir.
- `GET /map/hotspots` - Haritada gösterilecek mevcut yangın noktalarını getirir.
- `POST /nasa/fetch-hotspots` - NASA'dan anlık veri çeker (API Key gerektirir).
- `GET /alerts/active` - Sistemdeki mevcut aktif alarmları listeler.
- `POST /api/ml/predict-hotspot` - Verilen nokta için anlık ML risk tahmini yapar.

---

## 📝 Testler

Projenin güvenilirliğini sağlamak amacıyla detaylı test senaryoları yazılmıştır.
Backend testlerini (Pytest) çalıştırmak için:
```bash
cd fire-detection-backend
export TEST_DATABASE_URL="postgresql://kullanici:sifre@localhost:5432/test_db_adi"
pytest
```
*(Proje tesliminde tüm resmi 141+ testin başarıyla geçtiği doğrulanmıştır).*

---

## 📜 Lisans & Uyarılar

- Bu proje açık kaynak kodlu, **akademik bir bitirme çalışması** olarak geliştirilmiştir.
- Modeller (`.joblib`) yüksek boyutlu olduğundan repo içerisine dahil edilmemiştir; çalışma zamanında (runtime) veya dağıtım öncesi `aimodel/` veya ilgili Artifact klasörlerine eklenmesi gerekmektedir.
- İzinsiz ticari amaçla kullanılamaz. Katkıda bulunmak veya sorularınız için Github Issues üzerinden iletişime geçebilirsiniz.
