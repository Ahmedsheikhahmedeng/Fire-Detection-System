import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import "./Home.css";

import CreativeButton from "../../components/CreativeButton/CreativeButton";

gsap.registerPlugin(ScrollTrigger);

const AwarenessSection = lazy(() => import("../Awareness/AwarenessSection"));
const NotificationCards = lazy(() => import("../AlertCenter/NotificationCards"));
const HowItWorksSection = lazy(() => import("../HowItWorks/HowItWorksSection"));

function DeferredHomeSections() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let timeoutId;
    let done = false;

    const load = () => {
      if (done) return;
      done = true;
      setIsReady(true);
    };

    const onScrollIntent = () => load();
    window.addEventListener("wheel", onScrollIntent, { once: true, passive: true });
    window.addEventListener("touchmove", onScrollIntent, { once: true, passive: true });
    window.addEventListener("keydown", onScrollIntent, { once: true });

    timeoutId = window.setTimeout(load, 12000);

    return () => {
      done = true;
      window.removeEventListener("wheel", onScrollIntent);
      window.removeEventListener("touchmove", onScrollIntent);
      window.removeEventListener("keydown", onScrollIntent);
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, []);

  if (!isReady) return null;

  return (
    <Suspense fallback={null}>
      <AwarenessSection />
      <NotificationCards />
      <HowItWorksSection />
    </Suspense>
  );
}

export default function Home() {
  const navigate = useNavigate();

  const containerRef = useRef(null);
  const heroVideoRef = useRef(null);
  const heroMaskRef = useRef(null);
  const heroGridOverlayRef = useRef(null);
  const marker1Ref = useRef(null);
  const marker2Ref = useRef(null);
  const heroContentRef = useRef(null);
  const progressBarRef = useRef(null);

  useGSAP(
    () => {
      const heroContent = heroContentRef.current;
      const heroMask = heroMaskRef.current;
      const heroGridOverlay = heroGridOverlayRef.current;
      const progressBar = progressBarRef.current;
      const marker1 = marker1Ref.current;
      const marker2 = marker2Ref.current;
      const heroVideo = heroVideoRef.current;
      const heroParallax = containerRef.current?.querySelector(".hero-parallax");

      if (
        !heroContent ||
        !heroMask ||
        !heroGridOverlay ||
        !progressBar ||
        !marker1 ||
        !marker2 ||
        !heroVideo ||
        !heroParallax
      ) {
        return;
      }

      let heroContentMoveDistance = 0;

      const clamp01 = (value) => Math.max(0, Math.min(1, value));
      const smoothStep = (value) => value * value * (3 - 2 * value);
      const progressBetween = (progress, start, end) => {
        if (end <= start) return 0;
        return clamp01((progress - start) / (end - start));
      };

      const updateMeasurements = () => {
        const viewportHeight =
          window.visualViewport?.height || window.innerHeight;
        heroContentMoveDistance = Math.max(
          heroContent.scrollHeight - viewportHeight,
          0
        );
      };

      gsap.set(heroVideo, { opacity: 1, yPercent: 0, scale: 1.04 });
      gsap.set(heroMask, {
        opacity: 0,
        scale: 2.15,
        visibility: "hidden",
      });
      gsap.set(heroGridOverlay, { opacity: 0 });
      gsap.set([marker1, marker2], { opacity: 0, yPercent: 14 });
      gsap.set(progressBar, { "--progress": 0 });

      updateMeasurements();

      const onRefreshInit = () => {
        updateMeasurements();
      };

      ScrollTrigger.addEventListener("refreshInit", onRefreshInit);

      const trigger = ScrollTrigger.create({
        trigger: heroParallax,
        start: "top top",
        end: () =>
          `+=${window.innerHeight * (window.matchMedia("(max-width: 800px)").matches ? 3.4 : 4)}`,
        pin: true,
        pinSpacing: true,
        scrub: 0.65,
        anticipatePin: 1,
        invalidateOnRefresh: true,
        refreshPriority: 10,
        onUpdate: (self) => {
          const p = self.progress;

          gsap.set(progressBar, { "--progress": p });
          gsap.set(heroContent, { y: -p * heroContentMoveDistance });

          // Video hareketi kapalı: Home sayfasındaki scroll kasmasını azaltır.
          // Görsel aynı kalır; sadece videonun scroll ile yukarı/zoom hareketi durur.

          const maskIn = smoothStep(progressBetween(p, 0.42, 0.52));
          const maskOut = smoothStep(progressBetween(p, 0.76, 0.86));
          const maskOpacity = clamp01(maskIn - maskOut);
          const maskScale = 2.15 - maskIn * 1.15 + maskOut * 1.3;

          gsap.set(heroMask, {
            opacity: maskOpacity,
            scale: maskScale,
            visibility: maskOpacity < 0.01 ? "hidden" : "visible",
          });

          const gridIn = smoothStep(progressBetween(p, 0.5, 0.58));
          const gridOut = smoothStep(progressBetween(p, 0.72, 0.82));
          const gridOpacity = clamp01(gridIn - gridOut);

          gsap.set(heroGridOverlay, {
            opacity: gridOpacity,
          });

          const marker1In = smoothStep(progressBetween(p, 0.54, 0.6));
          const marker1Out = smoothStep(progressBetween(p, 0.72, 0.78));
          const marker1Opacity = clamp01(marker1In - marker1Out);

          const marker2In = smoothStep(progressBetween(p, 0.58, 0.64));
          const marker2Out = smoothStep(progressBetween(p, 0.72, 0.78));
          const marker2Opacity = clamp01(marker2In - marker2Out);

          gsap.set(marker1, {
            opacity: marker1Opacity,
            yPercent: (1 - marker1Opacity) * 14,
          });

          gsap.set(marker2, {
            opacity: marker2Opacity,
            yPercent: (1 - marker2Opacity) * 14,
          });
        },
      });

      ScrollTrigger.refresh();

      return () => {
        ScrollTrigger.removeEventListener("refreshInit", onRefreshInit);
        trigger.kill();
      };
    },
    { scope: containerRef }
  );

  return (
    <div className="home-page-wrapper" id="Home">
      <div className="home-container" ref={containerRef}>
        <section className="hero-parallax">
          <div className="hero-img">
            <video
              ref={heroVideoRef}
              className="hero-media hero-scrub-video"
              muted
              playsInline
              preload="metadata"
              autoPlay
              loop
              poster="/foto/home-hero-poster.png"
              src="/videos/14296625_3840_2160_24fps.mp4"
            />
          </div>

          <div className="hero-mask" ref={heroMaskRef} />

          <div className="hero-grid-overlay" ref={heroGridOverlayRef}>
            <img src="/grid-overlay.svg" alt="" />
          </div>

          <div className="marker marker-1" ref={marker1Ref}>
            <span className="marker-icon" />
            <p className="marker-label">Kritik Isı Artışı</p>
          </div>

          <div className="marker marker-2" ref={marker2Ref}>
            <span className="marker-icon" />
            <p className="marker-label">Yüksek Risk Alanı</p>
          </div>

          <div className="hero-content" ref={heroContentRef}>
            <div className="hero-content-block">
              <div className="hero-content-copy">
                <h1>Yangın Tespit Sistemi</h1>
                <p>
                  Bu proje, uydu sıcak nokta verileri ve meteorolojik bilgileri
                  makine öğrenmesiyle analiz ederek yangın riskini erken ve
                  erişilebilir şekilde tespit etmeyi amaçlar.
                </p>

                <div className="parallax-hero-buttons">
                  <CreativeButton
                    className="hero-analiz-btn"
                    onClick={() => navigate("/analiz")}
                  >
                    Canlı İzleme
                  </CreativeButton>
                </div>
              </div>
            </div>

            <div className="hero-content-block">
              <div className="hero-content-copy">
                <h2>Geç ve Eksik Yangın Tespiti</h2>
                <p>
                  Orman yangınları çoğu zaman duman, alev veya insan bildirimi sonrası fark edilir. Bu durum erken müdahaleyi zorlaştırır.
                </p>
              </div>
            </div>

            <div className="hero-content-block">
              <div className="hero-content-copy">
                <h2>Mevcut Sistemlerin Sınırlılığı</h2>
                <p>
                  Dronlar, kameralar ve ısı algılama cihazları yangın izleme sürecinde etkili olsa da maliyetli olabilir ve geniş alanlarda yetersiz kalabilir. Ayrıca bu sistemler her sıcak noktayı, geçmiş yangın verilerini ve son günlerdeki sıcaklık-nem değişimlerini birlikte değerlendiremeyebilir.
                </p>
              </div>
            </div>

            <div className="hero-content-block">
              <div className="hero-content-copy">
                <h2>Anlık Harita ve Uyarı Sistemi</h2>
                <p>
                  Uydu verileri sayesinde yangın riski taşıyan bölgeler 24 saat kesintisiz olarak izlenir. Riskli noktalar herkese açık canlı harita üzerinde koordinat bilgileriyle gösterilir ve yüksek risk durumlarında kullanıcıya anlık bildirim gönderilir.
                </p>

                <CreativeButton
                  className="hero-analiz-btn"
                  onClick={() => navigate("/analiz")}
                >
                  Risk Analizi
                </CreativeButton>
              </div>
            </div>
          </div>

          <div className="hero-scroll-progress-bar" ref={progressBarRef} />
        </section>

        <DeferredHomeSections />
      </div>
    </div>
  );
}
