import React, { useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import './HowItWorksSection.css';
import ParallaxScroll from '../../components/ParallaxScroll/ParallaxScroll';

gsap.registerPlugin(ScrollTrigger);

const HowItWorksSection = () => {
    const sectionRef = useRef(null);
    const pathRef = useRef(null);
    const containerRef = useRef(null);

    useGSAP(() => {
        const path = pathRef.current;
        if (!path) return;

        const pathLength = path.getTotalLength();
        const mm = gsap.matchMedia();

        mm.add("(prefers-reduced-motion: no-preference)", () => {
            const isMobile = window.matchMedia("(max-width: 768px)").matches;

            // Squiggle Animasyonu
            gsap.set(path, {
                strokeDasharray: pathLength,
                strokeDashoffset: pathLength
            });

            gsap.to(path, {
                strokeDashoffset: 0,
                ease: "none",
                scrollTrigger: {
                    trigger: sectionRef.current,
                    start: isMobile ? "top 78%" : "top center",
                    end: isMobile ? "bottom 35%" : "bottom center",
                    scrub: isMobile ? 0.65 : 0.5,
                    invalidateOnRefresh: true,
                    refreshPriority: 4
                }
            });
        });

        mm.add("(prefers-reduced-motion: reduce)", () => {
            gsap.set(path, {
                strokeDasharray: "none",
                strokeDashoffset: 0
            });
        });

        return () => mm.revert();
    }, { scope: sectionRef });

    return (
        <section className="how-it-works-wrapper" id="how" ref={sectionRef}>
            <div className="dancehaus-content" ref={containerRef}>
                <header className="how-header">
                    <h1 className="how-text-effect-h1" style={{ position: 'relative', zIndex: 10 }}>NASIL ÇALIŞIR</h1>
                </header>

                {/* 1. Aşama */}
                <ParallaxScroll 
                    title1="SÜREKLİ"
                    title2="GÖZETİM"
                    word="KESİNTİSİZ UYDU İSTİHBARATI"
                    imagesProp={[
                        "/foto/buyuk1.png",
                        "/foto/orta1.png",
                        "/foto/kucuk1.png"
                    ]}
                    description="Sistem, NASA FIRMS üzerinden VIIRS SNPP, NOAA-20 ve NOAA-21 kaynaklarından gelen sıcak nokta kayıtlarını düzenli olarak çeker. Her kayıt koordinat, gözlem zamanı, parlaklık ve kaynak bilgisiyle birlikte backend tarafında işlenir ve PostgreSQL veritabanına kaydedilir."
                />

                {/* 2. Aşama */}
                <ParallaxScroll 
                    title1="AKILLI"
                    title2="RİSK MOTORU"
                    word="SANİYELER İÇİNDE KARAR"
                    imagesProp={[
                        "/foto/buyuk2.png",
                        "/foto/orta2.png",
                        "/foto/kucuk2.png"
                    ]}
                    description="Kaydedilen her sıcak nokta için hava durumu verileri hazırlanır; sıcaklık, nem, rüzgar ve uydu gözlem özellikleri makine öğrenmesi modeline gönderilir. Model bu verilerden yangın olasılığı üretir, risk seviyesini belirler ve yakın sıcak noktaları yangın kümesi mantığıyla takip eder."
                />

                {/* 3. Aşama */}
                <ParallaxScroll 
                    title1="CANLI"
                    title2="MÜDAHALE"
                    word="REFRESH OLMADAN GÜNCEL"
                    imagesProp={[
                        "/foto/buyuk3.png",
                        "/foto/orta3.png",
                        "/foto/kucuk3.png"
                    ]}
                    description="Risk sonucu yüksek çıkan kayıtlar için alarm oluşturulur ve canlı harita üzerinde ilgili nokta güncellenir. Frontend, backend API ve WebSocket akışıyla yeni sıcak noktaları, aktif alarmları, küme durumlarını ve analiz panelindeki sayıları sayfa yenilemeden kullanıcıya gösterir."
                />

                <svg
                    width="100%"
                    height="100%"
                    viewBox="0 0 1350 2995"
                    preserveAspectRatio="none"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    className="squiggle"
                >
                    <path
                        ref={pathRef}
                        d="M1349.62 0.490112C1349.62 0.490112 765.558 110.365 601.12 397.49C318.149 891.588 633.535 1477.51 1004.62 782.49C1375.71 87.4701 203.027 684.159 17.6203 1252.99C-165.894 1816.01 1185.92 1259.8 1209.12 1394.49C1271.88 1758.75 -73.8797 1600.99 17.6203 2083.99C109.12 2566.99 1418.93 1974.6 1279.62 2670.49C1225.55 2940.58 653.12 2994.49 653.12 2994.49"
                        stroke="var(--brand-crimson)"
                        strokeWidth="50"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                    />
                </svg>
            </div>
        </section>
    );
};

export default HowItWorksSection;
