import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import axios from "axios";
import { Flame, Bell, BellOff, AlertTriangle, CheckCircle, Satellite, ShieldAlert, Info } from "lucide-react";
import FireMap from "../../components/FireMap/FireMap";
import { SystemStatus } from "../FireDashboard/SystemStatus";
import { RecentFires } from "../FireDashboard/RecentFires";
import { API_BASE_URL } from "../../services/api";
import "./MonitoringSection.css";

const MAX_VISIBLE_HOURS = 24;

// ── Yardımcı fonksiyonlar ──────────────────────────────────────────────────

function formatTimeAgo(hoursAgo) {
  if (hoursAgo == null || hoursAgo === 0) return "Az önce";
  if (hoursAgo < 1) return `${Math.round(hoursAgo * 60)} dk önce`;
  if (hoursAgo < 24) return `${Math.round(hoursAgo)} saat önce`;
  return `${Math.round(hoursAgo / 24)} gün önce`;
}

function mapRiskLevel(riskLevel, alert) {
  if (alert) return "high";
  if (riskLevel === "HIGH") return "high";
  if (riskLevel === "MEDIUM") return "medium";
  if (riskLevel === "WATCH") return "watch";
  return "low";
}

function getCityLabel(city) {
  const value = typeof city === "string" ? city.trim() : "";
  return value || "Çözülüyor...";
}

function distanceKm(a, b) {
  const toRad = (value) => (Number(value) * Math.PI) / 180;
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const dLat = toRad(Number(b.latitude) - Number(a.latitude));
  const dLng = toRad(Number(b.longitude) - Number(a.longitude));
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function countNearbyHotspots(spot, hotspots) {
  if (
    !Number.isFinite(Number(spot.latitude)) ||
    !Number.isFinite(Number(spot.longitude))
  ) {
    return 0;
  }

  return hotspots.filter((candidate) => {
    if (candidate.id === spot.id) return false;
    if (
      !Number.isFinite(Number(candidate.latitude)) ||
      !Number.isFinite(Number(candidate.longitude))
    ) {
      return false;
    }

    return distanceKm(spot, candidate) <= 18;
  }).length;
}

function formatObservationLabel(value) {
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
}

function transformHotspot(spot, allHotspots = []) {
  const risk = mapRiskLevel(spot.risk_level, spot.alert);
  const riskPercent =
    spot.risk_percent ?? (spot.fire_probability ? Math.round(spot.fire_probability * 100) : 0);

  return {
    id: spot.id,
    name: getCityLabel(spot.city),
    region: "Türkiye",
    lat: spot.latitude,
    lng: spot.longitude,
    nearbyHotspotCount: countNearbyHotspots(spot, allHotspots),
    risk,
    intensity: riskPercent,
    riskPercent,
    brightness: spot.brightness,
    time: formatTimeAgo(spot.hours_ago),
    hoursAgo: Number.isFinite(spot.hours_ago) ? Number(spot.hours_ago) : Number.POSITIVE_INFINITY,
    temp: spot.temperature != null ? Math.round(spot.temperature) : "N/A",
    wind: spot.wind_speed != null ? Math.round(spot.wind_speed) : "N/A",
    humidity: spot.humidity != null ? Math.round(spot.humidity) : "N/A",
    active: spot.alert || false,
    direction: spot.spread_direction || "Bilinmiyor",
    clusterId: spot.cluster_id,
    clusterStatus: spot.cluster_status,
    observedLabel: formatObservationLabel(spot.observed_at),
    mlSource: spot.ml_source || "unknown",
  };
}

// ── ML verisinden dinamik alarm üret ──────────────────────────────────────

function buildAlarmsFromData(hotspots) {
  const critical = hotspots.filter((s) => s.alert && s.risk_percent != null);
  const high = hotspots.filter((s) => !s.alert && s.risk_level === "HIGH");

  const alarms = [];

  critical.forEach((s) => {
    const city = getCityLabel(s.city);
    alarms.push({
      id: `crit-${s.id}`,
      level: "critical",
      message: s.alert_message ||
        `🔥 KRİTİK: ${city} bölgesinde %${s.risk_percent} yangın ihtimali!`,
      lat: s.latitude,
      lng: s.longitude,
    });
  });

  high.forEach((s) => {
    const city = getCityLabel(s.city);
    alarms.push({
      id: `high-${s.id}`,
      level: "warning",
      message: s.alert_message ||
        `⚠️ YÜKSEK RİSK: ${city} — %${s.risk_percent} yangın riski`,
      lat: s.latitude,
      lng: s.longitude,
    });
  });

  if (alarms.length === 0) {
    return [];
  }

  return alarms;
}

// ── Bileşen ───────────────────────────────────────────────────────────────

export default function MonitoringSection() {
  const [fireLocations, setFireLocations] = useState([]);
  const [rawHotspots, setRawHotspots] = useState([]);
  const [isMapLoading, setIsMapLoading] = useState(true);
  const [selectedFire, setSelectedFire] = useState(null);
  const [alarmIndex, setAlarmIndex] = useState(0);
  const [alarmsEnabled, setAlarmsEnabled] = useState(true);
  const [showAlarm, setShowAlarm] = useState(true);
  const [alarms, setAlarms] = useState([
    { id: "loading", level: "info", message: "📡 ML modeli yükleniyor..." },
  ]);
  const prevAlertIdsRef = useRef(new Set());

  // ── Veri çekme ────────────────────────────────────────────────────────

  const fetchHotspots = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/map/hotspots`, { timeout: 8000 });
      const raw = Array.isArray(res.data)
        ? res.data.filter((spot) => {
            const hours = Number(spot.hours_ago);
            return Number.isFinite(hours) && hours <= MAX_VISIBLE_HOURS;
          })
        : [];

      setRawHotspots(raw);
      const transformed = raw.map((spot) => transformHotspot(spot, raw));
      transformed.sort((a, b) => b.intensity - a.intensity);
      setFireLocations(transformed);

      const newAlarms = buildAlarmsFromData(raw);
      setAlarms(newAlarms);

      const newAlertIds = new Set(
        raw.filter((s) => s.alert).map((s) => s.id)
      );
      const hasNew = [...newAlertIds].some(
        (id) => !prevAlertIdsRef.current.has(id)
      );
      if (hasNew) {
        setAlarmIndex(0);
        setShowAlarm(true);
      }
      prevAlertIdsRef.current = newAlertIds;
    } catch (e) {
      console.error("Backend bağlantı hatası:", e);
    } finally {
      setIsMapLoading(false);
    }
  }, []);

  // ── İlk yükleme + 60 saniyelik yenileme ──────────────────────────────

  useEffect(() => {
    const initialFetch = setTimeout(fetchHotspots, 0);
    const interval = setInterval(fetchHotspots, 60000);
    return () => {
      clearTimeout(initialFetch);
      clearInterval(interval);
    };
  }, [fetchHotspots]);

  // ── Alarm döngüsü ─────────────────────────────────────────────────────

  useEffect(() => {
    if (!alarmsEnabled || alarms.length <= 1) return;
    const interval = setInterval(() => {
      setAlarmIndex((i) => (i + 1) % alarms.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [alarmsEnabled, alarms]);

  const activeAlarm = alarms[alarmIndex] || alarms[0];

  const handleSelectFire = useCallback((fireId) => {
    setSelectedFire(fireId);
  }, []);

  // ── Banner renkleri ───────────────────────────────────────────────────

  const bannerStyle = {
    critical: {
      bg: "#780115",
      border: "#d42b3f",
      icon: <ShieldAlert size={14} />,
    },
    warning: {
      bg: "#2b0008",
      border: "#f7b638",
      icon: <AlertTriangle size={14} />,
    },
    info: {
      bg: "#193824",
      border: "#7fbc8c",
      icon: <Info size={14} />,
    },
  };

  const currentStyle = bannerStyle[activeAlarm?.level] || bannerStyle.info;

  return (
    <div className="monitoring-section">
      {/* ─── ALARM BANNER ─────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {alarmsEnabled && showAlarm && activeAlarm && (
          <motion.div
            key={activeAlarm.id}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className={`monitoring-alarm-banner monitoring-alarm-banner--${activeAlarm.level}`}
          >
            {/* İkon — kritik seviyede titreşim */}
            <div>{currentStyle.icon}</div>

            {/* Mesaj */}
            <span className="monitoring-alarm-message">{activeAlarm.message}</span>

            {/* Alarm sayacı */}
            {alarms.length > 1 && (
              <span className="monitoring-alarm-count">
                {alarmIndex + 1}/{alarms.length}
              </span>
            )}

            {/* Kontroller */}
            <button
              onClick={() => setAlarmsEnabled((v) => !v)}
              className="monitoring-alarm-icon-btn"
              title={alarmsEnabled ? "Uyarıları durdur" : "Uyarıları başlat"}
            >
              {alarmsEnabled ? <BellOff size={12} /> : <Bell size={12} />}
            </button>
            <button
              onClick={() => setShowAlarm(false)}
              className="monitoring-alarm-close"
            >
              KAPAT
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── ANA İÇERİK ───────────────────────────────────────────────── */}
      <div className="monitoring-content">
        {/* SOL — Leaflet Harita */}
        <div className="monitoring-map-area">
          <FireMap
            focusedHotspotId={selectedFire}
            hotspotsData={rawHotspots}
            loading={isMapLoading}
            onRefreshHotspots={fetchHotspots}
            onSelectHotspot={handleSelectFire}
          />
        </div>

        {/* SAĞ — Sidebar */}
        <div className="monitoring-sidebar">
          <SystemStatus />
          <RecentFires
            fires={fireLocations}
            selectedFire={selectedFire}
            onSelectFire={handleSelectFire}
          />
        </div>
      </div>
    </div>
  );
}
