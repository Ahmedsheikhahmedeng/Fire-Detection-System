import { useCallback, useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell,
} from "recharts";
import {
    Satellite, Thermometer, Flame, CheckCircle, RefreshCw,
    Brain, AlertTriangle, TrendingUp,
    Wind, MapPin,
} from "lucide-react";
import axios from "axios";
import { formatRelativeTimestamp } from "../../utils/time";
import { API_BASE_URL, WS_BASE_URL } from "../../services/api";
import "./RiskAnalysisPage.css";

const API = API_BASE_URL;
const COLORS = ["#e24b36", "#dda34a", "#d9c6b0", "#8b7355", "#5c4d3c"];

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-lg px-3 py-2"
            style={{ background: "rgba(10, 2, 3, 0.95)", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11, color: "#d9c6b0" }}>
            <div style={{ color: "#ffffff", marginBottom: 4 }}>{label}</div>
            {payload.map((p) => (
                <div key={p.name} className="flex items-center gap-2">
                    <span style={{ color: p.color }}>●</span>
                    <span>{p.name}: <strong style={{ color: p.color }}>{p.value}</strong></span>
                </div>
            ))}
        </div>
    );
};

export default function RiskAnalysisPage() {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState(null);
    const [sourceStats, setSourceStats] = useState(null);
    const [sourceStatsError, setSourceStatsError] = useState(false);
    const [clusterStats, setClusterStats] = useState(null);
    const [clusterStatsError, setClusterStatsError] = useState(false);
    const [clusterStatusFilter, setClusterStatusFilter] = useState("active,monitoring");
    const [systemHealth, setSystemHealth] = useState(null);
    const [systemHealthError, setSystemHealthError] = useState(false);
    const [systemHealthLoading, setSystemHealthLoading] = useState(true);
    const [recentHotspotCount, setRecentHotspotCount] = useState(0);
    const [lastUpdate, setLastUpdate] = useState("Bağlanıyor...");
    const [animKey, setAnimKey] = useState(0);

    const fetchAll = useCallback(async (isManual = false) => {
        if (isManual) setLoading(true);
        try {
            const sourceStatsRequest = axios
                .get(`${API}/api/hotspots/source-stats`, { timeout: 8000 })
                .then((res) => ({ ok: true, data: res.data }))
                .catch(() => ({ ok: false }));
            const clusterStatsRequest = axios
                .get(`${API}/api/hotspots/clusters`, {
                    timeout: 8000,
                    params: {
                        status: clusterStatusFilter,
                        limit: 50,
                    },
                })
                .then((res) => ({ ok: true, data: res.data }))
                .catch(() => ({ ok: false }));
            const systemHealthRequest = axios
                .get(`${API}/api/system/health`, { timeout: 8000 })
                .then((res) => ({ ok: true, data: res.data }))
                .catch(() => ({ ok: false }));

            const [statsRes, statusRes, hotspotsRes, sourceStatsRes, clusterStatsRes, systemHealthRes] = await Promise.all([
                axios.get(`${API}/map/stats`, { timeout: 8000 }),
                axios.get(`${API}/map/status`, { timeout: 8000 }),
                axios.get(`${API}/map/hotspots`, { timeout: 8000 }),
                sourceStatsRequest,
                clusterStatsRequest,
                systemHealthRequest,
            ]);
            setStats(statsRes.data);
            if (sourceStatsRes.ok) {
                setSourceStats(sourceStatsRes.data);
                setSourceStatsError(false);
            } else {
                setSourceStatsError(true);
            }
            if (clusterStatsRes.ok) {
                setClusterStats(clusterStatsRes.data);
                setClusterStatsError(false);
            } else {
                setClusterStatsError(true);
            }
            if (systemHealthRes.ok) {
                setSystemHealth(systemHealthRes.data);
                setSystemHealthError(false);
            } else {
                setSystemHealthError(true);
            }
            setSystemHealthLoading(false);
            const recent48 = Array.isArray(hotspotsRes.data)
                ? hotspotsRes.data.filter((spot) => {
                    const hours = Number(spot.hours_ago);
                    return Number.isFinite(hours) && hours <= 48;
                }).length
                : 0;
            setRecentHotspotCount(recent48);
            if (statusRes.data?.last_ml_scan) {
                setLastUpdate(formatRelativeTimestamp(statusRes.data.last_ml_scan));
            }
            setAnimKey(k => k + 1);
        } catch (e) {
            console.error("Dashboard veri hatası:", e);
        } finally {
            setSystemHealthLoading(false);
            if (isManual) {
                setTimeout(() => { setLoading(false); }, 600);
            } else {
                setLoading(false);
            }
        }
    }, [clusterStatusFilter]);

    useEffect(() => {
        fetchAll();
        const pollInterval = setInterval(() => fetchAll(false), 60000); // 60s'ye çıkarıldı

        let ws;
        let reconnectTimer;
        let reconnectDelay = 5000;
        
        function connectWs() {
            try {
                ws = new WebSocket(`${WS_BASE_URL}/alerts/ws`);
                ws.onopen = () => {
                    reconnectDelay = 5000; // başarılıysa sıfırla
                };
                ws.onclose = () => {
                    reconnectTimer = setTimeout(() => {
                        reconnectDelay = Math.min(reconnectDelay * 2, 60000); // max 60s
                        connectWs();
                    }, reconnectDelay);
                };
                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === "HOTSPOT_UPDATED" || data.type === "NEW_FIRE_ALERT") {
                            fetchAll(false);
                        }
                    } catch {
                        // Geçersiz WebSocket mesajını yoksay.
                    }
                };
            } catch {
                reconnectTimer = setTimeout(() => {
                    reconnectDelay = Math.min(reconnectDelay * 2, 60000);
                    connectWs();
                }, reconnectDelay);
            }
        }
        connectWs();

        return () => {
            clearInterval(pollInterval);
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        };
    }, [fetchAll]);

    const getSourceStatus = (hours) => {
        const value = Number(hours);
        if (!Number.isFinite(value)) return { label: "Veri bekleniyor", color: "#d9c6b0" };
        if (value <= 6) return { label: "Güncel", color: "#7fbc8c" };
        if (value <= 12) return { label: "Normal gecikme", color: "#dda34a" };
        return { label: "Gecikmiş olabilir", color: "#e24b36" };
    };

    const formatObservationTime = (value) => {
        if (!value) return "Bekleniyor";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "Bekleniyor";
        return date.toLocaleString("tr-TR", {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "Europe/Istanbul",
        });
    };
    const clusterFilterOptions = [
        { label: "Aktif", value: "active,monitoring" },
        { label: "İzlemede", value: "monitoring" },
        { label: "Geçmiş", value: "resolved" },
        { label: "Tümü", value: "all" },
    ];
    const getClusterStatusLabel = (status) => {
        if (status === "active") return "Aktif";
        if (status === "monitoring") return "İzlemede";
        if (status === "resolved") return "Geçmiş";
        return status || "-";
    };
    const getHealthBadge = (health) => {
        if (health === "healthy") return { label: "Sorunsuz", color: "#7fbc8c", bg: "rgba(127,188,140,0.12)" };
        if (health === "error") return { label: "Hata", color: "#e24b36", bg: "rgba(226,75,54,0.12)" };
        return { label: "Kısıtlı", color: "#dda34a", bg: "rgba(221,163,74,0.12)" };
    };
    const formatDuration = (seconds) => {
        const value = Number(seconds);
        if (!Number.isFinite(value)) return "-";
        return `${value.toFixed(1)} sn`;
    };

    if (!stats) return (
        <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0a0203", color: "#d9c6b0" }}>
            <RefreshCw className="animate-spin" style={{ marginRight: 10 }} /> Yükleniyor...
        </div>
    );

    /* ──── GERÇEK VERİLERİ UI FORMATINA DÖNÜŞTÜRME ──── */

    // 1. Stat Cards
    const riskDistribution = stats.risk_distribution || {};
    const alerts = stats.alerts || {};
    const weatherSummary = stats.weather_summary || {};
    const cityStats = Array.isArray(stats.city_stats) ? stats.city_stats : [];
    const trendStats = Array.isArray(stats.trend) ? stats.trend : [];
    const sortedCityStats = [...cityStats].sort((a, b) => (b.total || 0) - (a.total || 0));
    const totalML = (riskDistribution.CRITICAL || 0) + (riskDistribution.HIGH || 0) + (riskDistribution.MEDIUM || 0);
    const activeAlerts = alerts.active || 0;
    
    const statCards = [
        { icon: Satellite, label: "Aktif Veri Servisleri", value: "NASA", unit: "", color: "#d9c6b0", border: "rgba(255,255,255,0.08)", bg: "rgba(255,255,255,0.02)", sub: "VIIRS SNPP/NOAA-20/NOAA-21" },
        { icon: Thermometer, label: "Son 48 Saatte Tespit Edilen", value: recentHotspotCount, unit: "tespit", color: "#dda34a", border: "rgba(221,163,74,0.12)", bg: "rgba(221,163,74,0.06)", sub: "Son 48 saat" },
        { icon: Flame, label: "ML Risk Tespiti", value: totalML, unit: "nokta", color: "#e24b36", border: "rgba(226,75,54,0.15)", bg: "rgba(226,75,54,0.05)", sub: "Yüksek/Orta Dereceli" },
        { icon: CheckCircle, label: "Doğrulanan Alarmlar", value: activeAlerts, unit: "alarm", color: "#d9c6b0", border: "rgba(255,255,255,0.08)", bg: "rgba(255,255,255,0.02)", sub: "Aktif risk bildirimleri" },
    ];

    // 2. Trend (Son 7 Gün)
    const trendByDate = new Map(trendStats.map((item) => [item.date, item.count || 0]));
    const latestTrendDate = trendStats.length
        ? new Date(trendStats[trendStats.length - 1].date)
        : new Date();
    const fireByMonthData = Array.from({ length: 7 }, (_, index) => {
        const dateObj = new Date(latestTrendDate);
        dateObj.setDate(latestTrendDate.getDate() - (6 - index));
        const dateKey = dateObj.toISOString().slice(0, 10);
        return {
            ay: dateObj.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
            yangin: trendByDate.get(dateKey) || 0
        };
    });

    // 3. Şehir Dağılımı (Pie Chart) -- En çok hotspot olan ilk 5-6 şehir
    let regionRiskData = sortedCityStats.slice(0, 5).map((city, idx) => ({
        name: city.city,
        value: city.total,
        color: COLORS[idx % COLORS.length]
    }));
    if (regionRiskData.length === 0) {
        regionRiskData = [{ name: "Veri Bekleniyor", value: 1, color: "#d9c6b0" }];
    }

    // 4. Model özellik gruplarının yangın riski tahminine katkı oranları
    const sampledHotspots = stats.sampled_hotspots || 0;
    const maxSignalRisk = sampledHotspots
        ? Math.round((totalML / sampledHotspots) * 100)
        : 0;
    const avgTemp = weatherSummary.avg_temp || 0;
    const avgWind = weatherSummary.avg_wind || 0;
    
    const riskFactors = [
        { faktor: "Uydu / Kaynak / Algılama Bilgisi", deger: 53.62 },
        { faktor: "Zaman ve Yangın Sezonu Bilgisi", deger: 24.46 },
        { faktor: "Meteorolojik ve Kuraklık Faktörleri", deger: 11.18 },
        { faktor: "Konum / Harita Bilgisi", deger: 7.05 },
        { faktor: "Yakın Hotspot Geçmişi", deger: 3.68 },
    ];
    const citySummaryMetrics = [
        { icon: AlertTriangle, label: "Toplam Alarm", value: activeAlerts, color: "#dda34a" },
        { icon: Wind, label: "Ort. Rüzgar", value: `${avgWind} m/s`, color: "#d9c6b0" },
        { icon: Thermometer, label: "Ort. Sıcaklık", value: `${avgTemp}°C`, color: "#d9c6b0" },
    ];
    const sourceItems = Array.isArray(sourceStats?.sources) ? sourceStats.sources : [];
    const clusterItems = Array.isArray(clusterStats?.clusters) ? clusterStats.clusters.slice(0, 2) : [];
    const healthBadge = getHealthBadge(systemHealth?.health);
    const healthFetch = systemHealth?.last_fetch || {};
    const healthSources = systemHealth?.sources || {};
    const formatRiskLevel = (level) => {
        if (level === "CRITICAL") return "Kritik";
        if (level === "HIGH") return "Yüksek";
        if (level === "MEDIUM") return "Orta";
        if (level === "WATCH") return "İzleme";
        if (level === "LOW") return "Düşük";
        if (level === "UNKNOWN" || level === "PENDING") return "Bekleniyor";
        return level || "Bekleniyor";
    };
    const healthMetricItems = [
        ["Alınan", healthFetch.received_count],
        ["Yeni", healthFetch.inserted_count],
        ["Tekrarlı", healthFetch.duplicate_count],
        ["Risk Tahmini", healthFetch.v3_prediction_count],
    ];
    const sourceStatusText = (status) => (status === "ok" ? "Sorunsuz" : "Hata");
    const getSourceHealthStatus = (sourceName) => {
        const item = healthSources?.[sourceName];
        if (!item) return null;
        return {
            label: sourceStatusText(item.status),
            color: item.status === "ok" ? "#7fbc8c" : "#e24b36",
        };
    };

    return (
        <div className="risk-analysis-page flex flex-col"
            style={{
                minHeight: "calc(100svh - 56px)",
                marginTop: 56,
                display: "flex",
                flexDirection: "column",
                overflow: "visible",
                background: "#020101",
                fontFamily: "'Inter', system-ui, sans-serif",
                color: "#ffffff",
            }}>
            {/* HEADER */}
            <div className="risk-analysis-header shrink-0 flex items-center justify-between px-5 py-3"
                style={{ background: "#0a0203", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                <div className="risk-analysis-title-wrap flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg"
                        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}>
                        <Brain size={16} color="#d9c6b0" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span style={{ fontSize: 14, color: "#ffffff", letterSpacing: 1, fontWeight: "bold" }}>RİSK ANALİZ</span>
                            <span className="px-1.5 py-0.5 rounded flex items-center gap-1" style={{ fontSize: 9, background: "rgba(255,255,255,0.1)", color: "#d9c6b0", letterSpacing: 1 }}>
                                <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#dda34a" }} />
                                CANLI
                            </span>
                        </div>
                        <div style={{ fontSize: 10, color: "#7fbc8c", letterSpacing: 1 }}>VERİ PANELİ · Son durum: {lastUpdate}</div>
                    </div>
                </div>
            </div>

            {/* CONTENT */}
            <div className="risk-analysis-content flex-1 min-h-0 px-3 py-2 flex flex-col gap-2"
                style={{ flex: "1 1 auto", minHeight: 0, display: "flex", flexDirection: "column", gap: 8, padding: "8px 12px", overflow: "visible" }}>
                <AnimatePresence>
                    {loading && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-50 flex items-center justify-center"
                            style={{ background: "rgba(2, 1, 1,0.8)", backdropFilter: "blur(4px)" }}>
                            <div className="flex flex-col items-center gap-3">
                                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                                    <RefreshCw size={32} color="#d9c6b0" />
                                </motion.div>
                                <span style={{ fontSize: 12, color: "#d9c6b0", letterSpacing: 2 }}>VERİ YENİLENİYOR...</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* STAT CARDS */}
                <div className="risk-stat-grid grid grid-cols-2 lg:grid-cols-4 gap-2 shrink-0"
                    style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, flexShrink: 0 }}>
                    {statCards.map((card, i) => (
                        <motion.div key={card.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.08 }} className="risk-stat-card rounded-xl p-3 flex flex-col gap-1 relative overflow-hidden"
                            style={{ background: card.bg, border: `1px solid ${card.border}` }}>
                            <div className="absolute top-0 left-0 right-0" style={{ height: 1, background: `linear-gradient(90deg, transparent, ${card.color}, transparent)` }} />
                            <div className="flex items-center justify-between">
                                <div className="flex items-center justify-center rounded-lg"
                                    style={{ width: 28, height: 28, background: `${card.color}18`, border: `1px solid ${card.color}33` }}>
                                    <card.icon size={13} color={card.color} />
                                </div>
                            </div>
                            <div style={{ marginTop: 6 }}>
                                <div style={{ fontSize: 10, color: "#d9c6b0", letterSpacing: 0.5 }}>{card.label}</div>
                                <div className="flex items-baseline gap-1 mt-1">
                                    <motion.span key={animKey} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                                        style={{ fontSize: 26, color: card.color, lineHeight: 1, fontWeight: "bold" }}>{card.value}</motion.span>
                                    <span style={{ fontSize: 10, color: "#7fbc8c" }}>{card.unit}</span>
                                </div>
                                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.4)", marginTop: 4 }}>{card.sub}</div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {/* CHARTS ROW */}
                <div className="risk-chart-grid grid grid-cols-1 lg:grid-cols-3 gap-2" style={{ display: "grid", gridTemplateColumns: "1fr 0.78fr 1fr", gap: 8, flex: 1, minHeight: 0 }}>
                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                        className="risk-panel risk-chart-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203", display: "flex", flexDirection: "column" }}>
                        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <TrendingUp size={13} color="#d9c6b0" />
                            <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>Son 7 Günlük Tespit Aktivitesi</span>
                        </div>
                        <div className="risk-chart-body p-2" style={{ flex: 1 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={fireByMonthData} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis dataKey="ay" tick={{ fill: "#7fbc8c", fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: "#7fbc8c", fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend wrapperStyle={{ fontSize: 10, color: "#7fbc8c", paddingTop: 4 }} formatter={() => "Sıcak Nokta Sayısı"} />
                                    <Line type="monotone" dataKey="yangin" name="Aktivite" stroke="#e24b36" strokeWidth={2} dot={{ fill: "#e24b36", r: 3 }} activeDot={{ r: 5, fill: "#ffffff" }} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </motion.div>

                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.34 }}
                        className="risk-panel system-summary-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203", display: "flex", flexDirection: "column", minHeight: 0 }}>
                        <div className="flex items-center justify-between gap-2 px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <div className="flex items-center gap-2">
                                <Brain size={13} color="#d9c6b0" />
                                <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>Sistem Durumu</span>
                            </div>
                            <span
                                className="rounded-full px-2 py-0.5"
                                style={{ fontSize: 9, color: healthBadge.color, background: healthBadge.bg, border: `1px solid ${healthBadge.color}44` }}
                            >
                                {healthBadge.label}
                            </span>
                        </div>
                        <div className="system-summary-body">
                            {systemHealthLoading ? (
                                <div style={{ fontSize: 10, color: "#d9c6b0" }}>Sistem durumu yükleniyor...</div>
                            ) : systemHealthError ? (
                                <div style={{ fontSize: 10, color: "#dda34a" }}>Sistem sağlık bilgisi alınamadı</div>
                            ) : (
                                <>
                                    <div className="system-summary-line">
                                        <span>İşlem Süresi</span>
                                        <strong>{formatDuration(healthFetch.duration_seconds)}</strong>
                                    </div>
                                    <div className="system-summary-metric-grid">
                                        {healthMetricItems.map(([label, value]) => (
                                            <div key={label} className="system-summary-metric">
                                                <span>{label}</span>
                                                <strong>{value ?? 0}</strong>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    </motion.div>

                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.38 }}
                        className="risk-panel risk-chart-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203", display: "flex", flexDirection: "column" }}>
                        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <MapPin size={13} color="#d9c6b0" />
                            <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>En Yoğun Gösterilen Şehirler</span>
                        </div>
                        <div className="city-density-body">
                            <div className="risk-pie-body flex items-center p-3 gap-4" style={{ flex: 1 }}>
                                <ResponsiveContainer width="50%" height="100%">
                                    <PieChart>
                                        <Pie data={regionRiskData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={4} dataKey="value" startAngle={90} endAngle={-270}>
                                            {regionRiskData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
                                            ))}
                                        </Pie>
                                        <Tooltip content={({ active, payload }) => {
                                            if (!active || !payload?.length) return null;
                                            const d = payload[0].payload;
                                            return (<div className="rounded-lg px-2 py-1.5" style={{ background: "rgba(10, 2, 3, 0.95)", border: "1px solid rgba(255,255,255,0.1)", fontSize: 11 }}>
                                                <span style={{ color: d.color }}>{d.name}: </span><strong style={{ color: d.color }}>{d.value} tespit</strong>
                                            </div>);
                                        }} />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="flex flex-col gap-3 flex-1">
                                    {regionRiskData.map((r) => (
                                        <div key={r.name} className="flex items-center justify-between pr-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: r.color }} />
                                                <span style={{ fontSize: 11, color: "#d9c6b0", flex: 1 }}>{r.name}</span>
                                            </div>
                                            <span style={{ fontSize: 11, color: r.color, fontWeight: "bold" }}>{r.value}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="city-density-metrics">
                                {citySummaryMetrics.map((item) => (
                                    <div key={item.label} className="city-density-metric">
                                        <div className="flex items-center justify-center rounded-md shrink-0">
                                            <item.icon size={11} color={item.color} />
                                        </div>
                                        <span>{item.label}</span>
                                        <strong>{item.value}</strong>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* BOTTOM ROW */}
                <div className="risk-bottom-grid grid grid-cols-1 lg:grid-cols-3 gap-2" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, flex: 1, minHeight: 0 }}>
                    {/* Risk Factors */}
                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.46 }}
                        className="risk-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203" }}>
                        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <AlertTriangle size={13} color="#d9c6b0" />
                            <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>Model Özellik Grubu Etki Oranları</span>
                        </div>
                        <div className="p-4 flex flex-col gap-3.5">
                            {riskFactors.map((f, i) => {
                                const c = f.deger >= 75 ? "#e24b36" : f.deger >= 55 ? "#dda34a" : "#7fbc8c";
                                return (
                                    <div key={f.faktor}>
                                        <div className="flex justify-between mb-1.5">
                                            <span style={{ fontSize: 10, color: "#d9c6b0" }}>{f.faktor}</span>
                                            <span style={{ fontSize: 10, color: c }}>%{f.deger.toFixed(2)} Etki</span>
                                        </div>
                                        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                                            <motion.div initial={{ width: 0 }} animate={{ width: `${f.deger}%` }}
                                                transition={{ duration: 0.9, delay: 0.5 + i * 0.08, ease: "easeOut" }}
                                                className="h-full rounded-full" style={{ background: `linear-gradient(90deg, ${c}, ${c}88)` }} />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </motion.div>

                    {/* Satellite Source Status */}
                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.58 }}
                        className="risk-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203" }}>
                        <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                            <Satellite size={13} color="#d9c6b0" />
                            <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>Uydu Kaynağı Durumu</span>
                        </div>
                        <div className="flex flex-col" style={{ minHeight: 0 }}>
                            {sourceStatsError ? (
                                <div className="px-4 py-5" style={{ fontSize: 11, color: "#dda34a" }}>Uydu kaynak durumu alınamadı</div>
                            ) : sourceItems.length === 0 ? (
                                <div className="px-4 py-5" style={{ fontSize: 11, color: "#d9c6b0" }}>Kaynak verisi bekleniyor</div>
                            ) : (
                                sourceItems.map((source) => {
                                    const status = getSourceStatus(source.hours_since_latest_observation);
                                    const healthStatus = getSourceHealthStatus(source.firms_source);
                                    return (
                                        <div key={`${source.firms_source}-${source.satellite}`} className="px-4 py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                            <div className="flex items-center justify-between gap-2">
                                                <span style={{ fontSize: 10, color: "#ffffff", fontWeight: 700 }}>{source.firms_source}</span>
                                                <span style={{ fontSize: 9, color: status.color }}>{status.label}</span>
                                            </div>
                                            <div className="flex items-center justify-between mt-1.5">
                                                <span style={{ fontSize: 9, color: "#7fbc8c" }}>
                                                    Uydu: {source.satellite || "?"}
                                                    {healthStatus && (
                                                        <span style={{ color: healthStatus.color }}> · {healthStatus.label}</span>
                                                    )}
                                                </span>
                                                <span style={{ fontSize: 9, color: "#d9c6b0" }}>{source.total_hotspots || 0} tespit</span>
                                            </div>
                                            <div className="flex items-center justify-between mt-1">
                                                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.45)" }}>Son: {formatObservationTime(source.latest_observation_trt)}</span>
                                                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.45)" }}>
                                                    {Number.isFinite(Number(source.hours_since_latest_observation))
                                                        ? `${Number(source.hours_since_latest_observation).toFixed(1)} saat`
                                                        : "-"}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </motion.div>

                    {/* AI Analysis Panel */}
                    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.62 }}
                        className="risk-panel data-analysis-panel rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0a0203", display: "flex", flexDirection: "column", minHeight: 0 }}>
                        <div className="data-analysis-header">
                            <div className="flex items-center gap-2">
                                <Brain size={13} color="#d9c6b0" />
                                <span style={{ fontSize: 11, color: "#d9c6b0", letterSpacing: 0.5 }}>Yangın Grubu Özeti</span>
                            </div>
                            <span className="data-analysis-risk-rate">%{maxSignalRisk}</span>
                        </div>
                        <div className="data-analysis-body">
                            <div className="data-analysis-clusters">
                                <div className="flex items-center justify-between">
                                    <span style={{ fontSize: 11, color: "#d9c6b0" }}>Yangın Grupları</span>
                                    <span style={{ fontSize: 11, color: "#dda34a", fontWeight: 700 }}>{clusterStats?.returned_count ?? 0}/{clusterStats?.cluster_count ?? 0}</span>
                                </div>
                                <div className="grid grid-cols-4 gap-1">
                                    {clusterFilterOptions.map((option) => (
                                        <button
                                            key={option.value}
                                            type="button"
                                            onClick={() => setClusterStatusFilter(option.value)}
                                            className="rounded"
                                            style={{
                                                padding: "4px 2px",
                                                fontSize: 8,
                                                color: clusterStatusFilter === option.value ? "#020101" : "#d9c6b0",
                                                background: clusterStatusFilter === option.value ? "#dda34a" : "rgba(255,255,255,0.045)",
                                                border: "1px solid rgba(255,255,255,0.08)",
                                                lineHeight: 1.1,
                                            }}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                                {clusterStats?.status_counts && (
                                    <div className="data-analysis-status-counts">
                                        <span>Aktif: {clusterStats.status_counts.active || 0}</span>
                                        <span>İzlemede: {clusterStats.status_counts.monitoring || 0}</span>
                                        <span>Geçmiş: {clusterStats.status_counts.resolved || 0}</span>
                                    </div>
                                )}
                                {clusterStatsError ? (
                                    <div style={{ fontSize: 10, color: "#dda34a" }}>Yangın grubu durumu alınamadı</div>
                                ) : clusterItems.length === 0 ? (
                                    <div style={{ fontSize: 10, color: "#7fbc8c" }}>Seçili filtrede yangın grubu yok</div>
                                ) : (
                                    clusterItems.map((cluster) => (
                                        <div key={cluster.id} className="data-analysis-cluster-card">
                                            <div className="flex items-center justify-between gap-2">
                                                <span style={{ fontSize: 10, color: "#ffffff", fontWeight: 700 }}>Grup #{cluster.id}</span>
                                                <span style={{ fontSize: 10, color: cluster.max_risk_level === "CRITICAL" ? "#e24b36" : "#dda34a" }}>{formatRiskLevel(cluster.max_risk_level)}</span>
                                            </div>
                                            <div className="flex items-center justify-between mt-1">
                                                <span style={{ fontSize: 9, color: "#7fbc8c" }}>{cluster.hotspot_count} tespit</span>
                                                <span style={{ fontSize: 9, color: "#d9c6b0" }}>
                                                    Risk: {cluster.max_fire_probability != null ? Number(cluster.max_fire_probability).toFixed(2) : "-"}
                                                </span>
                                            </div>
                                            <div className="mt-1" style={{ fontSize: 9, color: "rgba(255,255,255,0.45)" }}>
                                                Durum: {getClusterStatusLabel(cluster.status)}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </motion.div>
                </div>

            </div>
        </div>
    );
}
