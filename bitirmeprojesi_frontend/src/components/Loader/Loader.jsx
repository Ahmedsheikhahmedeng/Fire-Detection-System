import { useCallback, useEffect, useMemo, useRef, useState } from "react"; 
import gsap from "gsap"; 
import "./Loader.css"; 

const TEXTS = [
  "UYDU BAGLANIYOR........", 
  "VERI AKISI BASLATILIYOR.......", 
  "SICAK NOKTALAR TESPIT EDILIYOR......", 
  "KOORDINATLAR ISLENIYOR.....", 
  "HAVA DURUMU ANALIZ EDILIYOR....", 
  "AI MODEL CALISIYOR...",
  "RISK HESAPLANIYOR..", 
  "SISTEM HAZIR.", 
];

export default function LoadingFire({ onFinish, durationMs = 3200 }) {
    
  const rootRef = useRef(null); // Ana kapsayıcı <div>'in DOM referansını tutar (GSAP için)
  const textWrapRef = useRef(null); // Metinleri saran kapsayıcının DOM referansını tutar
  const counterRef = useRef(null);
  const finishRef = useRef(onFinish);
  const finalStartedRef = useRef(false);
  const timelineRef = useRef(null);

  const [progress, setProgress] = useState(0); // Metin değişimi için seyrek güncellenen progress değeri
  const [isFinal, setIsFinal] = useState(false); // Son animasyonun başlayıp başlamadığını izleyen state

  useEffect(() => {
    finishRef.current = onFinish;
  }, [onFinish]);

  // progress değerine göre gösterilecek metnin indeksini hesaplar (performans için useMemo ile önbelleklenir)
  const textIndex = useMemo(() => {
    // progress'in yüzdelik dilimine göre TEXTS dizisinden oransal olarak bir indeks seçer
    return Math.min(TEXTS.length - 1, Math.floor((progress / 100) * TEXTS.length));
  }, [progress]); // Sadece progress değiştiğinde yeniden hesaplanır

  // Şu anki metin dizinin son elemanı mı diye kontrol eder
  const isLastSentence = textIndex === TEXTS.length - 1; 

  const completeLoading = useCallback(() => {
    finishRef.current?.();
  }, []);

  // --- METİN DEĞİŞİM ANİMASYONU ---
  useEffect(() => {
    const wrap = textWrapRef.current; // DOM elemanına eriş
    if (!wrap) return; // Eleman henüz render olmadıysa iptal et

    const letters = wrap.querySelectorAll(".letter"); // DOM'daki tüm harf span'lerini seç
    if (!letters.length) return;

    // GSAP reset işlemi: Önceki animasyonlardan kalan inline stilleri ve transformları temizle
    gsap.set(letters, {
      clearProps: "all", 
      opacity: 1, x: 0, y: 0, z: 0, rotateX: 0, rotateY: 0, rotateZ: 0, scale: 1, filter: "blur(0px)",
    });

    // Yeni metin geldiğinde harfleri aşağıdan (y:12, opacity:0) normal konuma doğru sırayla (stagger) canlandır
    gsap.fromTo(
      letters,
      { y: 12, opacity: 0 }, // Başlangıç durumu
      { y: 0, opacity: 1, duration: 0.35, stagger: 0.012, ease: "power2.out" } // Bitiş durumu ve zamanlama ayarları
    );
  }, [textIndex]); // Bu efekt SADECE metin (textIndex) değiştiğinde tetiklenir

  // --- ANA PROGRESS DÖNGÜSÜ VE FİNAL ANİMASYONU ---
  useEffect(() => {
    const root = rootRef.current; // Ana kapsayıcı DOM elemanı
    if (!root) return;

    // Bileşen ilk yüklendiğinde tüm ekranı yumuşakça (fade-in) görünür yap
    gsap.fromTo(root, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power2.out" });

    const start = performance.now(); // Animasyonun başladığı anın milisaniye cinsinden tam zamanı
    let raf = 0; // requestAnimationFrame ID'sini tutacak değişken (iptal etmek için)
    let lastProgress = -1;
    let lastTextIndex = -1;

    const fallbackTimer = window.setTimeout(() => {
      if (!finalStartedRef.current) completeLoading();
    }, durationMs + 1800);

    // Tarayıcının her boyama (paint) işleminde çağrılacak olan döngü fonksiyonu
    const tick = (t) => {
      const p = Math.min(1, (t - start) / durationMs); // Geçen sürenin toplam süreye oranı (0.0 ile 1.0 arası)
      const eased = 1 - Math.pow(1 - p, 3); // Dümdüz artmak yerine başta hızlı, sona doğru yavaşlayan matematiksel easing (cubic out)
      const val = Math.round(eased * 100); // Oranı 0-100 arası tam sayıya çevir

      if (val !== lastProgress) {
        lastProgress = val;
        if (counterRef.current) {
          counterRef.current.textContent = String(val).padStart(3, "0");
        }
      }

      const nextTextIndex = Math.min(TEXTS.length - 1, Math.floor((val / 100) * TEXTS.length));
      if (nextTextIndex !== lastTextIndex) {
        lastTextIndex = nextTextIndex;
        setProgress(val);
      }

      if (val > 85) root.classList.add("hot"); // İlerleme %85'i geçince DOM'a 'hot' class'ı ekle (muhtemelen CSS'te kırmızılığı artırıyor)

      if (p < 1) { // Süre henüz dolmadıysa...
        raf = requestAnimationFrame(tick); // Döngüyü bir sonraki frame için tekrar çağır
        return; // Fonksiyondan çık
      }

      // --- SÜRE DOLDU, FİNAL SAHNESİ BAŞLIYOR ---
      if (finalStartedRef.current) return; // Zaten final sahnesi başladıysa tekrar girme
      finalStartedRef.current = true; // Bayrağı kaldır

      const wrap = textWrapRef.current;
      const letters = wrap?.querySelectorAll(".letter") || []; // Son cümlenin harflerini DOM'dan seç
      const smoke = root.querySelector(".lf-smoke");
      const fullcover = root.querySelector(".fullcover");
      const counter = root.querySelector(".lf-counterCorner");
      const loader = root.querySelector(".loader");

      setIsFinal(true); // Final state'ini true yap (CSS sınıfları için)

      // GSAP Timeline oluştur (animasyonları sırayla/birlikte oynatmak için)
      const tl = gsap.timeline({ defaults: { ease: "power3.inOut" } });
      timelineRef.current = tl;

      if (letters.length) {
        // Adım 1: Harfler hafifçe titrer/şarj olur (sinematik etki için küçük rastgele hareketler)
        tl.to(letters, {
          y: () => gsap.utils.random(-6, 6), x: () => gsap.utils.random(-6, 6), rotateZ: () => gsap.utils.random(-6, 6),
          duration: 0.12, stagger: 0.002, ease: "power1.inOut",
        });

        // Adım 2: Harfler 3D uzayda patlayarak dağılır ve düşer
        tl.to(
          letters,
          {
            x: () => gsap.utils.random(-260, 260), // X ekseninde rastgele saçıl
            y: () => gsap.utils.random(240, 560),  // Y ekseninde aşağı düşüş
            z: () => gsap.utils.random(-280, 320), // Z ekseninde (derinlik) dağılma
            rotateX: () => gsap.utils.random(-520, 520), rotateY: () => gsap.utils.random(-520, 520), rotateZ: () => gsap.utils.random(-520, 520), // Kendi etrafında fırıl fırıl dönme
            scale: () => gsap.utils.random(0.6, 1.18), opacity: 0, filter: "blur(2px)", // Boyut değişimi, şeffaflaşma ve bulanıklaşma
            duration: 0.55, stagger: { each: 0.008, from: "random" }, ease: "power3.in",
          },
          0.02 // Timeline başladıktan 0.02 saniye sonra bu animasyona başla
        );
      }

      // Adım 3: Dumanı (.lf-smoke) aniden görünür yap
      if (smoke) {
        tl.to(smoke, { opacity: 1, duration: 0.08, ease: "power1.out" }, 0.08);
      }

      // Adım 4: Ekranı tamamen kaplayan efekti tetikle ve bileşeni sonlandır
      if (fullcover) {
        tl.to(fullcover, { opacity: 1, duration: 0.05, ease: "power1.out" }, 0.16) // Parlamayı görünür yap
          .to(fullcover, { scale: 70, duration: 0.62, ease: "power2.inOut" }, 0.2); // Parlamayı tüm ekranı kaplayacak kadar büyüt
      }

      if (counter) {
        tl.to(counter, { y: 10, opacity: 0, duration: 0.18, ease: "power2.inOut" }, 0.22); // Sayacı aşağı kaydırıp sakla
      }

      if (loader) {
        tl.to(loader, { scale: 1.08, duration: 0.18, ease: "power2.out" }, 0.16); // Ortadaki yuvayı hafifçe büyüt
      }

      tl.to(
        root,
        {
          opacity: 0, duration: 0.26, ease: "power2.inOut", // En dış kapsayıcıyı tamamen şeffaf yap
          onComplete: completeLoading, // Tüm timeline bitince ebeveyn bileşene işin bittiğini haber ver
        },
        0.62 // Bu adımı timeline'ın 0.62'nci saniyesinde başlat
      );
    };

    raf = requestAnimationFrame(tick); // Döngüyü başlat
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(fallbackTimer);
      timelineRef.current?.kill();
      gsap.killTweensOf(root);
    }; // Bileşen domdan silinirse (unmount) hafıza sızıntısını önlemek için frame döngüsünü temizle
  }, [completeLoading, durationMs]); // Sadece bu bağımlılıklar değişirse efekti yeniden yarat

  // Metni harf harf bölen ve her birini bir <span> içine koyan yardımcı fonksiyon
  const renderLetters = (text) =>
    (text ?? "").split("").map((ch, i) => (
      <span key={`${text}-${i}`} className="letter">
        {ch === " " ? "\u00A0" : ch} {/* Boşluk karakterlerini HTML boşluk entitisine çevir (CSS'te düzgün durması için) */}
      </span>
    ));

  return (
    <div // Ana kapsayıcı. Duruma göre dinamik class'lar alır.
      className={[
        "lf-root",
        progress > 85 ? "hot" : "", // Sayac %85'ten büyükse 'hot' sınıfını ekle
        isFinal && isLastSentence ? "final" : "", // Animasyon bittiyse 'final' sınıfını ekle
      ].join(" ")} // Dizi içindeki class'ları boşlukla birleştirerek string yapar
      ref={rootRef} // GSAP animasyonları için root referansı
    >
      {/* CSS animasyonlarıyla çalışan arkaplan atmosfer katmanları */}
      <div className="fire-bg" aria-hidden="true" />
      <div className="embers" aria-hidden="true" />
      <div className="heat-haze" aria-hidden="true" />

      {/* Sadece final sahnesinde Timeline ile opaklığı artırılan duman katmanları */}
      <div className="lf-smoke" aria-hidden="true">
        <span className="sm s1" />
        <span className="sm s2" />
        <span className="sm s3" />
        <span className="sm s4" />
        <span className="sm s5" />
      </div>

      {/* Ekran kapanışı/parlaması için kullanılan, normalde gizli katman */}
      <div className="fullcover" aria-hidden="true" />

      {/* Merkezdeki görsel yapı (Kara delik ve Metinler) */}
      <div className="lf-center" aria-hidden="true">
        <div className="loader">
          <div className="blackhole">
            <div className="blackhole-circle"></div>
            <div className="blackhole-disc"></div>
          </div>

          {/* Dinamik olarak güncellenen harflerin render edildiği alan */}
          <div className="curve-text" ref={textWrapRef}>
            {renderLetters(TEXTS[textIndex])}
          </div>
        </div>
      </div>

      {/* Ekranın köşesindeki sayaç (0-100 değerini 3 haneli formatta gösterir örn: 005, 085, 100) */}
      <div className="lf-counterCorner" ref={counterRef}>000</div>
    </div>
  );
}
