import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import axios from "axios";
import { AlertTriangle } from "lucide-react";
import { MapView } from "./MapView";
import { RecentFires } from "./RecentFires";
import { SystemStatus } from "./SystemStatus";
import { API_BASE_URL } from "../../services/api";
import { formatLocalTimestamp } from "../../utils/time";

const MAX_VISIBLE_HOURS = 24;

// Türkiye sınırları içinde lat/lng'yi harita üzerindeki % konumuna çevir
function latLngToXY(lat, lng) {
    const minLat = 36, maxLat = 42, minLng = 26, maxLng = 45;
    const x = ((lng - minLng) / (maxLng - minLng)) * 100;
    const y = ((maxLat - lat) / (maxLat - minLat)) * 100;
    return { x: Math.max(5, Math.min(95, x)), y: Math.max(5, Math.min(95, y)) };
}

function mapRiskLevel(riskLevel) {
    if (riskLevel === "CRITICAL" || riskLevel === "HIGH") return "high";
    if (riskLevel === "MEDIUM") return "medium";
    return "low";
}

function formatTimeAgo(hoursAgo) {
    if (hoursAgo == null || hoursAgo === 0) return "Az önce";
    if (hoursAgo < 1) return `${Math.round(hoursAgo * 60)} dk önce`;
    if (hoursAgo < 24) return `${Math.round(hoursAgo)} saat önce`;
    const days = Math.round(hoursAgo / 24);
    return `${days} gün önce`;
}

function getCityLabel(city) {
    const value = typeof city === "string" ? city.trim() : "";
    return value || "Çözülüyor...";
}

function transformHotspot(spot) {
    const { x, y } = latLngToXY(spot.latitude, spot.longitude);
    const risk = mapRiskLevel(spot.risk_level);
    const riskPercent = spot.risk_percent ?? (spot.fire_probability ? Math.round(spot.fire_probability * 100) : 0);

    return {
        id: spot.id,
        name: getCityLabel(spot.city),
        region: "Türkiye",
        x, y,
        lat: spot.latitude,
        lng: spot.longitude,
        risk,
        intensity: riskPercent,
        time: formatTimeAgo(spot.hours_ago),
        observedAt: spot.observed_at || null,
        observedLabel: formatLocalTimestamp(spot.observed_at),
        clusterId: spot.cluster_id || null,
        clusterStatus: spot.cluster_status || null,
        hoursAgo: Number.isFinite(spot.hours_ago) ? Number(spot.hours_ago) : Number.POSITIVE_INFINITY,
        temp: spot.temperature != null ? Math.round(spot.temperature) : "N/A",
        wind: spot.wind_speed != null ? Math.round(spot.wind_speed) : "N/A",
        humidity: spot.humidity != null ? Math.round(spot.humidity) : "N/A",
        active: spot.alert || false,
        direction: spot.spread_direction || "Ölçüm yok",
        spread: `${riskPercent}% risk`,
    };
}

function mapAlertLevel(riskLevel) {
    if (riskLevel === "CRITICAL" || riskLevel === "HIGH" || riskLevel === "MEDIUM") return "warning";
    return "info";
}

function formatAlertMessage(alert) {
    const probability = Number(alert.fire_probability);
    const probabilityText = Number.isFinite(probability)
        ? ` • Yangın olasılığı %${Math.round(probability * 100)}`
        : "";
    const location = [alert.latitude, alert.longitude].every((value) => Number.isFinite(Number(value)))
        ? ` (${Number(alert.latitude).toFixed(3)}, ${Number(alert.longitude).toFixed(3)})`
        : "";

    return `${alert.risk_level} uyarısı: Hotspot #${alert.hotspot_id}${location}${probabilityText}`;
}

export default function FireDashboardPage() {
    const [fireLocations, setFireLocations] = useState([]);
    const [selectedFire, setSelectedFire] = useState(null);
    const [alarmIndex, setAlarmIndex] = useState(0);
    const [alarms, setAlarms] = useState([]);
    const [alarmsEnabled] = useState(true);
    const [showAlarm, setShowAlarm] = useState(true);

    const fetchHotspots = useCallback(async () => {
        try {
            const [hotspotsRes, alertsRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/map/hotspots`),
                axios.get(`${API_BASE_URL}/alerts/active`, { timeout: 8000 }),
            ]);
            const recentHotspots = Array.isArray(hotspotsRes.data)
                ? hotspotsRes.data.filter((spot) => {
                    const hours = Number(spot.hours_ago);
                    return Number.isFinite(hours) && hours <= MAX_VISIBLE_HOURS;
                })
                : [];
            const transformed = recentHotspots.map(transformHotspot);
            transformed.sort((a, b) => b.intensity - a.intensity);
            setFireLocations(transformed);
            const activeAlarms = Array.isArray(alertsRes.data)
                ? alertsRes.data.map((alert) => ({
                    id: alert.alert_id,
                    message: formatAlertMessage(alert),
                    level: mapAlertLevel(alert.risk_level),
                }))
                : [];
            setAlarms(activeAlarms);
            setAlarmIndex((index) => activeAlarms.length ? index % activeAlarms.length : 0);
        } catch (e) {
            console.error("Backend bağlantı hatası:", e);
        }
    }, []);

    useEffect(() => {
        queueMicrotask(fetchHotspots);
        const interval = setInterval(fetchHotspots, 60000);
        return () => clearInterval(interval);
    }, [fetchHotspots]);

    // Saat güncelleme özellikle her saniye re-render tetikliyor, kaldırıldı

    useEffect(() => {
        if (!alarmsEnabled || alarms.length === 0) return;
        const interval = setInterval(() => {
            setAlarmIndex((i) => (i + 1) % alarms.length);
        }, 8000); // 5s'den 8s'ye çıkarıldı
        return () => clearInterval(interval);
    }, [alarmsEnabled, alarms.length]);

    const activeAlarm = alarms[alarmIndex] || null;

    return (
        <div
            className="h-screen flex flex-col overflow-hidden"
            style={{
                height: "100vh",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                background: "#080007",
                fontFamily: "'Inter', system-ui, sans-serif",
                color: "#ffffff",
                position: "relative",
                zIndex: 1,
            }}
        >
            {/* SPACER FOR GLOBAL FIXED HEADER */}
            <div style={{ height: 56, flexShrink: 0 }} />

            {/* ALARM BANNER */}
            <AnimatePresence mode="wait">
                {alarmsEnabled && showAlarm && activeAlarm && (
                    <motion.div
                        key={alarmIndex}
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.4 }}
                        className="shrink-0 flex items-center gap-3 px-4 md:px-6 py-2"
                        style={{
                            background: activeAlarm.level === "warning"
                                ? "rgba(80,20,10,0.92)"
                                : "rgba(40,5,15,0.92)",
                            borderBottom: `1px solid ${activeAlarm.level === "warning" ? "#f7b638" : "rgba(247,182,56,0.3)"}`,
                            borderTop: "1px solid rgba(247,182,56,0.15)",

                        }}
                    >
                    <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ repeat: Infinity, duration: 2 }}>
                            <AlertTriangle
                                size={14}
                                color={activeAlarm.level === "warning" ? "#f3d39b" : "#cce8c9"}
                            />
                        </motion.div>
                        <span style={{ fontSize: 12, flex: 1 }}>{activeAlarm.message}</span>
                        <button onClick={() => setShowAlarm(false)} style={{ color: "#f7efe4", fontSize: 10 }}>KAPAT</button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* MAIN CONTENT */}
            <div className="flex-1 flex flex-col lg:flex-row gap-3 px-4 md:px-6 py-3 overflow-hidden min-h-0"
                style={{ flex: 1, display: "flex", gap: 12, padding: "12px 16px", overflow: "hidden", minHeight: 0 }}>
                {/* LEFT — Map */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, minHeight: 0 }}>
                    <MapView
                        fires={fireLocations}
                        selectedFire={selectedFire}
                        onSelectFire={setSelectedFire}
                    />
                </div>

                {/* RIGHT — Sidebar */}
                <div
                    style={{ display: "flex", flexDirection: "column", gap: 12, width: 288, minHeight: 0, flexShrink: 0 }}
                >
                    <SystemStatus />
                    <RecentFires
                        fires={fireLocations}
                        selectedFire={selectedFire}
                        onSelectFire={setSelectedFire}
                    />
                </div>
            </div>
        </div>
    );
}
