import { lazy, Suspense, useEffect, useRef, useState } from "react";
import MonitoringSection from "../Monitoring/MonitoringSection";
import "./FireAnalysis.css";

const RiskAnalysisPage = lazy(() => import("../FireDashboard/RiskAnalysisPage"));

function DeferredRiskAnalysis() {
  const rootRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || isVisible) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "360px 0px" }
    );

    observer.observe(root);
    return () => observer.disconnect();
  }, [isVisible]);

  return (
    <div className="fire-analysis-risk-wrap" ref={rootRef}>
      {isVisible && (
        <Suspense fallback={null}>
          <RiskAnalysisPage />
        </Suspense>
      )}
    </div>
  );
}

export default function FireAnalysis() {
  return (
    <div className="fire-analysis-page">
      <MonitoringSection />
      <DeferredRiskAnalysis />
    </div>
  );
}
