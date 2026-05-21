import { useRef } from 'react';
import { motion } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import { perspective } from './anim';
import styles from './style.module.css';

const links = [
  { title: "Genel Bakış", href: "/#Home" },
  { title: "Farkındalık", href: "/#awareness" },
  { title: "Uyarı Merkezi", href: "/#alerts" },
  { title: "Nasıl Çalışır", href: "/#how" },
  { title: "Canlı İzleme", href: "/analiz", isHighlight: true },
];

const externalLinks = [
  { title: "Biz Kimiz?", href: "https://ahmedshikhahmed.pages.dev/" },
  { title: "Proje", href: "https://ahmedshikhahmed.pages.dev/#project-1" },
  { title: "İletişim", href: "https://ahmedshikhahmed.pages.dev/contact" },
];

function MenuLink({ title, href, onClick, className, isExternal }) {
    return (
        <a 
            href={href} 
            onClick={onClick}
            target={isExternal ? "_blank" : "_self"}
            rel={isExternal ? "noopener noreferrer" : ""}
            className={className}
        >
            {title}
        </a>
    );
}

export default function Nav({ setIsActive }) {
  const navRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  const handleClick = (e, href) => {
    e.preventDefault();
    setIsActive(false);

    if (href.startsWith("/#")) {
      const id = href.split("#")[1];
      if (location.pathname === "/") {
        setTimeout(() => {
          const el = document.getElementById(id);
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 500);
      } else {
        navigate("/");
        setTimeout(() => {
          const el = document.getElementById(id);
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 800);
      }
    } else {
      navigate(href);
    }
  };

  return (
    <div className={styles.nav} ref={navRef}>
      <div className={styles.body}>
        {links.map((link, i) => {
          const { title, href, isHighlight } = link;
          return (
            <div key={`b_${i}`} className={styles.linkContainer}>
              <motion.div
                custom={i}
                variants={perspective}
                initial="initial"
                animate="enter"
                exit="exit"
              >
                <MenuLink
                  title={title}
                  href={href}
                  onClick={(e) => handleClick(e, href)}
                  className={isHighlight ? styles.canliIzleme : ""}
                />
              </motion.div>
            </div>
          );
        })}
      </div>

      {/* Alt Bölüm: Hakkımızda Linkleri */}
      <div className={styles.footer}>
        {externalLinks.map((link, i) => (
          <motion.div
            key={`ext_${i}`}
            custom={links.length + i}
            variants={perspective}
            initial="initial"
            animate="enter"
            exit="exit"
          >
            <MenuLink
              title={link.title}
              href={link.href}
              className={styles.externalLink}
              isExternal={true}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
