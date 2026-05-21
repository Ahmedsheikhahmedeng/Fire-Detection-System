import { useMemo, useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
    Satellite, RefreshCw, Search, ZoomIn, ZoomOut,
    Layers, Radio, Flame, Eye, X, Thermometer,
    Wind, Droplets, Cloud, Navigation
} from "lucide-react";

const SATELLITE_BG = "https://images.unsplash.com/photo-1669092557499-093cb88dc249?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1200";
const FIRE_SMOKE_IMG = "https://images.unsplash.com/photo-1701990003443-2c552816e468?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=800";

const riskColors = {
    high: { dot: "#e24b36", glow: "rgba(226,75,54,0.52)", heat: "rgba(226,75,54,", ring: "rgba(226,75,54,0.18)", text: "#e24b36", label: "Yüksek Risk" },
    medium: { dot: "#f08a3c", glow: "rgba(240,138,60,0.44)", heat: "rgba(240,138,60,", ring: "rgba(240,138,60,0.16)", text: "#ffd6a0", label: "Orta Risk" },
    low: { dot: "#7fbc8c", glow: "rgba(127,188,140,0.34)", heat: "rgba(127,188,140,", ring: "rgba(127,188,140,0.14)", text: "#7fbc8c", label: "Düşük Risk" },
};

const NEARBY_POINT_DISTANCE = 7.5;

function pointDistance(first, second) {
    return Math.hypot(Number(first.x) - Number(second.x), Number(first.y) - Number(second.y));
}

function isBurningFire(fire) {
    return Boolean(fire.active) || (fire.risk === "high" && Number(fire.intensity) >= 75);
}

export function MapView({ fires, selectedFire, onSelectFire }) {
    const [hoveredFire, setHoveredFire] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [zoom, _setZoom] = useState(1);
    const [showHeatmap, setShowHeatmap] = useState(true);
    const [showLabels, setShowLabels] = useState(true);
    const [satelliteMode, setSatelliteMode] = useState(true);
    const [lastUpdated, setLastUpdated] = useState("Az önce");
    const [aiMode, setAiMode] = useState(false);
    const containerRef = useRef(null);

    const handleRefresh = () => {
        setIsRefreshing(true);
        setTimeout(() => {
            setIsRefreshing(false);
            setLastUpdated("Az önce");
        }, 2000);
    };

    const filteredFires = fires.filter(f =>
        searchQuery === "" ||
        f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        f.region.toLowerCase().includes(searchQuery.toLowerCase())
    );
    const nearbyPointInfo = useMemo(() => {
        const clusterIds = new Set();
        const lines = [];

        for (let i = 0; i < filteredFires.length; i += 1) {
            for (let j = i + 1; j < filteredFires.length; j += 1) {
                const first = filteredFires[i];
                const second = filteredFires[j];
                if (pointDistance(first, second) > NEARBY_POINT_DISTANCE) continue;

                clusterIds.add(first.id);
                clusterIds.add(second.id);
                lines.push({ id: `${first.id}-${second.id}`, first, second });
            }
        }

        return { clusterIds, lines: lines.slice(0, 28) };
    }, [filteredFires]);

    const selectedFireData = fires.find(f => f.id === selectedFire);
    const hoveredFireData = fires.find(f => f.id === hoveredFire);
    const tooltipFire = hoveredFireData || selectedFireData;

    // AI predicted fire spread lines (simulated)
    const aiPredictions = [
        { fromId: 1, dx: 5, dy: -12, confidence: 87 },
        { fromId: 2, dx: 8, dy: -8, confidence: 72 },
        { fromId: 3, dx: -6, dy: -10, confidence: 65 },
    ];

    return (
        <div
            className="rounded-xl overflow-hidden flex flex-col flex-1 min-h-0"
            style={{
                border: "1px solid #dda34a",
                background: "#0a0d0b",
            }}
        >
            {/* MAP CONTROLS BAR */}
            <div
                className="flex flex-col px-4 py-2 gap-2"
                style={{ borderBottom: "1px solid #dda34a", background: "rgba(18,21,17,0.88)" }}
            >
                {/* Üst satır: başlık */}
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ background: "#e24b36" }} />
                    <span style={{ fontSize: 11, color: "#dda34a", letterSpacing: 1 }}>TÜRKİYE YANGIN İZLEME HARİTASI</span>
                </div>

                {/* Alt satır: buton + arama + kontroller */}
                <div className="flex items-center gap-2">
                    {/* HARİTAYI AÇ BUTONU */}
                    <a
                        href=""
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all shrink-0"
                        style={{
                            background: "linear-gradient(135deg, #7f211b, #e24b36)",
                            border: "1px solid rgba(226,75,54,0.58)",
                            color: "#f7efe4",
                            fontSize: 11,
                            letterSpacing: 1,
                            boxShadow: "0 0 10px rgba(226,75,54,0.24)",
                            textDecoration: "none",
                        }}
                        onMouseEnter={e => {
                            e.currentTarget.style.background = "linear-gradient(135deg, #8f281f, #e24b36)";
                            e.currentTarget.style.boxShadow = "0 0 18px rgba(226,75,54,0.34)";
                            e.currentTarget.style.borderColor = "rgba(226,75,54,0.72)";
                        }}
                        onMouseLeave={e => {
                            e.currentTarget.style.background = "linear-gradient(135deg, #7f211b, #e24b36)";
                            e.currentTarget.style.boxShadow = "0 0 10px rgba(226,75,54,0.24)";
                            e.currentTarget.style.borderColor = "rgba(226,75,54,0.58)";
                        }}
                    >
                        <Flame size={12} color="#f7efe4" />
                        HARİTAYI AÇ
                    </a>

                    {/* Ayırıcı boşluk */}
                    <div className="w-6" />

                    <div className="flex items-center gap-1.5 ml-auto">
                        {/* Search */}
                        <div
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
                            style={{ background: "rgba(25,29,23,0.92)", border: "1px solid rgba(221,163,74,0.45)" }}
                        >
                            <Search size={12} color="#dda34a" />
                            <input
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder="Bölge ara..."
                                className="bg-transparent outline-none"
                                style={{ fontSize: 11, color: "#f7efe4", width: 80 }}
                            />
                            {searchQuery && (
                                <button onClick={() => setSearchQuery("")}><X size={10} color="#dda34a" /></button>
                            )}
                        </div>

                        {/* Heatmap toggle */}
                        <ControlBtn
                            active={showHeatmap}
                            onClick={() => setShowHeatmap(!showHeatmap)}
                            icon={<Layers size={12} />}
                            label="Isı"
                        />

                        {/* Labels toggle */}
                        <ControlBtn
                            active={showLabels}
                            onClick={() => setShowLabels(!showLabels)}
                            icon={<Eye size={12} />}
                            label="Etiket"
                        />

                        {/* Satellite mode */}
                        <ControlBtn
                            active={satelliteMode}
                            onClick={() => setSatelliteMode(!satelliteMode)}
                            icon={<Satellite size={12} />}
                            label="Uydu"
                        />

                        {/* AI mode */}
                        <ControlBtn
                            active={aiMode}
                            onClick={() => setAiMode(!aiMode)}
                            icon={<Radio size={12} />}
                            label="AI"
                            accentColor="#dda34a"
                        />

                        {/* Refresh */}
                        <button
                            onClick={handleRefresh}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg"
                            style={{ background: "rgba(25,29,23,0.92)", border: "1px solid rgba(221,163,74,0.45)" }}
                        >
                            <motion.div animate={{ rotate: isRefreshing ? 360 : 0 }} transition={{ duration: 0.8, repeat: isRefreshing ? Infinity : 0, ease: "linear" }}>
                                <RefreshCw size={12} color="#dda34a" />
                            </motion.div>
                            <span style={{ fontSize: 11, color: "#dda34a" }}>Güncelle</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* MAP AREA */}
            <div className="relative overflow-hidden flex-1 min-h-0" ref={containerRef}>
                {/* Satellite background */}
                <div
                    className="absolute inset-0"
                    style={{
                        backgroundImage: satelliteMode ? `url(${SATELLITE_BG})` : "none",
                        backgroundSize: "cover",
                        backgroundPosition: "center",
                        opacity: satelliteMode ? 0.35 : 0,
                        transition: "opacity 0.5s",
                    }}
                />

                {/* Dark gradient overlay */}
                <div
                    className="absolute inset-0"
                    style={{
                        background: "radial-gradient(ellipse at 40% 50%, rgba(10,13,11,0.68) 0%, rgba(10,13,11,0.86) 100%)",
                    }}
                />

                {/* Grid overlay */}
                <div
                    className="absolute inset-0"
                    style={{
                        backgroundImage: `
              linear-gradient(#dda34a 1px, transparent 1px),
              linear-gradient(90deg, #dda34a 1px, transparent 1px)
            `,
                        backgroundSize: "40px 40px",
                    }}
                />

                {/* Coordinate lines overlay */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        backgroundImage: `
              linear-gradient(#dda34a 1px, transparent 1px),
              linear-gradient(90deg, #dda34a 1px, transparent 1px)
            `,
                        backgroundSize: "200px 200px",
                    }}
                />

                {/* Map content (Turkey map area) */}
                <div
                    className="absolute"
                    style={{
                        inset: 0,
                        transform: `scale(${zoom})`,
                        transformOrigin: "center center",
                        transition: "transform 0.3s",
                    }}
                >
                    {/* Turkey SVG border */}
                    <svg
                        className="absolute inset-0 w-full h-full pointer-events-none"
                        viewBox="0 0 100 56"
                        preserveAspectRatio="xMidYMid meet"
                    >
                        <defs>
                            <filter id="glow-border">
                                <feGaussianBlur stdDeviation="0.8" result="coloredBlur" />
                                <feMerge>
                                    <feMergeNode in="coloredBlur" />
                                    <feMergeNode in="SourceGraphic" />
                                </feMerge>
                            </filter>
                            <filter id="fire-glow">
                                <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
                                <feMerge>
                                    <feMergeNode in="coloredBlur" />
                                    <feMergeNode in="SourceGraphic" />
                                </feMerge>
                            </filter>
                        </defs>

                        {/* Turkey polygon border */}
                        <polygon
                            points="16,11 22,8 30,5 40,4 50,4 60,5 68,5 76,7 83,9 90,12 94,18 95,24 93,30 90,38 85,44 78,50 70,53 62,55 52,55 44,53 38,51 32,49 28,47 24,43 18,41 14,40 10,35 10,28 12,20 14,15"
                            fill="#dda34a"
                            stroke="#dda34a"
                            strokeWidth="0.3"
                            filter="url(#glow-border)"
                        />

                        {/* Region boundary lines (simplified) */}
                        {[
                            "M 30,5 L 28,47",
                            "M 50,4 L 52,55",
                            "M 70,5 L 70,53",
                        ].map((d, i) => (
                            <path key={i} d={d} stroke="#dda34a" strokeWidth="0.2" strokeDasharray="1,2" />
                        ))}

                        {/* AI fire spread predictions */}
                        {aiMode && aiPredictions.map((pred) => {
                            const fire = fires.find(f => f.id === pred.fromId);
                            if (!fire) return null;
                            const sx = (fire.x / 100) * 100;
                            const sy = (fire.y / 100) * 56;
                            const ex = sx + pred.dx;
                            const ey = sy + pred.dy;
                            return (
                                <g key={pred.fromId}>
                                    <line
                                        x1={sx} y1={sy} x2={ex} y2={ey}
                                        stroke="#dda34a"
                                        strokeWidth="0.5"
                                        strokeDasharray="2,1"
                                    />
                                    <circle cx={ex} cy={ey} r="1.5" fill="#dda34a" />
                                    <text x={ex + 1} y={ey - 1} fontSize="2" fill="#dda34a">
                                        AI {pred.confidence}%
                                    </text>
                                </g>
                            );
                        })}

                        {/* Wind arrows */}
                        {fires.filter(f => f.risk === "high").map((fire) => {
                            const cx = (fire.x / 100) * 100;
                            const cy = (fire.y / 100) * 56;
                            return (
                                <g key={`wind-${fire.id}`} opacity="0.4">
                                    <line x1={cx} y1={cy} x2={cx + 3} y2={cy - 2} stroke="#dda34a" strokeWidth="0.4" />
                                    <polygon
                                        points={`${cx + 3},${cy - 2} ${cx + 2},${cy - 0.5} ${cx + 3.5},${cy - 0.5}`}
                                        fill="#dda34a"
                                    />
                                </g>
                            );
                        })}
                    </svg>

                    {/* HEATMAP LAYERS */}
                    {showHeatmap && (
                        <div className="absolute inset-0 pointer-events-none">
                            {filteredFires.map((fire) => {
                                const colors = riskColors[fire.risk] || riskColors.low;
                                const size = fire.risk === "high" ? 220 : fire.risk === "medium" ? 150 : 90;
                                const opacity = fire.intensity / 100;
                                return (
                                    <div
                                        key={`heat-${fire.id}`}
                                        className="absolute pointer-events-none"
                                        style={{
                                            left: `${fire.x}%`,
                                            top: `${fire.y}%`,
                                            width: size,
                                            height: size * 0.7,
                                            transform: "translate(-50%, -50%)",
                                            background: `radial-gradient(ellipse, ${colors.heat}${opacity * 0.6}) 0%, ${colors.heat}${opacity * 0.25}) 40%, transparent 75%)`,
                                            mixBlendMode: "screen",
                                            borderRadius: "50%",
                                        }}
                                    />
                                );
                            })}
                        </div>
                    )}

                    {/* NEARBY POINT EFFECTS */}
                    {nearbyPointInfo.lines.length > 0 && (
                        <svg className="absolute inset-0 pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                            {nearbyPointInfo.lines.map(({ id, first, second }) => (
                                <motion.line
                                    key={`near-${id}`}
                                    x1={first.x}
                                    y1={first.y}
                                    x2={second.x}
                                    y2={second.y}
                                    stroke="#f7b638"
                                    strokeWidth="0.16"
                                    strokeDasharray="1.4 1.6"
                                    initial={{ opacity: 0.16 }}
                                    animate={{ opacity: [0.18, 0.48, 0.18], pathLength: [0.88, 1, 0.88] }}
                                    transition={{ repeat: Infinity, duration: 2.2, ease: "easeInOut" }}
                                />
                            ))}
                        </svg>
                    )}

                    {nearbyPointInfo.clusterIds.size > 0 && (
                        <div className="absolute inset-0 pointer-events-none">
                            {filteredFires
                                .filter((fire) => nearbyPointInfo.clusterIds.has(fire.id))
                                .map((fire) => {
                                    const colors = riskColors[fire.risk] || riskColors.low;
                                    return (
                                        <motion.div
                                            key={`near-halo-${fire.id}`}
                                            className="absolute rounded-full"
                                            style={{
                                                left: `${fire.x}%`,
                                                top: `${fire.y}%`,
                                                width: 38,
                                                height: 38,
                                                transform: "translate(-50%, -50%)",
                                                border: `1px solid ${colors.dot}44`,
                                                background: `${colors.dot}10`,
                                            }}
                                            animate={{ opacity: [0.22, 0.52, 0.22], scale: [0.92, 1.12, 0.92] }}
                                            transition={{ repeat: Infinity, duration: 2.4, ease: "easeInOut" }}
                                        />
                                    );
                                })}
                        </div>
                    )}

                    {/* FIRE MARKERS */}
                    {filteredFires.map((fire) => {
                        const colors = riskColors[fire.risk] || riskColors.low;
                        const isSelected = selectedFire === fire.id;
                        const isHovered = hoveredFire === fire.id;
                        const isBurning = isBurningFire(fire);
                        const isClustered = nearbyPointInfo.clusterIds.has(fire.id);
                        const markerSize = isSelected || isHovered ? 22 : 18;

                        return (
                            <div
                                key={fire.id}
                                className="absolute cursor-pointer"
                                style={{
                                    left: `${fire.x}%`,
                                    top: `${fire.y}%`,
                                    transform: "translate(-50%, -50%)",
                                    zIndex: isSelected ? 30 : isHovered ? 25 : 10,
                                }}
                                onClick={() => {
                                    onSelectFire(isSelected ? null : fire.id);
                                }}
                                onMouseEnter={() => setHoveredFire(fire.id)}
                                onMouseLeave={() => setHoveredFire(null)}
                            >
                                {/* Marker */}
                                <motion.div
                                    className="relative flex items-center justify-center z-10"
                                    style={{
                                        width: markerSize,
                                        height: markerSize,
                                    }}
                                >
                                    {isBurning && (
                                        <motion.div
                                            className="absolute rounded-full"
                                            style={{
                                                width: markerSize + 14,
                                                height: markerSize + 14,
                                                border: `1px solid ${colors.dot}`,
                                                background: `${colors.dot}14`,
                                            }}
                                            animate={{ opacity: [0.82, 0], scale: [0.62, 1.55] }}
                                            transition={{ repeat: Infinity, duration: 1.05, ease: "easeOut" }}
                                        />
                                    )}
                                    <div
                                        className="absolute"
                                        style={{
                                            width: markerSize,
                                            height: markerSize,
                                            borderRadius: "999px",
                                            background: `${colors.dot}24`,
                                            border: `1px solid ${isSelected ? "#fff8ee" : colors.dot}`,
                                            boxShadow: isBurning
                                                ? `0 0 16px ${colors.glow}`
                                                : isSelected || isHovered || isClustered
                                                ? `0 0 10px ${colors.glow}`
                                                : "none",
                                        }}
                                    />
                                    <div
                                        className="absolute rounded-full"
                                        style={{
                                            width: isSelected || isHovered ? 9 : 7,
                                            height: isSelected || isHovered ? 9 : 7,
                                            background: colors.dot,
                                            border: "1px solid rgba(255,248,238,0.72)",
                                            boxShadow: `0 0 6px ${colors.glow}`,
                                        }}
                                    />
                                </motion.div>

                                {/* City label */}
                                {showLabels && (
                                    <div
                                        className="absolute left-1/2 pointer-events-none whitespace-nowrap"
                                        style={{
                                            top: isSelected ? 25 : 22,
                                            transform: "translateX(-50%)",
                                            fontSize: isSelected ? 11 : 9,
                                            color: isSelected ? "#fff" : colors.text,
                                            background: "rgba(18,21,17,0.88)",
                                            padding: "1px 5px",
                                            borderRadius: 3,
                                            border: `1px solid ${colors.dot}44`,
                                            letterSpacing: 0.5,
                                        }}
                                    >
                                        {fire.name}
                                    </div>
                                )}
                            </div>
                        );
                    })}

                    {/* AI PREDICTION INFO PANEL */}
                    {aiMode && (
                        <motion.div
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="absolute top-3 right-3 p-3 rounded-xl"
                            style={{
                                background: "#e24b36",
                                border: "1px solid #dda34a",
                                backdropFilter: "blur(8px)",
                                minWidth: 160,
                            }}
                        >
                            <div className="flex items-center gap-2 mb-2">
                                <Radio size={12} color="#dda34a" />
                                <span style={{ fontSize: 10, color: "#dda34a", letterSpacing: 1 }}>AI TAHMİN MOD</span>
                            </div>
                            <div style={{ fontSize: 10, color: "#dda34a" }}>
                                <div className="flex justify-between mb-1"><span>Risk Tahmin Doğruluğu</span><span style={{ color: "#dda34a" }}>94.2%</span></div>
                                <div className="flex justify-between mb-1"><span>Yayılma Tahmini</span><span style={{ color: "#dda34a" }}>+12h</span></div>
                                <div className="flex justify-between"><span>Model</span><span style={{ color: "#dda34a" }}>FireNet v3</span></div>
                            </div>
                        </motion.div>
                    )}

                    {/* SCAN LINE - kaldırıldı (kasma sebebi) */}
                </div>

                {/* LEGEND */}
                <div
                    className="absolute bottom-3 left-3 p-3 rounded-xl"
                    style={{
                        background: "rgba(18, 0, 5,0.92)",
                        border: "1px solid rgba(247,182,56,0.4)",
                        zIndex: 20,
                    }}
                >
                    <div style={{ fontSize: 9, color: "#dda34a", letterSpacing: 1, marginBottom: 6 }}>RİSK SEVİYESİ</div>
                    {Object.entries(riskColors).map(([key, val]) => (
                        <div key={key} className="flex items-center gap-2 mb-1">
                            <div className="rounded-full" style={{ width: 8, height: 8, background: val.dot, boxShadow: `0 0 4px ${val.glow}` }} />
                            <span style={{ fontSize: 10, color: "#dda34a" }}>{val.label}</span>
                        </div>
                    ))}
                    <div className="flex items-center gap-2 mt-2 pt-2" style={{ borderTop: "1px solid #dda34a" }}>
                        <Flame size={8} color="#e24b36" />
                        <span style={{ fontSize: 10, color: "#dda34a" }}>Aktif Yangın</span>
                    </div>
                </div>

                {/* STATUS BAR */}
                <div
                    className="absolute bottom-3 right-3 flex items-center gap-3 px-3 py-2 rounded-xl"
                    style={{
                        background: "rgba(18, 0, 5,0.92)",
                        border: "1px solid rgba(247,182,56,0.4)",
                        zIndex: 20,
                    }}
                >
                    <div className="flex items-center gap-1.5">
                        <motion.div
                            animate={{ opacity: [1, 0.3, 1] }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                            className="w-1.5 h-1.5 rounded-full"
                            style={{ background: "#dda34a" }}
                        />
                        <span style={{ fontSize: 10, color: "#dda34a" }}>CANLI</span>
                    </div>
                    <span style={{ fontSize: 10, color: "#dda34a" }}>|</span>
                    <span style={{ fontSize: 10, color: "#dda34a" }}>Zoom: {Math.round(zoom * 100)}%</span>
                    <span style={{ fontSize: 10, color: "#dda34a" }}>|</span>
                    <span style={{ fontSize: 10, color: "#dda34a" }}>{lastUpdated}</span>
                </div>

                {/* COORDINATE DISPLAY */}
                <div
                    className="absolute top-3 left-3 px-3 py-2 rounded-lg"
                    style={{
                        background: "rgba(18, 0, 5,0.92)",
                        border: "1px solid rgba(247,182,56,0.4)",
                        zIndex: 20,
                    }}
                >
                    <div style={{ fontSize: 9, color: "#dda34a", letterSpacing: 1 }}>KONUM</div>
                    <div style={{ fontSize: 10, color: "#dda34a" }}>36°N – 42°N / 26°E – 45°E</div>
                </div>

                {/* HOVER TOOLTIP */}
                <AnimatePresence>
                    {tooltipFire && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="absolute p-3 rounded-xl"
                            style={{
                                left: `${Math.min(tooltipFire.x + 4, 60)}%`,
                                top: `${Math.max(tooltipFire.y - 20, 5)}%`,
                                background: "rgba(18, 0, 5,0.97)",
                                border: `1px solid ${(riskColors[tooltipFire.risk] || riskColors.low).dot}55`,
                                zIndex: 40,
                                minWidth: 200,
                                boxShadow: `0 4px 20px ${(riskColors[tooltipFire.risk] || riskColors.low).glow}`,
                            }}
                        >
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <div
                                        className="w-2 h-2 rounded-full"
                                        style={{ background: (riskColors[tooltipFire.risk] || riskColors.low).dot }}
                                    />
                                    <span style={{ fontSize: 13, color: "#fff" }}>{tooltipFire.name}</span>
                                    <span style={{ fontSize: 10, color: "#dda34a" }}>{tooltipFire.region}</span>
                                </div>
                                {selectedFire === tooltipFire.id && (
                                    <button onClick={() => onSelectFire(null)}>
                                        <X size={12} color="#dda34a" />
                                    </button>
                                )}
                            </div>

                            <div
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full mb-3"
                                style={{
                                    background: `${(riskColors[tooltipFire.risk] || riskColors.low).dot}22`,
                                    border: `1px solid ${(riskColors[tooltipFire.risk] || riskColors.low).dot}55`,
                                }}
                            >
                                <Flame size={9} color={(riskColors[tooltipFire.risk] || riskColors.low).dot} />
                                <span style={{ fontSize: 10, color: (riskColors[tooltipFire.risk] || riskColors.low).text }}>
                                    {(riskColors[tooltipFire.risk] || riskColors.low).label} — {tooltipFire.intensity}%
                                </span>
                            </div>

                            {tooltipFire.clusterId && (
                                <div
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full mb-3 ml-1"
                                    style={{
                                        background: "rgba(221,163,74,0.10)",
                                        border: "1px solid rgba(221,163,74,0.38)",
                                    }}
                                >
                                    <span style={{ fontSize: 10, color: "#f6d28b" }}>
                                        KÜME #{tooltipFire.clusterId}
                                        {tooltipFire.clusterStatus ? ` · Durum: ${tooltipFire.clusterStatus}` : ""}
                                    </span>
                                </div>
                            )}

                            {/* Intensity bar */}
                            <div className="mb-3">
                                <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.08)" }}>
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${tooltipFire.intensity}%` }}
                                        transition={{ duration: 0.6 }}
                                        className="h-full rounded-full"
                                        style={{
                                            background: `linear-gradient(90deg, ${(riskColors[tooltipFire.risk] || riskColors.low).dot}, ${(riskColors[tooltipFire.risk] || riskColors.low).dot}88)`,
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                {[
                                    { icon: Thermometer, label: "Sıcaklık", value: `${tooltipFire.temp}°C`, color: "#dda34a" },
                                    { icon: Wind, label: "Rüzgar", value: `${tooltipFire.wind} km/s`, color: "#dda34a" },
                                    { icon: Droplets, label: "Nem", value: `%${tooltipFire.humidity}`, color: "#dda34a" },
                                    { icon: Cloud, label: "Duman", value: `%${tooltipFire.smoke}`, color: "#dda34a" },
                                ].map((item) => (
                                    <div key={item.label} className="flex items-center gap-1.5">
                                        <item.icon size={10} color={item.color} />
                                        <div>
                                            <div style={{ fontSize: 9, color: "#dda34a" }}>{item.label}</div>
                                            <div style={{ fontSize: 11, color: item.color }}>{item.value}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="flex items-center justify-between mt-2 pt-2" style={{ borderTop: "1px solid #dda34a" }}>
                                <div className="flex items-center gap-1">
                                    <Navigation size={9} color="#dda34a" />
                                    <span style={{ fontSize: 9, color: "#dda34a" }}>Yayılma: {tooltipFire.spread} → {tooltipFire.direction}</span>
                                </div>
                                <span style={{ fontSize: 9, color: "#dda34a" }}>{tooltipFire.time}</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

function ControlBtn({ active, onClick, icon, label, accentColor = "#dda34a" }) {
    return (
        <button
            onClick={onClick}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-all"
            style={{
                background: active ? `${accentColor}22` : "rgba(255,255,255,0.04)",
                border: `1px solid ${active ? accentColor + "55" : "rgba(255,255,255,0.08)"}`,
                color: active ? accentColor : "#dda34a",
            }}
        >
            {icon}
            <span style={{ fontSize: 10 }}>{label}</span>
        </button>
    );
}
