import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import gsap from 'gsap';
import { disperse } from './anim';
import './Footer.css';

// ---- TextDisperse bileşeni ----
function TextDisperse({ children, setBackground, href }) {
    const [isAnimated, setIsAnimated] = useState(false);

    const getChars = (text) => {
        if (typeof text !== 'string') return text;

        return text.split("").map((char, i) => (
            <motion.span
                key={i}
                custom={i}
                variants={disperse}
                animate={isAnimated ? "open" : "closed"}
                style={{ display: "inline-block", whiteSpace: "pre" }}
            >
                {char === " " ? "\u00A0" : char}
            </motion.span>
        ));
    };

    const Tag = href ? "a" : "div";

    return (
        <Tag
            {...(href && {
                href: href,
                ...(href.startsWith('http') && { target: "_blank", rel: "noopener noreferrer" })
            })}
            style={{ textDecoration: 'none', cursor: "pointer", display: "inline-flex" }}
            onMouseEnter={() => {
                setBackground(true);
                setIsAnimated(true);
            }}
            onMouseLeave={() => {
                setBackground(false);
                setIsAnimated(false);
            }}
            className="footer-disperse-link"
        >
            {getChars(children)}
        </Tag>
    );
}

// ---- Ana Footer ----
export default function Footer() {
    return (
        <div className="footer-wrapper" style={{ clipPath: "polygon(0% 0, 100% 0%, 100% 100%, 0 100%)" }}>
            <div className="footer-fixed-container">
                <Content />
            </div>
        </div>
    );
}

function Content() {
    const background = useRef(null);

    const setBackground = (isActive) => {
        gsap.to(background.current, {
            opacity: isActive ? 0.8 : 0,
            backdropFilter: isActive ? 'blur(6px)' : 'blur(0px)',
            duration: 0.5
        });
    };

    return (
        <div className="footer-content-bg">
            <Nav setBackground={setBackground} />

            {/* Karartma Overlay */}
            <div ref={background} className="footer-background-overlay"></div>

            <div className="footer-bottom-bar">
                <h1>YANGIN İZLE </h1>
                <p><span style={{ color: "var(--brand-crimson)", textShadow: "0 0 2px var(--brand-amber)" }}>© {new Date().getFullYear()}</span> Tüm Hakları Saklıdır.</p>
            </div>
        </div>
    );
}

const Nav = ({ setBackground }) => {
    return (
        <div className="footer-nav">
            <div className="footer-nav-col">
                <h3>Sistem</h3>
                <TextDisperse setBackground={setBackground} href="/">Ana Sayfa</TextDisperse>
                <TextDisperse setBackground={setBackground} href="/#how">Nasıl Çalışır?</TextDisperse>
                <TextDisperse setBackground={setBackground} href="/#awareness">Çözümlerimiz</TextDisperse>
            </div>
            <div className="footer-nav-col">
                <h3>Risk Analizi</h3>
                <TextDisperse setBackground={setBackground} href="/analiz">Canlı İzleme</TextDisperse>
                <TextDisperse setBackground={setBackground} href="/analiz">Raporlar</TextDisperse>
                <TextDisperse setBackground={setBackground} href="/analiz">İstatistikler</TextDisperse>
            </div>
            <div className="footer-nav-col">
                <h3>Hakkımızda</h3>
                <TextDisperse setBackground={setBackground} href="https://ahmedshikhahmed.pages.dev/">
                    Biz Kimiz➚
                </TextDisperse>
                <TextDisperse setBackground={setBackground} href="https://ahmedshikhahmed.pages.dev/#project-1">
                    Proje➚
                </TextDisperse>
                <TextDisperse setBackground={setBackground} href="https://ahmedshikhahmed.pages.dev/contact">
                    İletişim➚
                </TextDisperse>
            </div>
        </div>
    );
};
