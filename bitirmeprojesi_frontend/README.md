# 🔥 Yangın Tespit Sistemi - Frontend

Bu proje, uydu sıcak nokta verilerini (NASA FIRMS) ve meteorolojik bilgileri (OpenWeather) makine öğrenmesiyle analiz ederek yangın riskini erken ve erişilebilir şekilde tespit etmeyi amaçlayan sistemin **kullanıcı arayüzünü (Frontend)** oluşturur. 

Bu modern web uygulaması, kullanıcıların harita üzerinden canlı olarak riskli noktaları takip etmesini, anlık ML bazlı risk analiz raporlarını görmesini ve kritik bölgeler hakkında uyarılar almasını sağlar.

## 🌟 Öne Çıkan Özellikler

- **Anlık Harita ve İzleme:** NASA FIRMS verileri ile harmanlanmış ML (Makine Öğrenmesi) tahminlerinin canlı harita (Leaflet) üzerinde görüntülenmesi.
- **Dinamik Risk Alarmları:** Yüksek ve kritik risk taşıyan (örn. %85 üzeri yangın ihtimali) bölgeler için anlık olarak ekranda beliren bildirim afişleri.
- **Gelişmiş Animasyonlar:** GSAP ve ScrollTrigger kullanılarak hazırlanmış, video maskeleme içeren etkileyici paralaks (parallax) Hero ekranı.
- **Pürüzsüz Gezinme:** Lenis ile entegre edilmiş akıcı (smooth) sayfa kaydırma deneyimi.
- **Responsive Tasarım:** Tailwind CSS kullanılarak her cihaza (mobil, tablet, masaüstü) tam uyumlu, modern ve karanlık tema (dark mode) ağırlıklı tasarım.
- **Modüler Sayfa Yapısı:** Anasayfa, Risk Analizi (FireAnalysis) ve İzleme Merkezi (Monitoring) gibi ayrıştırılmış modüller.

## 🛠 Kullanılan Teknolojiler

- **Çatı (Framework):** React (v19) + Vite
- **Stil & Tasarım:** Tailwind CSS (v4), Vanilla CSS
- **Animasyon:** GSAP (ScrollTrigger), Framer Motion, Motion
- **Harita:** Leaflet, React-Leaflet
- **Grafikler & Veri Görselleştirme:** Recharts
- **HTTP İstemcisi:** Axios
- **İkonlar:** Lucide React
- **Scroll Yönetimi:** Lenis

## 📁 Proje Yapısı

```bash
src/
├── assets/         # Statik dosyalar, görseller ve ikonlar
├── components/     # Yeniden kullanılabilir UI bileşenleri (CreativeButton, FireMap, Menu, Footer vb.)
├── pages/          # Sayfa görünümleri ve bölümler
│   ├── AlertCenter/     # Bildirim ve uyarı kartları
│   ├── Awareness/       # Farkındalık bölümü
│   ├── FireAnalysis/    # Risk analiz ekranları
│   ├── FireDashboard/   # Sistem durumu ve son yangın istatistikleri
│   ├── Home/            # Paralaks efektli ana sayfa
│   └── Monitoring/      # Canlı harita ve alarm izleme arayüzü
├── services/       # API bağlantıları (Axios interceptors, baseURL ayarları vb.)
├── styles/         # Global ve yardımcı stil dosyaları
├── utils/          # Yardımcı fonksiyonlar
├── App.jsx         # Ana React yönlendirme (Router) ve yerleşimi
└── main.jsx        # React uygulamasının giriş noktası
```

## ⚙️ Kurulum ve Çalıştırma (Lokal)

Projeyi lokal bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

### Ön Koşullar
- Node.js (v20 veya üzeri önerilir)
- npm veya yarn

### 1. Bağımlılıkları Yükleyin
Proje klasörüne gidin ve paketleri indirin:
```bash
cd bitirmeprojesi_frontend
npm install
```

### 2. Çevre Değişkenlerini (Environment) Ayarlayın
`.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```
`.env` dosyasını açarak API bağlantı adresinizi güncelleyin:
```env
VITE_API_BASE_URL=http://localhost:8000
```
*(Eğer backend farklı bir portta çalışıyorsa, url adresini ona göre revize edin).*

### 3. Uygulamayı Başlatın
Geliştirme sunucusunu başlatmak için:
```bash
npm run dev
```
Uygulama varsayılan olarak `http://localhost:5173` adresinde çalışacaktır.

## 🐳 Docker ile Çalıştırma

Proje, production için Dockerize edilmiştir. Arka planda `Nginx` kullanarak optimize edilmiş statik dosyaları servis eder.

### Docker İmajını Oluşturma ve Başlatma
```bash
# Frontend dizinindeyken
docker build -t fire-detection-frontend .
docker run -d -p 8080:80 fire-detection-frontend
```

*Not: Uygulama tam yığın (full-stack) olarak bir üst dizindeki `docker-compose.yml` ve `docker-compose.prod.yml` üzerinden backend ile birlikte entegre çalışacak şekilde tasarlanmıştır.*

## 🔗 Sayfalar ve Yönlendirmeler

- `/` **(Home):** Projenin vizyonunu anlatan, GSAP tabanlı video scroll efektine sahip ana sayfa.
- `/analiz` **(Fire Analysis):** Makine öğrenmesi modeli tarafından üretilen güncel risk skorlarının ve hava durumu (FWI vb.) parametrelerinin detaylı incelendiği sayfa.
- `/izleme` **(Monitoring):** Leaflet haritası üzerinde `HIGH` ve `CRITICAL` seviyesindeki noktaların izlendiği, dinamik alarmların düştüğü canlı operasyon paneli.

## 📜 Lisans ve İletişim

Bu proje açık kaynak kodludur ve akademik bir bitirme projesi olarak geliştirilmiştir. İzinsiz ticari amaçla kullanılamaz. Katkıda bulunmak veya sorularınız için proje sahipleriyle iletişime geçebilirsiniz.
