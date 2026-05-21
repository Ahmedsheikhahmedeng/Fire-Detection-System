import { useState, useEffect } from "react";
import { ShieldCheck, Clock, Flame, ServerCrash } from "lucide-react";
import axios from "axios";
import { formatRelativeTimestamp } from "../../utils/time";
import { API_BASE_URL, WS_BASE_URL } from "../../services/api";

export function SystemStatus() {
    const [stats, setStats] = useState(null);
    const [lastUpdate, setLastUpdate] = useState("Bağlanıyor...");
    const [lastObservationUpdate, setLastObservationUpdate] = useState("Bekleniyor");
    const [currentTask, setCurrentTask] = useState(null);
    const [schedulerState, setSchedulerState] = useState(null);
    const [isOnline, setIsOnline] = useState(true);

    const fetchStatus = async () => {
        try {
            const [statusRes, statsRes] = await Promise.all([
                axios.get(`${API_BASE_URL}/map/status`, { timeout: 5000 }),
                axios.get(`${API_BASE_URL}/map/stats`, { timeout: 5000 })
            ]);
            setStats(statsRes.data);
            setIsOnline(true);
            setCurrentTask(statusRes.data?.current_task || null);
            setSchedulerState(statusRes.data?.is_running ? "Çalışıyor" : "Beklemede");

            setLastObservationUpdate(
                statusRes.data?.last_nasa_observation_at
                    ? formatRelativeTimestamp(statusRes.data.last_nasa_observation_at)
                    : "Bekleniyor"
            );
            
            const mlAt =
                statusRes.data?.last_ml_display_at ||
                statusRes.data?.last_ml_scan ||
                statusRes.data?.last_prediction_at;

            if (mlAt) {
                setLastUpdate(formatRelativeTimestamp(mlAt));
            } else if (statusRes.data?.last_cycle_finished_at) {
                setLastUpdate(formatRelativeTimestamp(statusRes.data.last_cycle_finished_at));
            } else {
                setLastUpdate("Henüz tarama yok");
            }
        } catch {
            setIsOnline(false);
            setCurrentTask(null);
            setSchedulerState(null);
            setLastObservationUpdate("Bağlantı koptu");
            setLastUpdate("Bağlantı koptu");
        }
    };

    useEffect(() => {
        queueMicrotask(fetchStatus);
        const poll = setInterval(fetchStatus, 60000); // 60s'ye çıkarıldı

        let ws;
        let reconnectTimer;
        let reconnectDelay = 5000;

        function connectWs() {
            try {
                ws = new WebSocket(`${WS_BASE_URL}/alerts/ws`);
                ws.onopen = () => { reconnectDelay = 5000; };
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === "HOTSPOT_UPDATED") fetchStatus();
                };
                ws.onclose = () => {
                    reconnectTimer = setTimeout(() => {
                        reconnectDelay = Math.min(reconnectDelay * 2, 60000);
                        connectWs();
                    }, reconnectDelay);
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
            clearInterval(poll);
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        };
    }, []);

    return (
        <div className="rounded-xl overflow-hidden mt-3"
            style={{ border: `1px solid ${isOnline ? 'rgba(120,1,21,0.68)' : '#d42b3f'}`, background: "#090305" }}>
            <div className="flex items-center gap-2 px-4 py-3"
                style={{ borderBottom: "1px solid rgba(120,1,21,0.38)", background: "rgba(28,2,8,0.9)" }}>
                <div className="flex items-center justify-center w-6 h-6 rounded-md"
                    style={{ background: isOnline ? "rgba(127,188,140,0.16)" : "rgba(226,75,54,0.16)" }}>
                    {isOnline ? <ShieldCheck size={13} color="#7fbc8c" /> : <ServerCrash size={13} color="#d42b3f" />}
                </div>
                <span style={{ fontSize: 12, color: "#f7efe4", letterSpacing: 1 }}>SİSTEM DURUMU</span>
                <div className="ml-auto flex items-center gap-1.5">
                    {isOnline ? (
                        <>
                            <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#7fbc8c" }} />
                            <span style={{ fontSize: 9, color: "#cce8c9", letterSpacing: 1 }}>AKTİF</span>
                        </>
                    ) : (
                        <span style={{ fontSize: 9, color: "#f7c1b6", letterSpacing: 1 }}>ÇEVRİMDIŞI</span>
                    )}
                </div>
            </div>
            <div className="flex flex-col divide-y" style={{ borderColor: "rgba(120,1,21,0.34)" }}>
                <div className="flex items-center gap-3 px-4 py-3">
                    <Clock size={13} color="#f7b638" />
                    <span style={{ fontSize: 11, color: "#cbbba4" }}>{currentTask ? "Aktif İşlem" : "Son Güncelleme"}</span>
                    <span className="ml-auto" style={{ fontSize: 11, color: "#f7efe4" }}>
                        {currentTask || lastUpdate || schedulerState}
                    </span>
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                    <Clock size={13} color="#f7b638" />
                    <span style={{ fontSize: 11, color: "#cbbba4" }}>Son Uydu Gözlemi</span>
                    <span className="ml-auto" style={{ fontSize: 11, color: "#f7efe4" }}>{lastObservationUpdate}</span>
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                    <Flame size={13} color="#d42b3f" />
                    <span style={{ fontSize: 11, color: "#cbbba4" }}>Son Tespit Edilen Yangınlar</span>
                    <span className="ml-auto" style={{ fontSize: 12, color: "#f7c1b6", fontWeight: "bold" }}>
                        {stats?.high_fire_hotspot_count || 0}
                    </span>
                </div>
            </div>
        </div>
    );
}
