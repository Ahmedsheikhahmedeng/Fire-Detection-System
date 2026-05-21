import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
    Flame, MapPin, Clock, Satellite,
    Navigation, ChevronDown, ChevronUp, Filter,
    AlertCircle, CheckCircle, Search, X
} from "lucide-react";

const riskColors = {
    high: { dot: "#d42b3f", text: "#f7c1b6", bg: "#d42b3f", border: "#d42b3f", label: "Yüksek" },
    medium: { dot: "#f08a3c", text: "#ffd6a0", bg: "#f08a3c", border: "#f08a3c", label: "Orta" },
    low: { dot: "#7fbc8c", text: "#cce8c9", bg: "#7fbc8c", border: "#7fbc8c", label: "Düşük" },
};

function formatMetric(value, suffix = "", prefix = "") {
    if (value == null || value === "N/A") return "N/A";
    const number = Number(value);
    if (!Number.isFinite(number)) return "N/A";
    return `${prefix}${new Intl.NumberFormat("tr-TR", {
        maximumFractionDigits: 1,
        minimumFractionDigits: 0,
    }).format(number)}${suffix}`;
}

export function RecentFires({ fires, selectedFire, onSelectFire }) {
    const [filter, setFilter] = useState("all");
    const [timeFilter, setTimeFilter] = useState("latest");
    const [expandedFire, setExpandedFire] = useState(null);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [idSearch, setIdSearch] = useState("");
    const fireRefs = useRef({});
    const scrollContainerRef = useRef(null);
    const normalizedIdSearch = idSearch.trim().replace(/^#/, "");
    const filteredFires = useMemo(() => [...fires]
        .filter(f => filter === "all" || f.risk === filter)
        .filter(f => !normalizedIdSearch || String(f.id).includes(normalizedIdSearch))
        .sort((a, b) => {
            const aHours = Number.isFinite(a.hoursAgo) ? a.hoursAgo : Number.POSITIVE_INFINITY;
            const bHours = Number.isFinite(b.hoursAgo) ? b.hoursAgo : Number.POSITIVE_INFINITY;
            return timeFilter === "latest" ? aHours - bHours : bHours - aHours;
        }), [filter, fires, normalizedIdSearch, timeFilter]);

    useEffect(() => {
        if (selectedFire == null) return;
        const isVisible = filteredFires.some((fire) => String(fire.id) === String(selectedFire));
        if (!isVisible && fires.some((fire) => String(fire.id) === String(selectedFire))) {
            const filterResetTimer = window.setTimeout(() => {
                setFilter("all");
                setIdSearch("");
            }, 0);
            return () => window.clearTimeout(filterResetTimer);
        }

        const expandTimer = window.setTimeout(() => {
            setExpandedFire(selectedFire);
        }, 0);
        const timer = window.setTimeout(() => {
            const container = scrollContainerRef.current;
            const target = fireRefs.current[selectedFire];
            if (!container || !target) return;

            const nextScrollTop =
                target.offsetTop -
                container.offsetTop -
                (container.clientHeight - target.offsetHeight) / 2;

            container.scrollTo({
                top: Math.max(0, nextScrollTop),
                behavior: "smooth",
            });
        }, 120);

        return () => {
            window.clearTimeout(expandTimer);
            window.clearTimeout(timer);
        };
    }, [selectedFire, filteredFires, fires]);

    return (
        <div className="flex flex-col flex-1 rounded-xl overflow-hidden min-h-0"
            style={{ border: "1px solid rgba(120,1,21,0.68)", background: "#090305" }}>
            <div className="shrink-0 flex items-center gap-2 px-3 py-2"
                style={{ borderBottom: "1px solid rgba(120,1,21,0.38)", background: "rgba(28,2,8,0.9)" }}>
                <Flame size={11} color="#d42b3f" />
                <span style={{ fontSize: 10, color: "#f7efe4", letterSpacing: 1 }}>SON TESPİT EDİLEN YANGINLAR</span>
                <span className="ml-auto shrink-0" style={{ fontSize: 9, color: "#cbbba4" }}>{filteredFires.length} kayıt</span>
            </div>
            <div
                className="shrink-0 flex items-center gap-1 px-2 py-1.5 overflow-x-auto"
                style={{ borderBottom: "1px solid rgba(120,1,21,0.34)", background: "rgba(6,2,4,0.7)", scrollbarWidth: "none" }}
            >
                <Filter size={9} color="#cbbba4" />
                {[
                    { type: "time", id: "latest", label: "En Güncel" },
                    { type: "time", id: "oldest", label: "En Eski" },
                    { type: "risk", id: "high", label: riskColors.high.label },
                    { type: "risk", id: "medium", label: riskColors.medium.label },
                    { type: "risk", id: "low", label: riskColors.low.label },
                ].map((option) => {
                    const isTime = option.type === "time";
                    const isActive = isTime ? timeFilter === option.id : filter === option.id;
                    const riskStyle = !isTime && option.id !== "all" ? riskColors[option.id] : null;

                    return (
                    <button
                        key={`${option.type}-${option.id}`}
                        onClick={() => {
                            if (isTime) {
                                setTimeFilter(option.id);
                            } else {
                                setFilter(option.id);
                            }
                        }}
                        className="px-1.5 py-0.5 rounded-md transition-all whitespace-nowrap"
                        style={{
                            fontSize: 9,
                            background: isActive
                                ? (riskStyle ? `${riskStyle.dot}24` : "rgba(120,1,21,0.24)")
                                : "rgba(247,239,228,0.04)",
                            border: isActive
                                ? (riskStyle ? `1px solid ${riskStyle.dot}66` : "1px solid rgba(120,1,21,0.58)")
                                : "1px solid transparent",
                            color: isActive
                                ? (riskStyle ? riskStyle.text : "#f7efe4")
                                : "#cbbba4",
                        }}
                    >
                        {option.label}
                    </button>
                    );
                })}
                <div className="shrink-0 flex items-center gap-1">
                    <AnimatePresence initial={false}>
                        {isSearchOpen && (
                            <motion.div
                                key="id-search"
                                initial={{ width: 0, opacity: 0 }}
                                animate={{ width: 86, opacity: 1 }}
                                exit={{ width: 0, opacity: 0 }}
                                transition={{ duration: 0.18 }}
                                className="overflow-hidden"
                            >
                                <input
                                    value={idSearch}
                                    onChange={(event) => setIdSearch(event.target.value.replace(/[^\d#]/g, ""))}
                                    placeholder="ID ara"
                                    autoFocus
                                    className="w-full rounded-md px-1.5 py-0.5 outline-none"
                                    style={{
                                        height: 20,
                                        fontSize: 9,
                                        color: "#f7efe4",
                                        background: "rgba(247,239,228,0.06)",
                                        border: "1px solid rgba(203,187,164,0.26)",
                                    }}
                                />
                            </motion.div>
                        )}
                    </AnimatePresence>
                    <button
                        type="button"
                        aria-label={isSearchOpen ? "ID aramayı kapat" : "ID ile ara"}
                        onClick={() => {
                            if (isSearchOpen) {
                                setIdSearch("");
                            }
                            setIsSearchOpen((value) => !value);
                        }}
                        className="rounded-md flex items-center justify-center transition-all"
                        style={{
                            width: 20,
                            height: 20,
                            background: isSearchOpen ? "rgba(120,1,21,0.24)" : "rgba(247,239,228,0.04)",
                            border: isSearchOpen ? "1px solid rgba(120,1,21,0.58)" : "1px solid transparent",
                            color: "#cbbba4",
                        }}
                    >
                        {isSearchOpen ? <X size={10} /> : <Search size={10} />}
                    </button>
                </div>
            </div>
            <div ref={scrollContainerRef} className="recent-fires-scroll flex-1 overflow-y-auto min-h-0">
                {filteredFires.map((fire, i) => {
                    const colors = riskColors[fire.risk] || riskColors.low;
                    const isExpanded = String(expandedFire) === String(fire.id);
                    const isSelected = String(selectedFire) === String(fire.id);
                    return (
                        <motion.div key={fire.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                            ref={(element) => {
                                if (element) {
                                    fireRefs.current[fire.id] = element;
                                } else {
                                    delete fireRefs.current[fire.id];
                                }
                            }}
                            transition={{ delay: i * 0.04 }} className="border-b transition-all" style={{ borderColor: "rgba(120,1,21,0.24)" }}>
                            <motion.div className="flex items-center gap-2 px-2 py-2 cursor-pointer hover:bg-white/5"
                                style={{
                                    background: isSelected || fire.active ? `${colors.dot}${fire.active ? "16" : "18"}` : "transparent",
                                    borderLeft: `2px solid ${isSelected || fire.active ? colors.dot : "transparent"}`,
                                }}
                                animate={fire.active ? {
                                    boxShadow: [
                                        `inset 0 0 0 rgba(255, 80, 32, 0)`,
                                        `inset 0 0 22px ${colors.dot}28`,
                                        `inset 0 0 0 rgba(255, 80, 32, 0)`,
                                    ],
                                } : {}}
                                transition={fire.active ? { repeat: Infinity, duration: 1.35, ease: "easeInOut" } : {}}
                                onClick={() => {
                                    onSelectFire(null);
                                    setExpandedFire(isExpanded ? null : fire.id);
                                }}>
                                <div className="relative shrink-0">
                                    <div className="rounded-full flex items-center justify-center"
                                        style={{
                                            width: 22,
                                            height: 22,
                                            background: `${colors.dot}22`,
                                            border: `1px solid ${colors.dot}88`,
                                            boxShadow: "none",
                                        }}>
                                        {fire.risk === "high" ? <Flame size={10} color={colors.dot} /> : fire.risk === "medium" ? <AlertCircle size={10} color={colors.dot} /> : <CheckCircle size={10} color={colors.dot} />}
                                    </div>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-1">
                                        <div className="flex items-center gap-1 min-w-0">
                                            <span style={{ fontSize: 11, color: "#f7efe4", fontWeight: 600 }} className="truncate">{fire.name}</span>
                                        </div>
                                        <span className="px-1 py-0.5 rounded shrink-0" style={{ fontSize: 8, background: `${colors.dot}18`, color: colors.text, border: `1px solid ${colors.dot}55` }}>{colors.label}</span>
                                    </div>
                                    <div className="flex items-center gap-2 mt-0.5">
                                        <div className="flex items-center gap-0.5"><MapPin size={8} color="#cbbba4" /><span style={{ fontSize: 9, color: "#cbbba4" }}>{fire.region}</span></div>
                                        <span style={{ fontSize: 9, color: "rgba(203,187,164,0.36)" }}>·</span>
                                        <div className="flex items-center gap-0.5"><Clock size={8} color="#cbbba4" /><span style={{ fontSize: 9, color: "#cbbba4" }}>{fire.time}</span></div>
                                    </div>
                                    <div className="mt-1">
                                        <div className="h-0.5 rounded-full overflow-hidden" style={{ background: "rgba(232,199,150,0.12)" }}>
                                            <motion.div initial={{ width: 0 }} animate={{ width: `${fire.intensity}%` }}
                                                transition={{ duration: 0.8, delay: i * 0.05 }} className="h-full rounded-full"
                                                style={{ background: `linear-gradient(90deg, ${colors.dot}, ${colors.dot}88)` }} />
                                        </div>
                                    </div>
                                </div>
                                <div style={{ color: "#cbbba4" }}>{isExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}</div>
                            </motion.div>
                            <AnimatePresence>
                                {isExpanded && (
                                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
                                        <div className="grid grid-cols-2 gap-1.5 px-2 pb-2 mx-2 mb-1.5 rounded-lg"
                                            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
                                            {[
                                                { icon: Flame, label: "Yakın Nokta", value: `${fire.nearbyHotspotCount || 0} tespit`, color: "#d9c6b0" },
                                                { icon: Satellite, label: "Parlaklık", value: formatMetric(fire.brightness, " K"), color: "#d9c6b0" },
                                                { icon: MapPin, label: "ID", value: `#${fire.id}`, color: "#d9c6b0" },
                                            ].map((item) => (
                                                <div key={item.label} className="flex items-center gap-1.5 pt-1.5">
                                                    <item.icon size={9} color={item.color} />
                                                    <div className="min-w-0">
                                                        <div style={{ fontSize: 8, color: "rgba(255,255,255,0.5)" }}>{item.label}</div>
                                                        <div className="truncate" style={{ fontSize: 10, color: item.color }}>{item.value}</div>
                                                    </div>
                                                </div>
                                            ))}
                                            <div className="flex items-end justify-end pt-1.5 pr-17 max-sm:justify-start max-sm:pl-1">
                                                <button
                                                    type="button"
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        onSelectFire(fire.id);
                                                    }}
                                                    className="fire-detail-action-button"
                                                >
                                                    <Navigation size={10} />
                                                    Noktaya Git
                                                </button>
                                            </div>
                                            <div className="col-span-2 pt-1.5 flex items-center gap-1.5" style={{ borderTop: "1px solid rgba(255,255,255,0.08)", marginTop: 2 }}>
                                                <Navigation size={8} color="rgba(255,255,255,0.5)" />
                                                <span style={{ fontSize: 9, color: "rgba(255,255,255,0.7)" }}>
                                                    NASA Gözlemi: {fire.observedLabel || "Bekleniyor"}
                                                </span>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
