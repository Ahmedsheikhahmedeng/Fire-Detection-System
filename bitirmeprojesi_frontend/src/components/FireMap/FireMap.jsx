import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import axios from "axios";
import { Circle, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import { toast } from "react-hot-toast";
import L from "leaflet";
import { Layers, Moon, Sun, X } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { FireDetailCard } from "./FireDetailCard";
import { formatRelativeTimestamp } from "../../utils/time";
import { API_BASE_URL, WS_BASE_URL } from "../../services/api";
import "./FireMap.css";

const MAX_VISIBLE_HOURS = 24;
const MAP_THEMES = {
  night: {
    label: "Gece",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  morning: {
    label: "Sabah",
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
};

function formatTimeAgo(hoursAgo) {
  const hours = Number(hoursAgo);
  if (!Number.isFinite(hours) || hours <= 0) return "Az önce";
  if (hours < 1) return `${Math.round(hours * 60)} dk önce`;
  if (hours < 24) return `${Math.round(hours)} saat önce`;
  return `${Math.round(hours / 24)} gün önce`;
}

function getCityLabel(city) {
  const value = typeof city === "string" ? city.trim() : "";
  return value || "Çözülüyor...";
}

/* ── Marker icon üreteci ───────────────────────────────────────────────── */
const createCustomIcon = (level, { burning = false, clustered = false } = {}) => {
  const styles = {
    HIGH: { color: "#e24b36", glow: "rgba(226,75,54,0.55)" },
    MEDIUM: { color: "#f7b638", glow: "rgba(247,182,56,0.42)" },
    LOW: { color: "#7fbc8c", glow: "rgba(127,188,140,0.48)" },
    UNKNOWN: { color: "#8e9385", glow: "rgba(142,147,133,0.42)" },
  };
  const style = styles[level] || styles.LOW;
  const { color, glow } = style;

  const markerHtml = `
    <div class="simple-map-marker ${burning ? "simple-map-marker--burning" : ""} ${clustered ? "simple-map-marker--clustered" : ""}" style="--pin-color: ${color}; --pin-glow: ${glow};">
      <span class="simple-map-marker-ring"></span>
      <span class="simple-map-marker-heat"></span>
      <span class="simple-map-marker-dot"></span>
    </div>
  `;

  return L.divIcon({
    className: "custom-leaflet-marker",
    html: markerHtml,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -14],
  });
};

const NEARBY_DISTANCE_KM = 18;

function distanceKm(a, b) {
  const toRad = (value) => (Number(value) * Math.PI) / 180;
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function isBurningHotspot(spot) {
  const riskPercent = Number(spot.risk_percent);
  const probability = Number(spot.fire_probability);
  return Boolean(spot.alert) || spot.risk_level === "CRITICAL" || (spot.risk_level === "HIGH" && (riskPercent >= 75 || probability >= 0.75));
}

/* ── Harita kontrolcüsü ────────────────────────────────────────────────── */
function MapController({ center, zoom, focusTarget }) {
  const map = useMap();
  useEffect(() => {
    if (center && zoom) map.setView(center, zoom, { animate: true });
  }, [center, zoom, map]);
  useEffect(() => {
    if (!focusTarget?.center || !focusTarget?.zoom) return;
    map.flyTo(focusTarget.center, focusTarget.zoom, {
      animate: true,
      duration: 1.2,
    });
  }, [focusTarget, map]);
  return null;
}

function MapResizeObserver() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();

    const refreshSize = () => {
      window.requestAnimationFrame(() => {
        map.invalidateSize({ animate: false });
      });
    };

    refreshSize();
    const timers = [120, 320, 700].map((delay) => setTimeout(refreshSize, delay));

    const resizeObserver =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(refreshSize)
        : null;

    resizeObserver?.observe(container);
    window.addEventListener("orientationchange", refreshSize);
    window.addEventListener("resize", refreshSize);

    return () => {
      timers.forEach(clearTimeout);
      resizeObserver?.disconnect();
      window.removeEventListener("orientationchange", refreshSize);
      window.removeEventListener("resize", refreshSize);
    };
  }, [map]);

  return null;
}

function MapGestureGuard() {
  const map = useMap();
  const [showHint, setShowHint] = useState(false);
  const hintTimerRef = useRef(null);

  useEffect(() => {
    const container = map.getContainer();

    const disableWheelZoom = () => {
      map.scrollWheelZoom.disable();
    };

    const enableWheelZoom = () => {
      map.scrollWheelZoom.enable();
    };

    const handleKeyDown = (event) => {
      if (event.metaKey || event.ctrlKey) enableWheelZoom();
    };

    const handleKeyUp = () => {
      disableWheelZoom();
    };

    const handleWheel = (event) => {
      if (event.metaKey || event.ctrlKey) {
        enableWheelZoom();
        return;
      }

      disableWheelZoom();
      setShowHint(true);
      window.clearTimeout(hintTimerRef.current);
      hintTimerRef.current = window.setTimeout(() => {
        setShowHint(false);
      }, 1500);
    };

    disableWheelZoom();
    container.addEventListener("wheel", handleWheel, { passive: true });
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", disableWheelZoom);

    return () => {
      window.clearTimeout(hintTimerRef.current);
      container.removeEventListener("wheel", handleWheel);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", disableWheelZoom);
    };
  }, [map]);

  return (
    <div className={`map-gesture-hint${showHint ? " map-gesture-hint--visible" : ""}`}>
      Haritayı yakınlaştırmak için Ctrl veya ⌘ tuşuna basıp kaydırın
    </div>
  );
}

/* ── ML Durum Rozeti ───────────────────────────────────────────────────── */
function MlStatusBadge({ hotspots, loading }) {
  const [lastScan, setLastScan] = useState("Henüz tarama yok");
  const modelCount = hotspots.filter((s) => s.ml_source === "model").length;
  const pendingCount = hotspots.filter((s) => s.ml_source === "pending").length;

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/map/status`, { timeout: 3000 });
        const scanAt = res.data?.last_ml_display_at || res.data?.last_ml_scan || res.data?.last_prediction_at;
        setLastScan(scanAt ? formatRelativeTimestamp(scanAt) : "Henüz tarama yok");
      } catch { /* başarısız olursa sessizce geç */ }
    };
    fetchStatus();
    const timer = setInterval(fetchStatus, 30000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="ml-status-badge">
      {loading ? (
        <>
          <span className="ml-spinner" />
          <span>Yükleniyor...</span>
        </>
      ) : (
        <>
          <span className="ml-dot-active" />
          <span>ML: {modelCount} Nokta</span>
          {pendingCount > 0 && (
            <span className="ml-no-data"> · {pendingCount} İşleniyor</span>
          )}
          <span className="ml-no-data"> · Son Tarama: {lastScan}</span>
        </>
      )}
    </div>
  );
}

/* ── Ana bileşen ────────────────────────────────────────────────────────── */
export default function FireMap({
  focusedHotspotId = null,
  hotspotsData = null,
  loading: externalLoading,
  onRefreshHotspots,
  onSelectHotspot,
}) {
  const isControlled = Array.isArray(hotspotsData);
  const [internalHotspots, setInternalHotspots] = useState([]);
  const [internalLoading, setInternalLoading] = useState(!isControlled);
  const [mapCenter] = useState([39.92, 32.85]);
  const [mapZoom] = useState(6);
  const [wsStatus, setWsStatus] = useState("connecting");
  const [focusTarget, setFocusTarget] = useState(null);
  const [showLegend, setShowLegend] = useState(true);
  const [mapTheme, setMapTheme] = useState("night");
  const markerRefs = useRef({});
  const hasLoadedRef = useRef(isControlled);
  const activeMapTheme = MAP_THEMES[mapTheme];

  const hotspots = isControlled ? hotspotsData : internalHotspots;
  const loading = externalLoading ?? internalLoading;
  const nearbyHotspotInfo = useMemo(() => {
    const clusterIds = new Set();
    const lines = [];
    const validHotspots = hotspots.filter((spot) =>
      Number.isFinite(Number(spot.latitude)) && Number.isFinite(Number(spot.longitude))
    );

    for (let i = 0; i < validHotspots.length; i += 1) {
      for (let j = i + 1; j < validHotspots.length; j += 1) {
        const first = validHotspots[i];
        const second = validHotspots[j];
        const distance = distanceKm(first, second);
        if (distance > NEARBY_DISTANCE_KM) continue;

        clusterIds.add(first.id);
        clusterIds.add(second.id);
        lines.push({
          id: `${first.id}-${second.id}`,
          positions: [
            [first.latitude, first.longitude],
            [second.latitude, second.longitude],
          ],
        });
      }
    }

    return {
      clusterIds,
      lines: lines.slice(0, 36),
    };
  }, [hotspots]);

  const fetchHotspots = useCallback(async () => {
    if (onRefreshHotspots) {
      await onRefreshHotspots();
      return;
    }

    try {
      if (!hasLoadedRef.current) setInternalLoading(true);
      const res = await axios.get(`${API_BASE_URL}/map/hotspots`, { timeout: 8000 });
      const recentHotspots = Array.isArray(res.data)
        ? res.data.filter((spot) => {
            const hours = Number(spot.hours_ago);
            return Number.isFinite(hours) && hours <= MAX_VISIBLE_HOURS;
        })
        : [];
      setInternalHotspots(recentHotspots);
      hasLoadedRef.current = true;
    } catch (e) {
      console.error("Backend bağlantı hatası:", e);
      // Hata durumunda önceki noktaları koru — silme!
    } finally {
      setInternalLoading(false);
    }
  }, [onRefreshHotspots]);

  /* İlk yükleme + WebSocket + 30s yenileme */
  useEffect(() => {
    if (!isControlled) {
      queueMicrotask(fetchHotspots);
    }

    // 30 saniyelik polling
    const pollInterval = isControlled ? null : setInterval(fetchHotspots, 60000);

    // WebSocket — gerçek zamanlı uyarılar + auto-reconnect
    let ws;
    let reconnectTimer;
    let reconnectDelay = 5000;

    function connectWs() {
      try {
        ws = new WebSocket(`${WS_BASE_URL}/alerts/ws`);

        ws.onopen = () => {
          setWsStatus("connected");
          reconnectDelay = 5000;
          if (!isControlled) fetchHotspots();
        };

        ws.onclose = () => {
          setWsStatus("disconnected");
          reconnectTimer = setTimeout(connectWs, reconnectDelay);
          reconnectDelay = Math.min(reconnectDelay * 2, 60000);
        };

        ws.onerror = () => {
          setWsStatus("disconnected");
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "NEW_FIRE_ALERT") {
              toast.error(`🚨 ${data.message}`, {
                duration: 7000,
                style: {
                  background: "rgba(12,2,5,0.97)",
                  color: "#f7efe4",
                  borderRadius: "10px",
                  border: "1px solid rgba(120,1,21,0.76)",
                  boxShadow: "0 0 20px rgba(120,1,21,0.34)",
                  fontSize: "13px",
                  maxWidth: "380px",
                },
              });
              fetchHotspots();
            }
            if (data.type === "HOTSPOT_UPDATED") {
              fetchHotspots();
            }
          } catch {
            // JSON parse hatası — sessizce geç
          }
        };
      } catch {
        setWsStatus("disconnected");
        reconnectTimer = setTimeout(connectWs, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, 60000);
      }
    }

    connectWs();

    return () => {
      if (pollInterval) clearInterval(pollInterval);
      clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [fetchHotspots, isControlled]);

  useEffect(() => {
    if (!focusedHotspotId || hotspots.length === 0) return;

    const hotspot = hotspots.find((spot) => spot.id === focusedHotspotId);
    if (!hotspot) return;

    setFocusTarget({
      id: hotspot.id,
      center: [hotspot.latitude, hotspot.longitude],
      zoom: 9,
      token: `${hotspot.id}-${hotspot.latitude}-${hotspot.longitude}`,
    });
  }, [focusedHotspotId, hotspots]);

  useEffect(() => {
    if (!focusTarget?.id) return;

    const timer = setTimeout(() => {
      const marker = markerRefs.current[focusTarget.id];
      if (marker?.openPopup) {
        marker.openPopup();
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [focusTarget]);

  return (
    <div className={`firemap-wrapper firemap-wrapper--${mapTheme}`}>
      {/* WebSocket durum göstergesi */}
      <div className={`ws-indicator ws-${wsStatus}`}>
        <span className="ws-dot" />
        {wsStatus === "connected"
          ? "CANLI"
          : wsStatus === "connecting"
          ? "BAĞLANIYOR"
          : "ÇEVRİMDIŞI"}
      </div>

      {/* ML durum rozeti */}
      <MlStatusBadge hotspots={hotspots} loading={loading} />

      <button
        type="button"
        className="map-theme-toggle"
        onClick={() => setMapTheme((theme) => (theme === "night" ? "morning" : "night"))}
        title={mapTheme === "night" ? "Sabah moduna geç" : "Gece moduna geç"}
        aria-label={mapTheme === "night" ? "Sabah moduna geç" : "Gece moduna geç"}
      >
        {mapTheme === "night" ? <Sun size={13} /> : <Moon size={13} />}
        <span>{mapTheme === "night" ? "Sabah" : "Gece"}</span>
      </button>

      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        className="firemap-container"
        zoomControl={false}
        scrollWheelZoom={false}
      >
        <MapController center={mapCenter} zoom={mapZoom} focusTarget={focusTarget} />
        <MapResizeObserver />
        <MapGestureGuard />

        <TileLayer
          key={mapTheme}
          url={activeMapTheme.url}
          attribution={activeMapTheme.attribution}
        />

        {nearbyHotspotInfo.lines.map((line) => (
          <Polyline
            key={`near-line-${line.id}`}
            positions={line.positions}
            pathOptions={{
              color: "#f7b638",
              weight: 1,
              opacity: 0.42,
              dashArray: "4 6",
              className: "nearby-hotspot-line",
            }}
          />
        ))}

        {hotspots
          .filter((spot) => nearbyHotspotInfo.clusterIds.has(spot.id))
          .map((spot) => (
            <Circle
              key={`near-area-${spot.id}`}
              center={[spot.latitude, spot.longitude]}
              radius={12500}
              pathOptions={{
                color: "#f7b638",
                fillColor: "#f7b638",
                fillOpacity: 0.045,
                opacity: 0.18,
                weight: 1,
                className: "nearby-hotspot-area",
              }}
            />
          ))}

        {hotspots.map((spot) => {
          const posLat = spot.latitude;
          const posLng = spot.longitude;

          const cityStr = getCityLabel(spot.city);
          const regionStr = "Türkiye";

          const parsedRiskLevel =
            spot.risk_level === "CRITICAL" || spot.risk_level === "HIGH"
              ? "Yüksek"
              : spot.risk_level === "MEDIUM"
              ? "Orta"
              : spot.risk_level === "UNKNOWN"
              ? "Ölçüm yok"
              : "Düşük";

          const riskPercentage =
            spot.risk_percent ??
            (spot.fire_probability != null
              ? Math.round(spot.fire_probability * 100)
              : null);

          const temp = spot.temperature ?? "N/A";
          const wind = spot.wind_speed ?? "N/A";
          const hum = spot.humidity ?? "N/A";
          const spreadDirection = spot.spread_direction ?? "Ölçüm yok";
          const timeAgo = formatTimeAgo(spot.hours_ago);

          // "pending" ise marker gri gösterilir
          const effectiveLevel =
            spot.ml_source === "pending"
              ? "UNKNOWN"
              : spot.risk_level === "CRITICAL"
              ? "HIGH"
              : spot.risk_level === "WATCH"
              ? "LOW"
              : spot.risk_level;
          const icon = createCustomIcon(effectiveLevel, {
            burning: isBurningHotspot(spot),
            clustered: nearbyHotspotInfo.clusterIds.has(spot.id),
          });

          return (
            <Marker
              key={spot.id}
              position={[posLat, posLng]}
              icon={icon}
              ref={(ref) => {
                if (ref) {
                  markerRefs.current[spot.id] = ref;
                } else {
                  delete markerRefs.current[spot.id];
                }
              }}
            >
              <Popup className="custom-popup" closeButton={false}>
                <FireDetailCard
                  city={cityStr}
                  region={regionStr}
                  riskLevel={parsedRiskLevel}
                  riskPercentage={riskPercentage}
                  temperature={temp}
                  windSpeed={wind}
                  humidity={hum}
                  spreadDirection={spreadDirection}
                  timeAgo={timeAgo}
                  mlSource={spot.ml_source}
                  clusterId={spot.cluster_id}
                  clusterStatus={spot.cluster_status}
                  onShowInList={() => onSelectHotspot?.(spot.id)}
                  onClose={null}
                />
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Harita açıklaması */}
      <button
        type="button"
        className="map-legend-toggle"
        onClick={() => setShowLegend((value) => !value)}
        title={showLegend ? "Risk açıklamasını kapat" : "Risk açıklamasını aç"}
        aria-label={showLegend ? "Risk açıklamasını kapat" : "Risk açıklamasını aç"}
      >
        {showLegend ? <X size={13} /> : <Layers size={13} />}
        <span>{showLegend ? "Kapat" : "Risk"}</span>
      </button>

      {showLegend && (
        <div className="map-legend">
          <div className="legend-title">RİSK SEVİYESİ</div>
          <div className="legend-item">
            <span className="legend-dot dot-red" /> Alarm / Aktif Yangın
          </div>
          <div className="legend-item">
            <span className="legend-dot dot-orange" /> Yüksek Risk
          </div>
          <div className="legend-item">
            <span className="legend-dot dot-blue" /> Orta Risk
          </div>
          <div className="legend-item">
            <span className="legend-dot dot-green" /> Düşük Risk
          </div>
          <div className="legend-item">
            <span className="legend-dot dot-gray" /> Veri Bekleniyor
          </div>
        </div>
      )}
    </div>
  );
}
