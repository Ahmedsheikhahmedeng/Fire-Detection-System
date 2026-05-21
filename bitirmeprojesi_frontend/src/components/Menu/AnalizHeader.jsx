import { useState, useEffect } from "react";
import { Flame, Satellite, CheckCircle, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import CreativeButton from "../CreativeButton/CreativeButton";
import axios from "axios";
import { API_BASE_URL } from "../../services/api";
import "./AnalizHeader.css";

export default function AnalizHeader({ isActive, setIsActive }) {
    const [isOnline, setIsOnline] = useState(true);
    const navigate = useNavigate();

    // Arka plan sisteminin canlı olup olmadığını kontrol et (Gerçek Veri Temsili)
    useEffect(() => {
        const checkStatus = async () => {
            try {
                await axios.get(`${API_BASE_URL}/map/status`, { timeout: 3000 });
                setIsOnline(true);
            } catch {
                setIsOnline(false);
            }
        };
        checkStatus();
        const timer = setInterval(checkStatus, 30000);
        return () => clearInterval(timer);
    }, []);

    return (
        <header
            className="analiz-header"
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                width: "100%",
                minHeight: 56,
                zIndex: 1050, // Menü 1000. Onun üstünde kalarak butonun ezilmesini (kaybolmasını) engeller.
                background: "linear-gradient(90deg, rgba(5,2,4,0.98), rgba(28,2,8,0.98), rgba(7,2,4,0.98))",
                borderBottom: "1px solid rgba(120,1,21,0.72)",
                boxShadow: "0 10px 30px rgba(0,0,0,0.46)",
                fontFamily: "'Inter', system-ui, sans-serif",
                color: "#ffffff",
            }}
        >
            {/* LEFT SIDE: Logo */}
            <div className="analiz-header-brand">
                <button
                    type="button"
                    className="analiz-header-brand-inner analiz-header-brand-button"
                    onClick={() => navigate("/")}
                    aria-label="Ana sayfaya git"
                >
                    <div
                        className="analiz-header-logo"
                        style={{ background: "rgba(120,1,21,0.32)", border: "1px solid rgba(120,1,21,0.78)" }}
                    >
                        <Flame className="analiz-header-logo-icon" size={16} color="#f7c1b6" />
                    </div>
                    <div className="analiz-header-title">
                        <div className="analiz-header-wordmark">
                            <span className="analiz-header-brand-fire" style={{ color: "#f7efe4", fontWeight: "bold" }}>FIRE</span>
                            <span className="analiz-header-brand-watch" style={{ color: "#f7b638", fontWeight: "bold" }}>WATCH</span>
                            <span className="analiz-header-version" style={{ background: "rgba(120,1,21,0.28)", color: "#f7c1b6", border: "1px solid rgba(120,1,21,0.58)" }}>
                                v1.0.01 
                            </span>
                        </div>
                        <div className="analiz-header-subtitle" style={{ color: "#cbbba4" }}>ORMAN YANGIN ERKEN TESPİT SİSTEMİ</div>
                    </div>
                </button>
            </div>

            {/* RIGHT SIDE: Stats & Menu Button */}
            <div className="analiz-header-actions">
                
                <div className="analiz-header-status">
                    <div className="analiz-header-chip">
                        <Satellite size={13} color="#f7b638" />
                        <span style={{ color: "#f6d28b" }}>3 SERVİS (VIIRS)</span>
                    </div>
                    <div className="analiz-header-divider" />
                    <div className="analiz-header-chip">
                        {isOnline ? <CheckCircle size={13} color="#7fbc8c" /> : <AlertTriangle size={13} color="#e24b36" />}
                        <span style={{ color: isOnline ? "#cce8c9" : "#f7c1b6" }}>
                            SİSTEM {isOnline ? "NORMAL" : "HATALI"}
                        </span>
                    </div>
                </div>

                <div className="analiz-header-menu-divider" />

                {/* Fixed width container prevents right-side pushing */}
                <div className="analiz-header-menu-slot">
                    <div className="analiz-header-menu-scale">
                        <CreativeButton onClick={() => setIsActive(!isActive)}>
                            {isActive ? "Kapat" : "Menü"}
                        </CreativeButton>
                    </div>
                </div>
                
            </div>
        </header>
    );
}
