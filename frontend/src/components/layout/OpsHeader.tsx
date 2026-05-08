"use client";

import { useState, useRef, useEffect } from "react";
import { searchLocations, type ApiLocationResult } from "@/lib/api";
import { RISK_COLORS, RISK_ICONS } from "@/lib/risk-colors";
import type { RiskLevel } from "@/lib/types";
import type { MockRiskEntry } from "@/data/mock";
import { CITY_WEATHER, type CityWeather } from "@/data/pakistan-cities-weather";

interface Props {
  riskData: Map<string, MockRiskEntry>;
  onDistrictSelect: (result: ApiLocationResult) => void;
  onCitySearch?: (city: CityWeather) => void;
}

const MVP_DISTRICTS = new Set([
  "PK-SD-SKR","PK-SD-JCB","PK-SD-LRK","PK-PB-MUL","PK-PB-RWP",
  "PK-PB-LHR","PK-KP-PSH","PK-BL-QTA","PK-BL-NAS","PK-GB-GIL",
]);

export function OpsHeader({ riskData, onDistrictSelect, onCitySearch }: Props) {
  const [query, setQuery]               = useState("");
  const [results, setResults]           = useState<ApiLocationResult[]>([]);
  const [outOfScope, setOutOfScope]     = useState<string | null>(null);
  const [outOfScopeCity, setOutOfScopeCity] = useState<CityWeather | null>(null);
  const [open, setOpen]                 = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const entries      = Array.from(riskData.values());
  const severeCount  = entries.filter((e) => e.risk_level === "Severe").length;
  const highCount    = entries.filter((e) => e.risk_level === "High").length;
  const totalAlerts  = entries.filter((e) => e.risk_level === "Severe" || e.risk_level === "High").length;
  const peakRainfall = 62; // representative value from city-weather data

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
      } else {
        setOutOfScopeCity(null);
      }
      if (!data.length) {
        const directMatch = CITY_WEATHER.find((c) =>
          c.name.toLowerCase().includes(query.toLowerCase())
        );
        if (directMatch) {
          setOutOfScope(directMatch.name);
          setOutOfScopeCity(directMatch);
        }
      }
      setOpen(true);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function select(result: ApiLocationResult) {
    if (!MVP_DISTRICTS.has(result.district_id)) return;
    onDistrictSelect(result);
    setQuery(""); setOpen(false); setResults([]); setOutOfScope(null); setOutOfScopeCity(null);
  }

  function selectOutOfScopeCity() {
    if (outOfScopeCity && onCitySearch) onCitySearch(outOfScopeCity);
    setQuery(""); setOpen(false); setResults([]); setOutOfScope(null); setOutOfScopeCity(null);
  }

  const mono: React.CSSProperties = {
    fontFamily: "var(--font-geist-mono, monospace)",
  };

  return (
    <header style={{ background: "#050C14", borderBottom: "1px solid rgba(0,255,209,0.10)" }}>
      {/* Row 1 — 48px brand + status + search */}
      <div
        style={{
          height: 48,
          display: "flex",
          alignItems: "center",
          gap: 12,
          paddingLeft: 16,
          paddingRight: 16,
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 900,
              color: "#050C14",
              background: "linear-gradient(135deg, #00FFD1 0%, #3B82F6 100%)",
              boxShadow: "0 0 16px rgba(0,255,209,0.50)",
              flexShrink: 0,
            }}
          >
            ⬡
          </div>
          <div style={{ lineHeight: 1, ...mono }}>
            <div style={{ color: "#DCF0F5", fontWeight: 700, fontSize: 13, letterSpacing: "0.06em" }}>
              PAKFLOOD AI
            </div>
            <div style={{ color: "#00C8AA", fontSize: 9, letterSpacing: "0.18em", marginTop: 1 }}>
              FLOOD INTELLIGENCE SYSTEM
            </div>
          </div>
        </div>

        {/* Status pills — center */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto", marginRight: "auto" }}>
          <StatusPill color="#00C8AA" label="SYS:OK" />
          <StatusPill color="#00C8AA" label="DATA:FRESH" />
          {severeCount > 0 && (
            <StatusPill color="#FF2D55" label={`SEVERE:${severeCount} ▲`} pulse />
          )}
          {highCount > 0 && (
            <StatusPill color="#FF6B00" label={`HIGH:${highCount}`} />
          )}
        </div>

        {/* Search */}
        <div ref={containerRef} style={{ position: "relative", width: 240, flexShrink: 0 }}>
          <input
            type="text"
            placeholder="Search district…"
            aria-label="Search district"
            value={query}
            onChange={(e) => { setQuery(e.target.value); if (e.target.value.length < 2) setOpen(false); }}
            onFocus={() => results.length > 0 && setOpen(true)}
            style={{
              width: "100%",
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: 12,
              color: "#DCF0F5",
              background: "rgba(9,24,41,0.90)",
              border: "1px solid rgba(0,255,209,0.18)",
              outline: "none",
              ...mono,
              boxSizing: "border-box",
            }}
          />

          {/* Active indicator */}
          <div
            style={{
              position: "absolute",
              right: 10,
              top: "50%",
              transform: "translateY(-50%)",
              display: "flex",
              alignItems: "center",
              gap: 4,
              ...mono,
            }}
          >
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: "#00FFD1",
                boxShadow: "0 0 6px rgba(0,255,209,0.8)",
                animation: "ops-active-blink 1.5s ease-in-out infinite",
              }}
            />
            <span style={{ fontSize: 9, color: "#00C8AA", fontWeight: 700, letterSpacing: "0.08em" }}>
              ACTIVE
            </span>
          </div>

          {open && (results.length > 0 || outOfScope) && (
            <ul
              role="listbox"
              style={{
                position: "absolute",
                top: "100%",
                marginTop: 4,
                width: "100%",
                background: "#091829",
                border: "1px solid rgba(0,255,209,0.18)",
                borderRadius: 10,
                boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
                zIndex: 9999,
                overflow: "hidden",
                padding: "4px 0",
                listStyle: "none",
                margin: 0,
              }}
            >
              {outOfScope ? (
                <li
                  style={{ padding: "10px 12px", cursor: outOfScopeCity ? "pointer" : "default" }}
                  onClick={outOfScopeCity ? selectOutOfScopeCity : undefined}
                  onMouseEnter={(e) => { if (outOfScopeCity) e.currentTarget.style.background = "rgba(0,255,209,0.05)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ color: "#DCF0F5", fontSize: 13, fontWeight: 600 }}>{outOfScope}</span>
                    {outOfScopeCity && (
                      <span style={{ fontSize: 11, color: "#FFD60A", fontWeight: 700, ...mono }}>
                        {outOfScopeCity.temp_c}°C {outOfScopeCity.icon}
                      </span>
                    )}
                  </div>
                  <p style={{ color: "#3B6070", fontSize: 11, marginTop: 2 }}>
                    City weather marker · outside the 10-district MVP dataset
                  </p>
                  {outOfScopeCity && (
                    <p style={{ fontSize: 10, color: "#00FFD1", marginTop: 3, ...mono }}>
                      {outOfScopeCity.rainfall_mm_24h}mm/24h · {outOfScopeCity.wind_kmh} km/h {outOfScopeCity.wind_dir} · Click to open city analysis →
                    </p>
                  )}
                </li>
              ) : (
                results.filter((r) => MVP_DISTRICTS.has(r.district_id)).map((r) => (
                  <li
                    key={r.district_id}
                    role="option"
                    aria-selected={false}
                    onClick={() => select(r)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      cursor: "pointer",
                      gap: 8,
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(0,255,209,0.05)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                  >
                    <div>
                      <span style={{ color: "#DCF0F5", fontSize: 13, fontWeight: 600 }}>{r.name}</span>
                      <span style={{ color: "#3B6070", fontSize: 11, marginLeft: 6 }}>{r.province}</span>
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: 9,
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: 99,
                          background: "rgba(0,255,209,0.10)",
                          color: "#00FFD1",
                          ...mono,
                        }}
                      >
                        MVP
                      </span>
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

      {/* Row 2 — 28px KPI readout strip */}
      <div
        style={{
          height: 28,
          display: "flex",
          alignItems: "center",
          paddingLeft: 16,
          paddingRight: 16,
          gap: 0,
          background: "rgba(0,255,209,0.03)",
          borderTop: "1px solid rgba(0,255,209,0.06)",
          ...mono,
          fontSize: 10,
          color: "#00C8AA",
          letterSpacing: "0.10em",
          fontWeight: 600,
          overflow: "hidden",
          whiteSpace: "nowrap",
        }}
      >
        <span>DISTRICTS MONITORED: {entries.length}</span>
        <Divider />
        <span>ACTIVE ALERTS: {totalAlerts}</span>
        <Divider />
        <span>PEAK RAINFALL: {peakRainfall}mm/24h</span>
        <Divider />
        <span>SAR COVERAGE: 4 PASSES</span>
        <Divider />
        <span style={{ color: "#3B6070" }}>EDUCATIONAL PROTOTYPE · PMD · FFD · NDMA</span>
      </div>
    </header>
  );
}

function Divider() {
  return (
    <span
      style={{
        display: "inline-block",
        width: 1,
        height: 12,
        background: "rgba(0,255,209,0.15)",
        margin: "0 14px",
        verticalAlign: "middle",
        flexShrink: 0,
      }}
    />
  );
}

function StatusPill({
  color,
  label,
  pulse = false,
}: {
  color: string;
  label: string;
  pulse?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 8px",
        borderRadius: 99,
        background: `rgba(${hexToRgb(color)},0.08)`,
        border: `1px solid rgba(${hexToRgb(color)},0.25)`,
        fontFamily: "var(--font-geist-mono, monospace)",
        fontSize: 10,
        fontWeight: 700,
        color,
        letterSpacing: "0.08em",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          animation: pulse ? "ops-active-blink 1s ease-in-out infinite" : undefined,
        }}
      />
      {label}
    </div>
  );
}

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `${r},${g},${b}`;
}
