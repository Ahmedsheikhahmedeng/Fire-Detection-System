import React, { useRef, useState } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import { api } from '../../services/api';
import './NotificationCards.css';

gsap.registerPlugin(ScrollTrigger);

const TELEGRAM_BOT_URL = "https://t.me/yanginizle_bot";

const NotificationCards = () => {
    const containerRef = useRef(null);
    const progressBarRef = useRef(null);
    const isDev = import.meta.env.DEV;
    const [emailAddress, setEmailAddress] = useState('');
    const [emailStatus, setEmailStatus] = useState({ type: 'idle', message: '' });
    const [isEmailSending, setIsEmailSending] = useState(false);
    const [smsPhone, setSmsPhone] = useState('');
    const [smsStatus, setSmsStatus] = useState({ type: 'idle', message: '' });
    const [isSmsSending, setIsSmsSending] = useState(false);

    const handleSmsSubmit = async (event) => {
        event.preventDefault();

        const normalizedPhone = smsPhone.trim();
        if (!normalizedPhone) {
            setSmsStatus({ type: 'error', message: 'Telefon numarası girin.' });
            return;
        }

        setIsSmsSending(true);
        setSmsStatus({ type: 'idle', message: '' });

        try {
            await api.subscribeSms(normalizedPhone);
            setSmsStatus({ type: 'success', message: 'SMS bildirimi aktif edildi.' });
        } catch (error) {
            setSmsStatus({
                type: 'error',
                message: error.message || 'SMS gönderilemedi.',
            });
        } finally {
            setIsSmsSending(false);
        }
    };

    const handleEmailSubmit = async (event) => {
        event.preventDefault();

        const normalizedEmail = emailAddress.trim();
        if (!normalizedEmail) {
            setEmailStatus({ type: 'error', message: 'E-posta adresi girin.' });
            return;
        }

        setIsEmailSending(true);
        setEmailStatus({ type: 'idle', message: '' });

        try {
            await api.sendTestEmail(normalizedEmail);
            setEmailStatus({ type: 'success', message: 'Test e-postası gönderildi.' });
        } catch (error) {
            setEmailStatus({
                type: 'error',
                message: error.message || 'E-posta gönderilemedi.',
            });
        } finally {
            setIsEmailSending(false);
        }
    };

    useGSAP(() => {
        const mm = gsap.matchMedia();

        const setupCardsScene = (isMobile = false) => {
            let isGapAnimationCompleted = false;
            let isFlipAnimationCompleted = false;

            const root = containerRef.current;
            if (!root) return;

            const sticky = root.querySelector(".sticky");
            const mainTitle = root.querySelector(".alerts-main-title");
            const subTitle = root.querySelector(".alerts-sub-title");
            const cardContainer = root.querySelector(".card-container");
            const cards = gsap.utils.toArray(root.querySelectorAll(".card"));
            const card1 = root.querySelector(".card-1");
            const card2 = root.querySelector(".card-2");
            const card3 = root.querySelector(".card-3");
            const edgeCards = [card1, card3].filter(Boolean);

            if (!sticky || !mainTitle || !subTitle || !cardContainer || cards.length === 0) {
                return;
            }

            const settings = isMobile
                ? {
                    endScreens: 3.4,
                    startWidth: 94,
                    endWidth: 90,
                    separatedGap: 10,
                    radius: "12px",
                    card1Radius: "12px 0 0 12px",
                    card2Radius: "0px",
                    card3Radius: "0 12px 12px 0",
                    edgeY: 10,
                    edgeRotation: [-6, 6],
                    scrub: 0.75,
                }
                : {
                    endScreens: 4,
                    startWidth: 85,
                    endWidth: 75,
                    separatedGap: 24,
                    radius: "16px",
                    card1Radius: "16px 0 0 16px",
                    card2Radius: "0px",
                    card3Radius: "0 16px 16px 0",
                    edgeY: 20,
                    edgeRotation: [-8, 8],
                    scrub: 1,
                };

            gsap.set(cardContainer, { width: `${settings.startWidth}vw`, gap: "0px" });
            gsap.set(cards, { rotationY: 0, rotationZ: 0, y: 0 });
            if (card1) gsap.set(card1, { borderRadius: settings.card1Radius });
            if (card2) gsap.set(card2, { borderRadius: settings.card2Radius });
            if (card3) gsap.set(card3, { borderRadius: settings.card3Radius });

            ScrollTrigger.create({
                trigger: sticky,
                start: "top top",
                end: `+=${window.innerHeight * settings.endScreens}px`,
                scrub: settings.scrub,
                pin: true,
                pinSpacing: true,
                refreshPriority: 5,
                onUpdate: (self) => {
                    const progress = self.progress;

                    if (progressBarRef.current) {
                        gsap.set(progressBarRef.current, { "--progress": progress });
                    }

                    // AŞAMA 1: Oku ve Başlığı Yavaşça Kaybet, Sonra "Siz Uzakta Olsanız Bile..." Yazısını Getir
                    if (progress < 0.05) {
                        gsap.set(mainTitle, { y: 0, opacity: 1 });

                        gsap.set(subTitle, { y: 40, opacity: 0 });
                    } else if (progress > 0.2) {
                        gsap.set(mainTitle, { opacity: 0 });

                        gsap.set(subTitle, { y: 0, opacity: 1 });
                    } else {
                        // İlk başlık kaybolsun
                        const fadeOutOpacity = gsap.utils.mapRange(0.05, 0.15, 1, 0, progress);
                        gsap.set(mainTitle, { opacity: fadeOutOpacity });

                        // Alt Başlık (%15'ten %25'e kadar) Gelsin
                        let fadeInProgress = gsap.utils.mapRange(0.15, 0.25, 0, 1, Math.max(0.15, Math.min(0.25, progress)));
                        if (progress < 0.15) fadeInProgress = 0;
                        const yValue = gsap.utils.mapRange(0, 1, 40, 0, fadeInProgress);
                        gsap.set(subTitle, { y: yValue, opacity: fadeInProgress });
                    }

                    // AŞAMA 2: Küçülme
                    if (progress <= 0.25) {
                        const widthPercentage = gsap.utils.mapRange(
                            0,
                            0.25,
                            settings.startWidth,
                            settings.endWidth,
                            progress
                        );
                        gsap.set(cardContainer, { width: `${widthPercentage}vw` });
                    } else {
                        gsap.set(cardContainer, { width: `${settings.endWidth}vw` });
                    }

                    // AŞAMA 3: Ayrılma ve Köşe Yuvarlama
                    if (progress >= 0.35 && !isGapAnimationCompleted) {
                        gsap.to(cardContainer, { gap: `${settings.separatedGap}px`, duration: 0.5, ease: "power3.out" });
                        gsap.to(cards, { borderRadius: settings.radius, duration: 0.5, ease: "power3.out" });
                        isGapAnimationCompleted = true;
                    } else if (progress < 0.35 && isGapAnimationCompleted) {
                        gsap.to(cardContainer, { gap: "0px", duration: 0.5, ease: "power3.out" });
                        if (card1) gsap.to(card1, { borderRadius: settings.card1Radius, duration: 0.5, ease: "power3.out" });
                        if (card2) gsap.to(card2, { borderRadius: settings.card2Radius, duration: 0.5, ease: "power3.out" });
                        if (card3) gsap.to(card3, { borderRadius: settings.card3Radius, duration: 0.5, ease: "power3.out" });
                        isGapAnimationCompleted = false;
                    }

                    // AŞAMA 4: Flip (Dönme) ve Yelpaze Açılımı
                    if (progress >= 0.7 && !isFlipAnimationCompleted) {
                        gsap.to(cards, { rotationY: 180, duration: 0.8, ease: "power2.out", stagger: 0.15 });
                        gsap.to(edgeCards, {
                            y: settings.edgeY,
                            rotationZ: (i) => settings.edgeRotation[i],
                            duration: 0.8,
                            ease: "power2.out"
                        });
                        isFlipAnimationCompleted = true;
                    } else if (progress < 0.7 && isFlipAnimationCompleted) {
                        gsap.to(cards, { rotationY: 0, duration: 0.8, ease: "power2.inOut", stagger: -0.1 });
                        gsap.to(edgeCards, {
                            y: 0,
                            rotationZ: 0,
                            duration: 0.8,
                            ease: "power2.inOut"
                        });
                        isFlipAnimationCompleted = false;
                    }
                }
            });
        };

        mm.add("(min-width: 1000px)", () => setupCardsScene(false));
        mm.add("(max-width: 999px)", () => setupCardsScene(true));

        return () => mm.revert();

    }, { scope: containerRef });

    return (
        <div ref={containerRef} id="alerts">
            <section className="sticky">
                <div className="alerts-scroll-progress-bar" ref={progressBarRef}></div>
                
                <div className="sticky-header">
                    <h1 className="alerts-main-title">Uyarı Merkezi</h1>
                    <div className="alerts-sub-title">
                        <h2 className="alerts-highlight-title">Siz Uzakta Olsanız Bile Biz Yangını Görürüz.</h2>
                        <p>Yangın risklerini yapay zeka destekli anlık bildirimlerle takip edin.</p>
                    </div>
                </div>

                <div className="card-container">
                    {/* KART 1: TELEGRAM */}
                    <div className="card card-1">
                        <div className="card-front">
                            <img src="/foto/uyar1.png" alt="Orman Sol" loading="lazy" decoding="async" />
                        </div>
                        <div className="card-back design-card">
                            <div className="icon-wrapper telegram-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.02-1.96 1.25-5.54 3.69-.52.36-1 .53-1.42.52-.47-.01-1.37-.26-2.03-.48-.82-.27-1.47-.42-1.42-.88.03-.24.29-.48.79-.74 3.08-1.34 5.15-2.23 6.19-2.66 2.95-1.23 3.56-1.45 3.96-1.46.09 0 .28.02.41.1.11.08.15.19.16.3z" /></svg>
                            </div>
                            <h3>Telegram Bildirimi</h3>
                            <p>Yüksek riskli yangın ihtimali tespit edildiğinde Telegram üzerinden anında alarm alın.</p>
                            <div className="spacer"></div>
                            <a
                                href={TELEGRAM_BOT_URL}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-telegram"
                            >
                                Telegram ile Bağlan
                            </a>
                        </div>
                    </div>

                    {/* KART 2: SMS */}
                    <div className="card card-2">
                        <div className="card-front">
                            <img src="/foto/uyar2.png" alt="Orman Orta" loading="lazy" decoding="async" />
                        </div>
                        <div className="card-back design-card">
                            <div className="icon-wrapper sms-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z" /></svg>
                            </div>
                            <h3>SMS Uyarısı</h3>
                            <p>Bölgenizdeki yangın tehlikesini SMS ile hemen öğrenin.</p>
                            <div className="spacer"></div>
                            <form className="notification-form" onSubmit={handleSmsSubmit}>
                                <input
                                    id="sms-phone"
                                    name="smsPhone"
                                    type="tel"
                                    placeholder="+90 5XX XXX XX XX"
                                    className="ui-input"
                                    value={smsPhone}
                                    onChange={(event) => setSmsPhone(event.target.value)}
                                    disabled={isSmsSending}
                                    required
                                />
                                <button className="btn btn-orange" type="submit" disabled={isSmsSending}>
                                    {isSmsSending ? 'Gönderiliyor' : 'SMS ile Bağlan'}
                                </button>
                                {smsStatus.message && (
                                    <p className={`notification-status ${smsStatus.type}`}>
                                        {smsStatus.message}
                                    </p>
                                )}
                            </form>
                        </div>
                    </div>

                    {/* KART 3: E-POSTA */}
                    <div className="card card-3">
                        <div className="card-front">
                            <img src="/foto/uyar3.png" alt="Orman Sağ" loading="lazy" decoding="async" />
                        </div>
                        <div className="card-back design-card">
                            <div className="icon-wrapper email-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2zm-2 1H8v-6c0-2.48 1.51-4.5 4-4.5s4 2.02 4 4.5v6z" /></svg>
                            </div>
                            <h3>E-posta Bildirimi</h3>
                            <p>Detaylı yangın raporlarını ve uyarıları e-posta ile alın.</p>
                            <div className="spacer"></div>
                            {isDev && (
                                <form className="notification-form" onSubmit={handleEmailSubmit}>
                                    <input
                                        id="email-address"
                                        name="emailAddress"
                                        type="email"
                                        placeholder="E-posta adresiniz"
                                        className="ui-input"
                                        value={emailAddress}
                                        onChange={(event) => setEmailAddress(event.target.value)}
                                        disabled={isEmailSending}
                                        required
                                    />
                                    <button className="btn btn-orange" type="submit" disabled={isEmailSending}>
                                        {isEmailSending ? 'Gönderiliyor' : 'Test Gönder'}
                                    </button>
                                    {emailStatus.message && (
                                        <p className={`notification-status ${emailStatus.type}`}>
                                            {emailStatus.message}
                                        </p>
                                    )}
                                </form>
                            )}
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default NotificationCards;
