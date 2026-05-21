import { useEffect, useRef } from "react";
import gsap from "gsap";
import styles from "./style.module.css";

export default function CreativeButton({
  children = "Uyarı Merkezi",
  onClick,
  className = "",
  variant = "default",
}) {
  const buttonRef = useRef(null);
  const textRef = useRef(null);
  const isForest = variant === "forest";

  useEffect(() => {
    if (!buttonRef.current || !textRef.current) return undefined;

    // Butonun dış çerçevesi için manyetik çekim gücü
    const xTo = gsap.quickTo(buttonRef.current, "x", { duration: 1, ease: "elastic.out(1, 0.3)" });
    const yTo = gsap.quickTo(buttonRef.current, "y", { duration: 1, ease: "elastic.out(1, 0.3)" });

    // İçindeki metin için daha hafif bir manyetik hareket (Derinlik hissi)
    const xTextTo = gsap.quickTo(textRef.current, "x", { duration: 1, ease: "elastic.out(1, 0.3)" });
    const yTextTo = gsap.quickTo(textRef.current, "y", { duration: 1, ease: "elastic.out(1, 0.3)" });

    const handleMouseMove = (e) => {
      const { clientX, clientY } = e;
      const { height, width, left, top } = buttonRef.current.getBoundingClientRect();
      const x = clientX - (left + width / 2);
      const y = clientY - (top + height / 2);
      
      xTo(x * 0.3);      // Buton farenin %30'u kadar hareket eder
      yTo(y * 0.3);
      xTextTo(x * 0.15); // Metin farenin %15'i kadar hareket eder
      yTextTo(y * 0.15);
    };

    const handleMouseLeave = () => {
      // Fare ayrıldığında her şeyi merkeze (0) geri çek
      xTo(0);
      yTo(0);
      xTextTo(0);
      yTextTo(0);
    };

    const element = buttonRef.current;
    element.addEventListener("mousemove", handleMouseMove);
    element.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      element.removeEventListener("mousemove", handleMouseMove);
      element.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  if (isForest) {
    return (
      <div className={`${styles.buttonWrapper} ${styles.forestWrapper} ${className}`}>
        <div className={styles.forestButton} ref={buttonRef} onClick={onClick}>
          <span className={styles.forestText} ref={textRef}>
            {children}
          </span>
          <span className={styles.forestTextAlt}>{children}</span>

          <svg
            className={styles.forestWaveBack}
            viewBox="0 0 2400 800"
            aria-hidden="true"
            focusable="false"
          >
            <defs>
              <linearGradient id="forest-button-grad" y2="100%" x2="50%" y1="0%" x1="50%">
                <stop offset="0%" stopColor="hsl(41, 97%, 63%)" />
                <stop offset="100%" stopColor="hsl(142, 53%, 36%)" />
              </linearGradient>
            </defs>
            <g transform="matrix(1,0,0,1,0,-91.0877685546875)" fill="url(#forest-button-grad)">
              <path opacity="0.09" transform="matrix(1,0,0,1,0,35)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
              <path opacity="0.25" transform="matrix(1,0,0,1,0,70)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
              <path opacity="0.44" transform="matrix(1,0,0,1,0,115)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
              <path opacity="0.7" transform="matrix(1,0,0,1,0,170)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
              <path opacity="1" transform="matrix(1,0,0,1,0,230)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            </g>
          </svg>

          <svg
            className={styles.forestWaveFront}
            viewBox="0 0 1440 320"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M0,288L9.2,250.7C18.5,213,37,139,55,133.3C73.8,128,92,192,111,224C129.2,256,148,256,166,256C184.6,256,203,256,222,250.7C240,245,258,235,277,213.3C295.4,192,314,160,332,170.7C350.8,181,369,235,388,229.3C406.2,224,425,160,443,122.7C461.5,85,480,75,498,74.7C516.9,75,535,85,554,101.3C572.3,117,591,139,609,170.7C627.7,203,646,245,665,256C683.1,267,702,245,720,245.3C738.5,245,757,267,775,266.7C793.8,267,812,245,831,234.7C849.2,224,868,224,886,218.7C904.6,213,923,203,942,170.7C960,139,978,85,997,53.3C1015.4,21,1034,11,1052,48C1070.8,85,1089,171,1108,197.3C1126.2,224,1145,192,1163,197.3C1181.5,203,1200,245,1218,224C1236.9,203,1255,117,1274,106.7C1292.3,96,1311,160,1329,170.7C1347.7,181,1366,139,1385,128C1403.1,117,1422,139,1431,149.3L1440,160L1440,320L0,320Z" />
          </svg>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.buttonWrapper} cybr-btn-wrapper ${className}`}>
      <div className={styles.button} ref={buttonRef} onClick={onClick}>
        <div className={styles.fill}></div>
        <svg
          className={styles.buttonWaveBack}
          viewBox="0 0 2400 800"
          aria-hidden="true"
          focusable="false"
        >
          <defs>
            <linearGradient id="button-wave-grad" y2="100%" x2="50%" y1="0%" x1="50%">
              <stop offset="0%" stopColor="#f7b638" />
              <stop offset="52%" stopColor="#b85f22" />
              <stop offset="100%" stopColor="#780115" />
            </linearGradient>
          </defs>
          <g transform="matrix(1,0,0,1,0,-91.0877685546875)" fill="url(#button-wave-grad)">
            <path opacity="0.05" transform="matrix(1,0,0,1,0,35)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="0.21" transform="matrix(1,0,0,1,0,70)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="0.37" transform="matrix(1,0,0,1,0,105)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="0.53" transform="matrix(1,0,0,1,0,140)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="0.68" transform="matrix(1,0,0,1,0,175)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="0.84" transform="matrix(1,0,0,1,0,210)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
            <path opacity="1" transform="matrix(1,0,0,1,0,245)" d="M 0 305.9828838196134 Q 227.6031525693441 450 600 302.17553022897005 Q 1010.7738828515054 450 1200 343.3024459932802 Q 1379.4406250195766 450 1800 320.38902780838214 Q 2153.573162029817 450 2400 314.38564046970816 L 2400 800 L 0 800 L 0 340.3112176762882 Z" />
          </g>
        </svg>
        <svg
          className={styles.buttonWaveFront}
          viewBox="0 0 1440 320"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M0,288L9.2,250.7C18.5,213,37,139,55,133.3C73.8,128,92,192,111,224C129.2,256,148,256,166,256C184.6,256,203,256,222,250.7C240,245,258,235,277,213.3C295.4,192,314,160,332,170.7C350.8,181,369,235,388,229.3C406.2,224,425,160,443,122.7C461.5,85,480,75,498,74.7C516.9,75,535,85,554,101.3C572.3,117,591,139,609,170.7C627.7,203,646,245,665,256C683.1,267,702,245,720,245.3C738.5,245,757,267,775,266.7C793.8,267,812,245,831,234.7C849.2,224,868,224,886,218.7C904.6,213,923,203,942,170.7C960,139,978,85,997,53.3C1015.4,21,1034,11,1052,48C1070.8,85,1089,171,1108,197.3C1126.2,224,1145,192,1163,197.3C1181.5,203,1200,245,1218,224C1236.9,203,1255,117,1274,106.7C1292.3,96,1311,160,1329,170.7C1347.7,181,1366,139,1385,128C1403.1,117,1422,139,1431,149.3L1440,160L1440,320L1430.8,320C1421.5,320,1403,320,1385,320C1366.2,320,1348,320,1329,320C1310.8,320,1292,320,1274,320C1255.4,320,1237,320,1218,320C1200,320,1182,320,1163,320C1144.6,320,1126,320,1108,320C1089.2,320,1071,320,1052,320C1033.8,320,1015,320,997,320C978.5,320,960,320,942,320C923.1,320,905,320,886,320C867.7,320,849,320,831,320C812.3,320,794,320,775,320C756.9,320,738,320,720,320C701.5,320,683,320,665,320C646.2,320,628,320,609,320C590.8,320,572,320,554,320C535.4,320,517,320,498,320C480,320,462,320,443,320C424.6,320,406,320,388,320C369.2,320,351,320,332,320C313.8,320,295,320,277,320C258.5,320,240,320,222,320C203.1,320,185,320,166,320C147.7,320,129,320,111,320C92.3,320,74,320,55,320C36.9,320,18,320,9,320L0,320Z" />
        </svg>
        <span className={styles.text} ref={textRef}>
          {children}
        </span>
      </div>
    </div>
  );
}
