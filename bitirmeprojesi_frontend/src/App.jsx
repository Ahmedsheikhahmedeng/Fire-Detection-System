import { lazy, Suspense, useEffect, useLayoutEffect, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Header from "./components/Menu/Header";

import { Toaster } from "react-hot-toast";

const Home = lazy(() => import("./pages/Home/Home"));
const FireAnalysis = lazy(() => import("./pages/FireAnalysis/FireAnalysis"));
const MonitoringSection = lazy(() => import("./pages/Monitoring/MonitoringSection"));
const Footer = lazy(() => import("./components/Footer/Footer"));

function AppContent() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [location.pathname]);

  return (
    <>
      <Header />
      <main style={{ position: 'relative', zIndex: 10, backgroundColor: '#000' }}>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analiz" element={<FireAnalysis />} />
            <Route path="/izleme" element={<MonitoringSection />} />
          </Routes>
        </Suspense>
      </main>
      {isHome && <DeferredFooter />}
    </>
  );
}

function DeferredFooter() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setIsReady(true), 7000);

    return () => window.clearTimeout(id);
  }, []);

  if (!isReady) return null;

  return (
    <Suspense fallback={null}>
      <Footer />
    </Suspense>
  );
}

export default function App() {
  return (
      <BrowserRouter>
        <AppContent />
        <Toaster position="top-right" />
      </BrowserRouter>
  );
}
