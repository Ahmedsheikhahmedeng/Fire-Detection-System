import { Fragment, useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./AwarenessSection.css";

gsap.registerPlugin(ScrollTrigger);

const sectionData = [
  {
    title: "Sessiz\nBaşlangıç",
    description:
      "Her büyük yangın önce görünmez bir işaretle başlar.\n\nOrman sakin görünse de sıcaklık artışı, düşük nem ve kuruyan bitki örtüsü riskin sessizce büyüdüğünü gösterir.",
    image: "/foto/nofire3.jpeg",
    services: [
      "Sıcaklık Artışı",
      "Düşük Nem",
      "Kurak Zemin",
      "Sessiz Risk",
      "İlk Sinyal",
      "Doğal Gerilim",
    ],
  },
  {
    title: "İlk\nKıvılcım",
    description:
      "Küçük bir kıvılcım, saniyeler içinde kontrol edilmesi zor bir süreci başlatabilir.\n\nBu ilk an, müdahalenin başarısını belirleyen en kritik eşiktir.",
    image: "/foto/aw-fire3.jpg",
    services: [
      "İlk Alev",
      "Kritik Eşik",
      "Anlık Tespit",
      "Hızlı Uyarı",
      "İlk Dakika",
      "Alarm Başlangıcı",
    ],
  },
  {
    title: "Hızlı\nYayılım",
    description:
      "Rüzgar ve düşük nem, yangının kısa sürede yön değiştirip yayılmasına neden olur.\n\nBu hızlı hareket, müdahale süresini daraltır.",
    image: "/foto/aw-nofire2.jpg",
    services: [
      "Rüzgar Gücü",
      "Yayılım Rotası",
      "Alan Büyümesi",
      "Hızlı Sıçrama",
      "Kritik Yayılım",
      "Sıcak Cephe",
    ],
  },
  {
    title: "Büyük\nYıkım",
    description:
      "Geç kalınan her saniye yalnızca ağaçları değil, toprağı, havayı ve canlı yaşamını da etkiler.\n\nYangının bıraktığı izler ekosistemde yıllarca hissedilir.",
    image: "/foto/aw-yanmis2.jpg",
    services: [
      "Habitat Kaybı",
      "Karbon Salımı",
      "Toprak Hasarı",
      "Hava Kirliliği",
      "Ekolojik Çöküş",
      "Uzun Etki",
    ],
  },
  {
    title: "Yeniden\nDoğuş",
    description:
      "Yangın sonrası doğa yeniden toparlanmaya çalışır; ancak bu süreç yıllar süren hassas bir iyileşme ister.\n\nKorunan her alan, geleceğe bırakılan en değerli mirastır.",
    image: "/foto/aw-hayvan1.jpg",
    services: [
      "Yeni Filizler",
      "Doğal Denge",
      "Toprak İyileşmesi",
      "Ekosistem Onarımı",
      "Uzun Süreç",
      "Umut",
    ],
  },
  {
    title: "Geleceği\nKoru",
    description:
      "Erken tespit teknolojileri yalnızca bugünün yangınlarını değil, yarının ormanlarını da korur.\n\nHer doğru alarm, ekosistemin sürdürülebilirliği için stratejik bir güvence sağlar.",
    image: "/foto/aw-hayvan2.jpg",
    services: [
      "AI İzleme",
      "Sürekli Koruma",
      "Gelecek Güvencesi",
      "Akıllı Alarm",
      "Önleyici Güç",
      "Sürdürülebilirlik",
    ],
  },
];

function CategorySection({ section, index }) {
  const titleLines = section.title.split("\n");
  const isVideo = section.image.endsWith(".mp4");

  return (
    <section
      data-snap-section
      className="aw-panel"
    >
      {/* Sol taraf */}
      <div className="aw-copy-shell">
        <div className="aw-title-lines">
          {titleLines.map((line, i) => (
            <h2 key={i} className="aw-text-effect" data-text-effect>
              {line}
              <span>{line}</span>
            </h2>
          ))}
        </div>

        <div className="aw-description">
          {section.description.split("\n\n").map((paragraph, i) => (
            <p key={i} className={i === 0 ? "aw-desc-main" : "aw-desc-sub"}>
              {paragraph}
            </p>
          ))}
        </div>
      </div>

      {/* Orta görsel */}
      <div className="aw-media-shell">
        <div data-media className="aw-media-frame">
          {isVideo ? (
            <video
              src={section.image}
              autoPlay
              loop
              muted
              playsInline
              className="h-full w-full object-cover"
            />
          ) : (
            <img
              src={section.image}
              alt={section.title}
              loading={index === 0 ? "eager" : "lazy"}
              decoding="async"
              className="h-full w-full object-cover"
            />
          )}
        </div>
      </div>

      {/* Sağ taraf */}
      <div className="aw-services-shell">
        <ul className="aw-services-list">
          {section.services.map((service, i) => (
            <li key={i}>{service}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default function AwarenessSection() {
  const mainRef = useRef(null);

  useEffect(() => {
    const root = mainRef.current;
    if (!root) return;

    const shouldReduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const isMobileScene = window.matchMedia("(max-width: 1023px)").matches;

    if (shouldReduceMotion) return;

    const ctx = gsap.context(() => {
      const sections = gsap.utils.toArray("[data-snap-section]", root);
      const medias = gsap.utils.toArray("[data-media]", root);
      const textEffects = gsap.utils.toArray("[data-text-effect]", root);

      textEffects.forEach((text) => {
        gsap.to(text, {
          backgroundPosition: "0% 0%",
          ease: "none",
          scrollTrigger: {
            trigger: text,
            start: "center 80%",
            end: "center 20%",
            scrub: isMobileScene ? 0.45 : true,
            invalidateOnRefresh: true,
          },
        });
      });

      if (isMobileScene) {
        medias.forEach((media, index) => {
          const isLast = index === medias.length - 1;

          gsap
            .timeline({
              scrollTrigger: {
                trigger: sections[index],
                start: "top 88%",
                end: isLast ? "bottom 52%" : "bottom 12%",
                scrub: 0.45,
                invalidateOnRefresh: true,
              },
            })
            .fromTo(
              media,
              { yPercent: -105, autoAlpha: 0.72, scale: 0.98 },
              {
                yPercent: 0,
                autoAlpha: 1,
                scale: 1,
                duration: 0.5,
                ease: "none",
              }
            )
            .to(media, {
              yPercent: isLast ? 0 : 105,
              autoAlpha: isLast ? 1 : 0.72,
              scale: isLast ? 1 : 0.98,
              duration: 0.5,
              ease: "none",
            });
        });

        ScrollTrigger.refresh();
        return;
      }

      medias.forEach((media, index) => {
        const isLast = index === medias.length - 1;

        gsap.fromTo(
          media,
          { y: "-100vh" },
          {
            y: isLast ? "0vh" : "100vh",
            ease: "none",
            scrollTrigger: {
              trigger: sections[index],
              start: "top bottom",
              end: isLast ? "bottom bottom" : "bottom top",
              scrub: true,
              invalidateOnRefresh: true,
            },
          }
        );
      });

      ScrollTrigger.create({
        trigger: root,
        start: "top top",
        end: "bottom bottom",
        refreshPriority: 8,
        invalidateOnRefresh: true,
        snap: {
          snapTo: (progress) => {
            const total = sections.length;
            const step = 1 / (total - 1);
            return gsap.utils.snap(step, progress);
          },
          duration: { min: 0.35, max: 0.75 },
          delay: 0.08,
          ease: "power2.inOut",
        },
      });

      ScrollTrigger.refresh();
    }, root);

    return () => ctx.revert();
  }, []);

  return (
    <section id="awareness" className="aw-main antialiased" ref={mainRef}>
      {sectionData.map((section, index) => (
        <Fragment key={index}>
          <CategorySection section={section} index={index} />
          {index < sectionData.length - 1 && <hr className="aw-divider" />}
        </Fragment>
      ))}
    </section>
  );
}
