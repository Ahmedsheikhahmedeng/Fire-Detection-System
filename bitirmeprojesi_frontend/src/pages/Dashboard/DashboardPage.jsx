import { createElement, useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { API_BASE_URL, WS_BASE_URL } from "../../services/api";
import { formatRelativeTimestamp } from "../../utils/time";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  AreaChart, Area
} from "recharts";
import {
  Flame, Thermometer, Droplets, Wind,
  AlertTriangle, MapPin, TrendingUp, Shield, Activity
} from "lucide-react";

const RISK_COLORS = { HIGH: "#780115", MEDIUM: "#F7B638", LOW: "#F7B638" };
const API = API_BASE_URL;

/* ── Stat Card ── */
function StatCard({ icon, label, value, sub, color, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5 }}
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: "20px 24px",
        display: "flex",
        alignItems: "center",
        gap: 16,
        backdropFilter: "blur(12px)",
      }}
    >
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: `${color}15`,
        display: "flex", alignItems: "center", justifyContent: "center"
      }}>
        {createElement(icon, { size: 22, color })}
      </div>
      <div>
        <div style={{ fontSize: 11, color: "#F7B638", fontWeight: 500, textTransform: "uppercase", letterSpacing: 1 }}>
          {label}
        </div>
        <div style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", lineHeight: 1.2 }}>
          {value}
        </div>
        {sub && <div style={{ fontSize: 11, color: "#F7B638", marginTop: 2 }}>{sub}</div>}
      </div>
    </motion.div>
  );
}

/* ── Pie Chart Card ── */
function RiskPieChart({ data }) {
  const chartData = [
    { name: "Yüksek", value: data.HIGH || 0, color: RISK_COLORS.HIGH },
    { name: "Orta", value: data.MEDIUM || 0, color: RISK_COLORS.MEDIUM },
    { name: "Düşük", value: data.LOW || 0, color: RISK_COLORS.LOW },
  ].filter(d => d.value > 0);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: 24,
        backdropFilter: "blur(12px)",
      }}
    >
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#F7B638", marginBottom: 16 }}>
        🎯 Risk Dağılımı
      </h3>
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <ResponsiveContainer width="60%" height={180}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              cx="50%" cy="50%"
              innerRadius={45} outerRadius={75}
              paddingAngle={3}
              stroke="none"
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "rgba(18, 0, 5,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#ffffff",
                fontSize: 12
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {chartData.map((d, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: d.color }} />
              <span style={{ fontSize: 12, color: "#F7B638" }}>{d.name}: <b style={{ color: "#ffffff" }}>{d.value}</b></span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ── Trend Chart ── */
function TrendChart({ data }) {
  const formatted = data.map(d => ({
    ...d,
    date: d.date ? d.date.slice(5) : ""  // "2026-04-08" → "04-08"
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.6 }}
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: 24,
        backdropFilter: "blur(12px)",
      }}
    >
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#F7B638", marginBottom: 16 }}>
        📈 Son 7 Gün — Hotspot Trendi
      </h3>
      {formatted.length > 0 ? (
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={formatted}>
            <defs>
              <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F7B638" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#F7B638" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="date" tick={{ fill: "#F7B638", fontSize: 11 }} />
            <YAxis tick={{ fill: "#F7B638", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "rgba(18, 0, 5,0.95)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#ffffff",
                fontSize: 12
              }}
            />
            <Area type="monotone" dataKey="count" stroke="#F7B638" fill="url(#trendGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center", color: "#F7B638", fontSize: 13 }}>
          Trend verisi henüz yok
        </div>
      )}
    </motion.div>
  );
}

/* ── City Table ── */
function CityTable({ data }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4, duration: 0.6 }}
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: 24,
        backdropFilter: "blur(12px)",
        overflow: "hidden",
      }}
    >
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#F7B638", marginBottom: 16 }}>
        🏙️ Şehir Bazlı Risk Analizi
      </h3>
      <div style={{ overflowY: "auto", maxHeight: 260 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ color: "#F7B638", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <th style={{ textAlign: "left", padding: "8px 0", fontWeight: 500 }}>Şehir</th>
              <th style={{ textAlign: "center", padding: "8px 0", fontWeight: 500 }}>Toplam</th>
              <th style={{ textAlign: "center", padding: "8px 0", fontWeight: 500 }}>🔴</th>
              <th style={{ textAlign: "center", padding: "8px 0", fontWeight: 500 }}>🟠</th>
              <th style={{ textAlign: "center", padding: "8px 0", fontWeight: 500 }}>🟢</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} style={{
                borderBottom: "1px solid rgba(255,255,255,0.03)",
                color: "#ffffff"
              }}>
                <td style={{ padding: "8px 0", display: "flex", alignItems: "center", gap: 6 }}>
                  <MapPin size={12} color="#F7B638" />
                  {row.city}
                </td>
                <td style={{ textAlign: "center", fontWeight: 600 }}>{row.total}</td>
                <td style={{ textAlign: "center", color: RISK_COLORS.HIGH, fontWeight: 600 }}>{row.HIGH || 0}</td>
                <td style={{ textAlign: "center", color: RISK_COLORS.MEDIUM, fontWeight: 600 }}>{row.MEDIUM || 0}</td>
                <td style={{ textAlign: "center", color: RISK_COLORS.LOW, fontWeight: 600 }}>{row.LOW || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

/* ── City Bar Chart ── */
function CityBarChart({ data }) {
  const top5 = data.slice(0, 5);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.6 }}
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        padding: 24,
        backdropFilter: "blur(12px)",
      }}
    >
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#F7B638", marginBottom: 16 }}>
        📊 En Çok Hotspot Bulunan Şehirler
      </h3>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={top5} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis type="number" tick={{ fill: "#F7B638", fontSize: 11 }} />
          <YAxis dataKey="city" type="category" width={80} tick={{ fill: "#F7B638", fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              background: "rgba(18, 0, 5,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 8,
              color: "#ffffff",
              fontSize: 12
            }}
          />
          <Bar dataKey="total" fill="#F7B638" radius={[0, 6, 6, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </motion.div>
  );
}

/* ══════════════════════════════════════════════ */
/*                MAIN DASHBOARD                  */
/* ══════════════════════════════════════════════ */
export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, statusRes] = await Promise.all([
          axios.get(`${API}/map/stats`, { timeout: 5000 }),
          axios.get(`${API}/map/status`, { timeout: 3000 }),
        ]);
        setStats(statsRes.data);
        setStatus(statusRes.data);
      } catch (e) {
        console.error("Dashboard veri hatası:", e);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
    const pollInterval = setInterval(fetchAll, 60000);

    // WebSocket — gerçek zamanlı güncellemeler + auto-reconnect
    let ws;
    let reconnectTimer;

    function connectWs() {
      try {
        ws = new WebSocket(`${WS_BASE_URL}/alerts/ws`);

        ws.onclose = () => {
          reconnectTimer = setTimeout(connectWs, 5000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "HOTSPOT_UPDATED" || data.type === "NEW_FIRE_ALERT") {
              fetchAll();
            }
          } catch {
            // Sessizce yoksay
          }
        };
      } catch {
        reconnectTimer = setTimeout(connectWs, 5000);
      }
    }

    connectWs();

    return () => {
      clearInterval(pollInterval);
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  if (loading || !stats) {
    return (
      <div style={{
        minHeight: "100vh", background: "#120005",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#F7B638", fontSize: 16
      }}>
        <Activity size={20} style={{ marginRight: 8, animation: "spin 1s linear infinite" }} />
        Dashboard yükleniyor...
      </div>
    );
  }

  const { risk_distribution: risk, city_stats, trend, weather_summary: ws, alerts } = stats;
  const totalML = (risk.HIGH || 0) + (risk.MEDIUM || 0) + (risk.LOW || 0);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#120005",
      fontFamily: "'Inter', system-ui, sans-serif",
      color: "#ffffff",
      padding: "80px 24px 40px",
    }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>

        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ marginBottom: 32 }}
        >
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", display: "flex", alignItems: "center", gap: 10 }}>
            <Activity size={28} color="#F7B638" />
            Yangın İzleme Dashboard
          </h1>
          <p style={{ fontSize: 13, color: "#F7B638", marginTop: 4 }}>
            Gerçek zamanlı istatistikler • Son güncelleme: {
              status?.last_ml_display_at || status?.last_ml_scan || status?.last_prediction_at
                ? formatRelativeTimestamp(status.last_ml_display_at || status.last_ml_scan || status.last_prediction_at)
                : "Henüz veri yok"
            }
          </p>
        </motion.div>

        {/* Stat Cards Row */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}>
          <StatCard icon={Flame} label="Toplam Hotspot" value={stats.total_hotspots} color="#F7B638" delay={0} />
          <StatCard icon={Shield} label="ML İşlenen" value={totalML} sub={`${risk.HIGH} yüksek risk`} color="#F7B638" delay={0.1} />
          <StatCard icon={AlertTriangle} label="Aktif Alarm" value={alerts.active} sub={`${alerts.total} toplam`} color="#780115" delay={0.2} />
          <StatCard icon={Thermometer} label="Ort. Sıcaklık" value={`${ws.avg_temp}°C`} sub={`${ws.min_temp}° — ${ws.max_temp}°`} color="#F7B638" delay={0.3} />
          <StatCard icon={Droplets} label="Ort. Nem" value={`%${ws.avg_humidity}`} color="#F7B638" delay={0.4} />
          <StatCard icon={Wind} label="Ort. Rüzgar" value={`${ws.avg_wind} m/s`} color="#F7B638" delay={0.5} />
        </div>

        {/* Charts Grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
          gap: 20,
          marginBottom: 24,
        }}>
          <RiskPieChart data={risk} />
          <TrendChart data={trend} />
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
          gap: 20,
        }}>
          <CityTable data={city_stats} />
          <CityBarChart data={city_stats} />
        </div>
      </div>
    </div>
  );
}
