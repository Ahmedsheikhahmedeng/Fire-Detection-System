import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import Nav from './Nav';
import styles from './style.module.css';
import CreativeButton from '../CreativeButton/CreativeButton';

import AnalizHeader from './AnalizHeader';

export default function Header() {
  const [isActive, setIsActive] = useState(false);
  const [windowSize, setWindowSize] = useState(() => ({
    width: typeof window !== 'undefined' ? window.innerWidth : 1000,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  }));
  const location = useLocation();

  useEffect(() => {
    const handleResize = () => setWindowSize({
      width: window.innerWidth,
      height: window.innerHeight,
    });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isAnaliz = location.pathname.includes("/analiz");
  const isCompactMenu = windowSize.width < 500 || windowSize.height < 680;
  const openMenuWidth = Math.max(
    288,
    Math.min(windowSize.width - 24, isCompactMenu ? 350 : 480)
  );
  const openMenuHeight = Math.max(
    420,
    Math.min(windowSize.height - 24, isCompactMenu ? 500 : 650)
  );

  const menuVariants = {
    open: {
      width: `${openMenuWidth}px`,
      height: `${openMenuHeight}px`,
      top: isCompactMenu ? "-12px" : "-25px",
      right: isCompactMenu ? "-12px" : "-25px",
      opacity: 1,
      transition: { duration: 0.99, type: "tween", ease: [0.76, 0, 0.24, 1] }
    },
    closed: {
      width: "100px",
      height: "40px",
      top: "0px",
      right: "0px",
      opacity: 0,
      transition: { duration: 0.44, type: "tween", ease: [0.76, 0, 0.24, 1] }
    }
  }

  return (
    <>
      <div className={styles.header}>
        <motion.div 
          className={styles.menu}
          variants={menuVariants}
          animate={isActive ? "open" : "closed"}
          initial="closed"
        >
          <AnimatePresence>
            {isActive && <Nav setIsActive={setIsActive} />}
          </AnimatePresence>
        </motion.div>
        
        {!isAnaliz && (
            <CreativeButton 
              className={`${styles.menuButtonWrapper} cybr-btn-wrapper`} 
              onClick={() => setIsActive(!isActive)}
            >
              {isActive ? "Kapat" : "Menü"}
            </CreativeButton>
        )}
      </div>

      {isAnaliz && <AnalizHeader isActive={isActive} setIsActive={setIsActive} />}
    </>
  );
}
