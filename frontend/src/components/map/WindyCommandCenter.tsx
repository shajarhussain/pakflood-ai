"use client";

import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { SafetyDisclaimer } from "@/components/layout/SafetyDisclaimer";
import { WindyModeBar } from "@/components/map/WindyModeBar";
import { RiskIndexBadge } from "@/components/map/RiskIndexBadge";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { FloodTimeline } from "@/components/timeline/FloodTimeline";
import { MOCK_FLOOD_EVENTS, RISK_BY_ID, buildMockExplanation } from "@/data/mock";
import type { MockRiskEntry, MockFloodEvent } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import { fetchExplanation, fetchFloodEvents, searchLocations, isV3Available, type ApiLocationResult } from "@/lib/api";
import { useModelStatus } from "@/lib/useModelStatus";
import { RISK_COLORS, RISK_ICONS } from "@/lib/risk-colors";
import type { RiskLevel } from "@/lib/types";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";
import { CITY_WEATHER } from "@/data/pakistan-cities-weather";
import type { MapHandle } from "@/components/map/MapDashboard";
import type { LayerMode } from "@/components/map/CleanLayerSwitcher";

const WindyPakistanMap = dynamic(
  () => import("./WindyPakistanMap"),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          position: "absolute", inset: 0, display: "flex",
          alignItems: "center", justifyContent: "center", background: "#0A0F1E",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44, height: 44, borderRadius: 14,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, fontWeight: 900, color: "#0A0F1E",
              background: "linear-gradient(135deg, #00FFD1, #3B82F6)",
              boxShadow: "0 0 24px rgba(0,255,209,0.5)",
            }}
          >⬡</div>
          <p style={{
            color: "#00D4FF", fontSize: 11,
            fontFamily: "var(--font-geist-mono, monospace)",
            letterSpacing: "0.14em",
          }}>
            INITIALISING COMMAND MAP…
          </p>
        </div>
      </div>
    ),
  }
);

const MVP_DISTRICTS = new Set([
  "PK-SD-SKR","PK-SD-JCB","PK-SD-LRK","PK-PB-MUL","PK-PB-RWP",
  "PK-PB-LHR","PK-KP-PSH","PK-BL-QTA","PK-BL-NAS","PK-GB-GIL",
]);

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono, monospace)" };

export default function WindyCommandCenter() {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  // ── Layer / selection state ──────────────────────────────────────────────
  const [mode, setMode]                     = useState<LayerMode>("risk");
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null);
  const [selectedGridCell,   setSelectedGridCell]   = useState<GridCell | null>(null);
  const [selectedCity,       setSelectedCity]       = useState<CityWeather | null>(null);
  const [activeYear,  setActiveYear]  = useState<number | null>(null);
  const [floodEvents, setFloodEvents] = useState<MockFloodEvent[]>(MOCK_FLOOD_EVENTS);
  const [panelClosed, setPanelClosed] = useState(false);
  const mapRef = useRef<MapHandle | null>(null);

  // ── Search state (inline header) ────────────────────────────────────────
  const [query,         setQuery]         = useState("");
  const [results,       setResults]       = useState<ApiLocationResult[]>([]);
  const [outOfScope,    setOutOfScope]    = useState<string | null>(null);
  const [outOfScopeCity,setOutOfScopeCity]= useState<CityWeather | null>(null);
  const [open,          setOpen]          = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchFloodEvents().then((apiEvents) => {
      if (apiEvents.length > 0) {
        setFloodEvents(
          apiEvents.map((e) => ({ ...e, damage_usd_billion: e.damage_usd_billion ?? undefined }))
        );
      }
    });
  }, []);

  // Search debounce
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length < 2) { setResults([]); setOutOfScope(null); setOpen(false); return; }
      const data = await searchLocations(query);
      setResults(data);
      const inScope = data.some((r) => MVP_DISTRICTS.has(r.district_id));
      const oos = !inScope && data.length > 0 ? data[0].name : null;
      setOutOfScope(oos);
      if (oos) {
        const match = CITY_WEATHER.find((c) =>
          c.name.toLowerCase().includes(query.toLowerCase()) ||
          query.toLowerCase().includes(c.name.toLowerCase())
        ) ?? null;
        setOutOfScopeCity(match);
      } else { setOutOfScopeCity(null); }
      if (!data.length) {
        const dm = CITY_WEATHER.find((c) => c.name.toLowerCase().includes(query.toLowerCase()));
        if (dm) { setOutOfScope(dm.name); setOutOfScopeCity(dm); }
      }
      setOpen(true);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  // Outside click closes search
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const entries      = Array.from(RISK_BY_ID.values());
  const severeCount  = entries.filter((e) => e.risk_level === "Severe").length;
  const highCount    = entries.filter((e) => e.risk_level === "High").length;

  // ── Affected districts for history mode ─────────────────────────────────
  const affectedDistrictNames = useMemo<string[]>(() => {
    if (!activeYear) return [];
    return floodEvents.find((e) => e.year === activeYear)?.affected_districts ?? [];
  }, [activeYear, floodEvents]);

  // ── Explanation ──────────────────────────────────────────────────────────
  const selectedDistrict: MockRiskEntry | null = selectedDistrictId
    ? (RISK_BY_ID.get(selectedDistrictId) ?? null)
    : null;

  const [liveExplanation,   setLiveExplanation]   = useState<RiskExplanation | null>(null);
  const [liveExplanationId, setLiveExplanationId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDistrictId) return;
    fetchExplanation(selectedDistrictId).then((live) => {
      if (live) { setLiveExplanation(live); setLiveExplanationId(selectedDistrictId); }
    });
  }, [selectedDistrictId]);

  const selectedExplanation: RiskExplanation | null = (() => {
    if (!selectedDistrict) return null;
    if (liveExplanation && liveExplanationId === selectedDistrictId) return liveExplanation;
    return buildMockExplanation(selectedDistrict);
  })();

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleDistrictClick = useCallback((id: string) => {
    setSelectedDistrictId((prev) => (prev === id ? null : id));
    setSelectedGridCell(null); setSelectedCity(null);
  }, []);

  const handleGridCellClick = useCallback((cell: GridCell) => {
    setSelectedGridCell((prev) => (prev?.id === cell.id ? null : cell));
    setSelectedDistrictId(null); setSelectedCity(null);
  }, []);

  const handleCityClick = useCallback((city: CityWeather) => {
    setSelectedCity((prev) => (prev?.name === city.name ? null : city));
    setSelectedGridCell(null); setMode("weather");
  }, []);

  const handleDistrictSearch = useCallback((result: ApiLocationResult) => {
    setSelectedDistrictId(result.district_id);
    setSelectedGridCell(null); setSelectedCity(null);
    mapRef.current?.flyTo(result.center[0], result.center[1], 9);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedDistrictId(null); setSelectedGridCell(null); setSelectedCity(null);
    setPanelClosed(true);
  }, []);

  function selectResult(r: ApiLocationResult) {
    if (!MVP_DISTRICTS.has(r.district_id)) return;
    handleDistrictSearch(r);
    setQuery(""); setOpen(false); setResults([]); setOutOfScope(null); setOutOfScopeCity(null);
  }

  function selectOosCity() {
    if (outOfScopeCity) handleCityClick(outOfScopeCity);
    setQuery(""); setOpen(false); setResults([]); setOutOfScope(null); setOutOfScopeCity(null);
  }

  const hasSelection = !!(selectedDistrictId || selectedGridCell || selectedCity);
  const showPanel    = !panelClosed || hasSelection;

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh", overflow: "hidden", background: "#0A0F1E" }}>

      {/* Full-viewport map */}
      <div style={{ position: "absolute", inset: 0, zIndex: 1 }}>
        <WindyPakistanMap
          mapRef={mapRef}
          mode={mode}
          riskData={RISK_BY_ID}
          selectedDistrictId={selectedDistrictId}
          onDistrictClick={handleDistrictClick}
          affectedDistrictNames={affectedDistrictNames}
          onGridCellClick={handleGridCellClick}
          selectedGridCellId={selectedGridCell?.id ?? null}
          onCityClick={handleCityClick}
          selectedCityName={selectedCity?.name ?? null}
          panelOpen={showPanel}
          v3Available={v3Ready}
        />
      </div>

      {/* ── Slim 48px header ─────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 750,
          height: 48,
          background: "rgba(10,15,30,0.94)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderBottom: "1px solid rgba(0,255,209,0.10)",
          display: "flex", alignItems: "center", gap: 12, padding: "0 16px",
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div
            style={{
              width: 28, height: 28, borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 13, fontWeight: 900, color: "#0A0F1E",
              background: "linear-gradient(135deg, #00FFD1 0%, #3B82F6 100%)",
              boxShadow: "0 0 16px rgba(0,255,209,0.55)",
              flexShrink: 0,
            }}
          >⬡</div>
          <div style={{ lineHeight: 1, ...mono }}>
            <div style={{ color: "#DCF0F5", fontWeight: 700, fontSize: 12, letterSpacing: "0.07em" }}>
              PAKFLOOD AI
            </div>
            <div style={{ color: "#00C8AA", fontSize: 8, letterSpacing: "0.18em", marginTop: 2 }}>
              FLOOD INTELLIGENCE SYSTEM
            </div>
          </div>
        </div>

        {/* Status pills — center */}
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginLeft: "auto", marginRight: "auto" }}>
          <Pill color="#00C8AA" label="SYS:OK" />
          <Pill color="#00C8AA" label="DATA:FRESH" />
          {severeCount > 0 && <Pill color="#FF0040" label={`SEVERE:${severeCount} ▲`} pulse />}
          {highCount   > 0 && <Pill color="#FF7700" label={`HIGH:${highCount}`} />}
        </div>

        {/* Search */}
        <div ref={containerRef} style={{ position: "relative", width: 230, flexShrink: 0 }}>
          <input
            type="text"
            placeholder="Search district…"
            aria-label="Search district"
            value={query}
            onChange={(e) => { setQuery(e.target.value); if (e.target.value.length < 2) setOpen(false); }}
            onFocus={() => results.length > 0 && setOpen(true)}
            style={{
              width: "100%", boxSizing: "border-box",
              borderRadius: 8, padding: "5px 30px 5px 10px",
              fontSize: 12, color: "#DCF0F5",
              background: "rgba(0,255,209,0.05)",
              border: "1px solid rgba(0,255,209,0.18)",
              outline: "none", ...mono,
            }}
          />
          <span
            style={{
              position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
              width: 5, height: 5, borderRadius: "50%",
              background: "#00FFD1", boxShadow: "0 0 5px #00FFD1",
              animation: "ops-active-blink 1.5s ease-in-out infinite",
            }}
          />

          {open && (results.length > 0 || outOfScope) && (
            <ul
              role="listbox"
              style={{
                position: "absolute", top: "100%", marginTop: 4, width: "100%",
                background: "#091829", border: "1px solid rgba(0,255,209,0.20)",
                borderRadius: 10, boxShadow: "0 8px 32px rgba(0,0,0,0.65)",
                zIndex: 9999, overflow: "hidden", padding: "4px 0",
                listStyle: "none", margin: "4px 0 0",
              }}
            >
              {outOfScope ? (
                <li
                  style={{ padding: "9px 12px", cursor: outOfScopeCity ? "pointer" : "default" }}
                  onClick={outOfScopeCity ? selectOosCity : undefined}
                  onMouseEnter={(e) => { if (outOfScopeCity) e.currentTarget.style.background = "rgba(0,255,209,0.05)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#DCF0F5", fontSize: 13, fontWeight: 600 }}>{outOfScope}</span>
                    {outOfScopeCity && <span style={{ fontSize: 11, color: "#FFE500", fontWeight: 700 }}>{outOfScopeCity.temp_c}°C {outOfScopeCity.icon}</span>}
                  </div>
                  <p style={{ color: "#3B6070", fontSize: 11, marginTop: 2 }}>
                    City weather marker · outside the 10-district MVP dataset
                  </p>
                  {outOfScopeCity && (
                    <p style={{ fontSize: 10, color: "#00FFD1", marginTop: 3, ...mono }}>
                      {outOfScopeCity.rainfall_mm_24h}mm/24h · {outOfScopeCity.wind_kmh} km/h · Click to open city analysis →
                    </p>
                  )}
                </li>
              ) : (
                results.filter((r) => MVP_DISTRICTS.has(r.district_id)).map((r) => (
                  <li
                    key={r.district_id}
                    role="option"
                    aria-selected={false}
                    onClick={() => selectResult(r)}
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", cursor: "pointer", gap: 8 }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(0,255,209,0.05)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                  >
                    <div>
                      <span style={{ color: "#DCF0F5", fontSize: 13, fontWeight: 600 }}>{r.name}</span>
                      <span style={{ color: "#3B6070", fontSize: 11, marginLeft: 6 }}>{r.province}</span>
                      <span style={{ marginLeft: 6, fontSize: 9, fontWeight: 700, padding: "2px 5px", borderRadius: 99, background: "rgba(0,255,209,0.10)", color: "#00FFD1", ...mono }}>MVP</span>
                    </div>
                    <span style={{ fontSize: 11, fontWeight: 700, flexShrink: 0, color: RISK_COLORS[r.risk_level as RiskLevel] }}>
                      {RISK_ICONS[r.risk_level as RiskLevel]} {r.risk_level}
                    </span>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      </div>

      {/* ── Horizontal mode bar ─────────────────────────────────────────── */}
      <WindyModeBar mode={mode} onChange={setMode} />

      {/* ── Risk Index badge ────────────────────────────────────────────── */}
      <RiskIndexBadge riskData={RISK_BY_ID} />

      {/* ── Copilot panel (slides in from right) ───────────────────────── */}
      <div
        style={{
          position: "absolute", top: 48, right: 0, bottom: 86, width: 300, zIndex: 700,
          display: "flex", flexDirection: "column",
          transform: showPanel ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <CopilotPanel
          district={selectedDistrict}
          explanation={selectedExplanation}
          selectedGridCell={selectedGridCell}
          selectedCity={selectedCity}
          onClose={handleClose}
        />
      </div>

      {/* ── Panel toggle tab — shows when panel is hidden ──────────────── */}
      {!showPanel && (
        <button
          onClick={() => setPanelClosed(false)}
          aria-label="Open analysis panel"
          style={{
            position: "absolute", right: 0, top: 48, bottom: 86,
            width: 28, zIndex: 690,
            background: "rgba(10,15,30,0.88)",
            borderLeft: "1px solid rgba(0,255,209,0.20)",
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", color: "#00C8AA",
            fontSize: 10, fontFamily: "var(--font-geist-mono, monospace)",
            writingMode: "vertical-rl", letterSpacing: "0.14em", fontWeight: 700,
            border: "none", outline: "none",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(0,255,209,0.08)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(10,15,30,0.88)"; }}
        >
          ◁ ANALYSIS
        </button>
      )}

      {/* ── Bottom: timeline + disclaimer ──────────────────────────────── */}
      <div
        style={{
          position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 500,
          background: "#0A0F1E",
        }}
      >
        <FloodTimeline
          events={floodEvents}
          activeYear={activeYear}
          onYearSelect={(yr) => setActiveYear((prev) => (prev === yr ? null : yr))}
        />
        <SafetyDisclaimer />
      </div>
    </div>
  );
}

function Pill({ color, label, pulse = false }: { color: string; label: string; pulse?: boolean }) {
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 5,
        padding: "3px 8px", borderRadius: 99,
        background: `${color}12`, border: `1px solid ${color}28`,
        ...mono, fontSize: 9, fontWeight: 700, color, letterSpacing: "0.08em", flexShrink: 0,
      }}
    >
      <span
        style={{
          width: 5, height: 5, borderRadius: "50%", background: color, flexShrink: 0,
          animation: pulse ? "ops-active-blink 1s ease-in-out infinite" : undefined,
        }}
      />
      {label}
    </div>
  );
}
