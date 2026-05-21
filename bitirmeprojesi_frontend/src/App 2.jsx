import { Component, lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Header from "./components/Menu/Header";
import Home from "./pages/Home/Home";

import { Toaster } from "react-hot-toast";

const FireAnalysis = lazy(() => import("./pages/FireAnalysis/FireAnalysis"));
const MonitoringSection = lazy(() => import("./pages/Monitoring/MonitoringSection"));
const Footer = lazy(() => import("./components/Footer/Footer"));

function PageFallback() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background: "#020101",
        color: "#fff8ee",
        fontFamily: "Inter, sans-serif",
      }}
    >
      Yükleniyor...
    </div>
  );
}

class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    console.error("Uygulama hatası:", error);
  }

  render() {
    if (this.state.error) {
      return (
        <div
          style={{
            minHeight: "100vh",
            padding: "32px",
            background: "#020101",
            color: "#fff8ee",
            fontFamily: "Inter, sans-serif",
          }}
        >
          <h1 style={{ marginTop: 0 }}>Uygulama açılırken hata oluştu</h1>
          <pre style={{ whiteSpace: "pre-wrap" }}>
            {this.state.error.message}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}

function AppContent() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <>
      <Header />
      <main style={{ position: 'relative', zIndex: 10, backgroundColor: '#000' }}>
        <Suspense fallback={<PageFallback />}>
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
    <AppErrorBoundary>
      <BrowserRouter>
        <AppContent />
        <Toaster position="top-right" />
      </BrowserRouter>
    </AppErrorBoundary>
  );
}
