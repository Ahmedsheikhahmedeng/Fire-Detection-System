import { memo, useEffect, useMemo, useRef, useState } from "react";
import { motion, useScroll, useTransform } from 'framer-motion';
import styles from './style.module.css';

const STATIC_SCROLL_QUERY =
    "(prefers-reduced-motion: reduce)";

const AnimatedLetter = memo(function AnimatedLetter({ letter, progress, offset, index }) {
    const y = useTransform(progress, [0, 1], [0, offset]);

    return (
        <motion.span style={{ top: y }} key={`l_${index}`}>
            {letter === " " ? "\u00A0\u00A0" : letter}
        </motion.span>
    );
});

const StaticLetter = memo(function StaticLetter({ letter, index }) {
    return (
        <span key={`l_${index}`}>
            {letter === " " ? "\u00A0\u00A0" : letter}
        </span>
    );
});

function useStaticScrollScene() {
    const [isStatic, setIsStatic] = useState(() => {
        if (typeof window === "undefined") return false;
        return window.matchMedia(STATIC_SCROLL_QUERY).matches;
    });

    useEffect(() => {
        const media = window.matchMedia(STATIC_SCROLL_QUERY);
        const update = () => setIsStatic(media.matches);

        update();
        if (media.addEventListener) {
            media.addEventListener("change", update);
            return () => media.removeEventListener("change", update);
        }

        media.addListener(update);
        return () => media.removeListener(update);
    }, []);

    return isStatic;
}

function createLetters(word) {
    return word.split("").map((letter, index) => ({
        letter,
        offset: -25 - ((index * 37) % 75),
    }));
}

function createImages(imagesProp, md = 0, lg = 0) {
    if (imagesProp) {
        return [
            { src: imagesProp[0], y: 0 },
            { src: imagesProp[1], y: lg },
            { src: imagesProp[2], y: md }
        ];
    }

    return [
        { src: "/foto/nasil1.jpeg", y: 0 },
        { src: "/foto/nasil2.jpeg", y: lg },
        { src: "/foto/home3.png", y: md }
    ];
}

function ParallaxMarkup({
    container,
    title1,
    title2,
    word,
    imagesProp,
    description,
    animated,
    scrollYProgress,
    sm,
    md,
    lg,
}) {
    const letters = useMemo(() => createLetters(word), [word]);
    const images = useMemo(
        () => createImages(imagesProp, md, lg),
        [imagesProp, md, lg]
    );
    const TitleOne = animated ? motion.h1 : "h1";
    const ImageContainer = animated ? motion.div : "div";

    return (
        <div ref={container} className={styles.container}>
            <div className={styles.body}>
                <TitleOne style={animated ? { y: sm } : undefined}>{title1}</TitleOne>
                <h1>{title2}</h1>
                <div className={styles.word}>
                    <p>
                        {
                            letters.map(({ letter, offset }, i) => (
                                animated ? (
                                    <AnimatedLetter
                                        key={`l_${i}`}
                                        letter={letter}
                                        progress={scrollYProgress}
                                        offset={offset}
                                        index={i}
                                    />
                                ) : (
                                    <StaticLetter
                                        key={`l_${i}`}
                                        letter={letter}
                                        index={i}
                                    />
                                )
                            ))
                        }
                    </p>
                </div>
            </div>
            <div className={styles.images}>
                {
                    images.map(({ src, y }, i) => {
                        // Resim 0: Büyük (55vh x 40vh)
                        // Resim 1: Orta (30vh x 30vh)
                        // Resim 2: En Küçük (20vh x 20vh)
                        const isSmallImage = i === 2;
                        return (
                            <ImageContainer
                                style={animated ? { y } : undefined}
                                key={`i_${i}`}
                                className={`${styles.imageContainer} ${isSmallImage ? 'fall-target' : ''}`}
                            >
                                <img src={src} alt="Parallax Image" loading="lazy" decoding="async" />
                            </ImageContainer>
                        )
                    })
                }
            </div>
            {description && (
                <div className={styles.description}>
                    <p>{description}</p>
                </div>
            )}
        </div>
    );
}

function AnimatedParallaxScroll({ 
    title1 = "SİSTEM", 
    title2 = "ANALİZİ", 
    word = "CANLI TAKİP",
    imagesProp,
    description
}) {
    const container = useRef(null);
    const isMobile = typeof window !== "undefined" &&
        window.matchMedia("(max-width: 768px)").matches;
    const { scrollYProgress } = useScroll({
        target: container,
        offset: ['start end', 'end start']
    });
    
    const sm = useTransform(scrollYProgress, [0, 1], [0, isMobile ? -28 : -50]);
    const md = useTransform(scrollYProgress, [0, 1], [0, isMobile ? -90 : -150]);
    const lg = useTransform(scrollYProgress, [0, 1], [0, isMobile ? -145 : -250]);

    return (
        <ParallaxMarkup
            container={container}
            title1={title1}
            title2={title2}
            word={word}
            imagesProp={imagesProp}
            description={description}
            animated
            scrollYProgress={scrollYProgress}
            sm={sm}
            md={md}
            lg={lg}
        />
    );
}

function StaticParallaxScroll({
    title1 = "SİSTEM",
    title2 = "ANALİZİ",
    word = "CANLI TAKİP",
    imagesProp,
    description
}) {
    return (
        <ParallaxMarkup
            title1={title1}
            title2={title2}
            word={word}
            imagesProp={imagesProp}
            description={description}
            animated={false}
        />
    );
}

export default function ParallaxScroll(props) {
    const isStatic = useStaticScrollScene();
    return isStatic ? (
        <StaticParallaxScroll {...props} />
    ) : (
        <AnimatedParallaxScroll {...props} />
    );
}
