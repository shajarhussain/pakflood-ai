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

export function MissionHeader({ riskData, onDistrictSelect, onCitySearch }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ApiLocationResult[]>([]);
  const [outOfScope, setOutOfScope] = useState<string | null>(null);
  const [outOfScopeCity, setOutOfScopeCity] = useState<CityWeather | null>(null);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const entries = Array.from(riskData.values());
  const severeCount = entries.filter((e) => e.risk_level === "Severe").length;
  const highCount   = entries.filter((e) => e.risk_level === "High").length;

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length < 2) { setResults([]); setOutOfScope(null); setOpen(false); return; }
      const data = await searchLocations(query);
      setResults(data);
      const inScope = data.some((r) => MVP_DISTRICTS.has(r.district_id));
      const oos = !inScope && data.length > 0 ? data[0].name : null;
      setOutOfScope(oos);
      // Find matching city-weather marker for out-of-scope results
      if (oos) {
        const match = CITY_WEATHER.find((c) =>
          c.name.toLowerCase().includes(query.toLowerCase()) ||
          query.toLowerCase().includes(c.name.toLowerCase())
        ) ?? null;
        setOutOfScopeCity(match);
      } else {
        setOutOfScopeCity(null);
      }
      // Also check query directly against city weather if no API results
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
    if (outOfScopeCity && onCitySearch) {
      onCitySearch(outOfScopeCity);
    }
    setQuery(""); setOpen(false); setResults([]); setOutOfScope(null); setOutOfScopeCity(null);
  }

  return (
    <header
      className="flex items-center gap-3 px-4 shrink-0 z-20"
      style={{ height: 52, background: "#0D1526", borderBottom: "1px solid rgba(255,255,255,0.08)" }}
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-black text-white select-none"
          style={{
            background: "linear-gradient(135deg, #22D3EE 0%, #3B82F6 100%)",
            boxShadow: "0 0 14px rgba(34,211,238,0.45)",
          }}
        >
          ⬡
        </div>
        <div className="leading-none">
          <div className="text-white font-bold text-sm tracking-wide">PakFlood AI</div>
          <div
            className="text-[10px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: "#22D3EE" }}
          >
            Command Center
          </div>
        </div>
      </div>

      <div
        className="hidden xl:block text-xs border-l pl-4 ml-1"
        style={{ color: "#4B6280", borderColor: "rgba(255,255,255,0.08)" }}
      >
        Flood Intelligence · Forecast Simulation · Response Planning
      </div>

      {/* Search */}
      <div ref={containerRef} className="relative ml-auto w-56 sm:w-72">
        <input
          type="text"
          placeholder="Search district…"
          aria-label="Search district"
          value={query}
          onChange={(e) => { setQuery(e.target.value); if (e.target.value.length < 2) setOpen(false); }}
          onFocus={() => (results.length > 0) && setOpen(true)}
          className="w-full rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none transition"
          style={{
            background: "#1A2845",
            border: "1px solid rgba(255,255,255,0.10)",
          }}
        />
        {open && (results.length > 0 || outOfScope) && (
          <ul
            role="listbox"
            className="absolute top-full mt-1 w-full rounded-xl shadow-2xl z-50 overflow-hidden py-1"
            style={{ background: "#111E35", border: "1px solid rgba(255,255,255,0.12)" }}
          >
            {outOfScope ? (
              <li
                className="px-3 py-3 cursor-pointer transition"
                onClick={outOfScopeCity ? selectOutOfScopeCity : undefined}
                onMouseEnter={(e) => { if (outOfScopeCity) e.currentTarget.style.background = "#1F2F55"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <p className="text-slate-300 text-sm font-medium">{outOfScope}</p>
                  {outOfScopeCity && (
                    <span style={{ fontSize: 11, color: "#FCD34D", fontWeight: 700 }}>
                      {outOfScopeCity.temp_c}°C {outOfScopeCity.icon}
                    </span>
                  )}
                </div>
                <p className="text-slate-500 text-xs mt-0.5">
                  City weather marker · outside the 10-district MVP dataset
                </p>
                {outOfScopeCity && (
                  <p style={{ fontSize: 10, color: "#22D3EE", marginTop: 3 }}>
                    {outOfScopeCity.rainfall_mm_24h}mm/24h · {outOfScopeCity.wind_kmh} km/h {outOfScopeCity.wind_dir} · Click to open city analysis →
                  </p>
                )}
                {!outOfScopeCity && (
                  <p style={{ fontSize: 10, color: "#4B6280", marginTop: 3 }}>
                    Full Pakistan district coverage planned.
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
                  className="flex items-center justify-between px-3 py-2.5 cursor-pointer transition"
                  style={{ gap: 8 }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#1F2F55")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <div>
                    <span className="text-white text-sm font-semibold">{r.name}</span>
                    <span className="text-slate-400 text-xs ml-2">{r.province}</span>
                    <span
                      className="ml-2 text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ background: "rgba(34,211,238,0.12)", color: "#22D3EE" }}
                    >
                      MVP
                    </span>
                  </div>
                  <span
                    className="text-xs font-bold shrink-0"
                    style={{ color: RISK_COLORS[r.risk_level as RiskLevel] }}
                  >
                    {RISK_ICONS[r.risk_level as RiskLevel]} {r.risk_level}
                  </span>
                </li>
              ))
            )}
          </ul>
        )}
      </div>

      {/* Alert pills */}
      <div className="hidden sm:flex items-center gap-2">
        {severeCount > 0 && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
            style={{
              background: "rgba(239,68,68,0.14)",
              border: "1px solid rgba(239,68,68,0.40)",
              color: "#FCA5A5",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-live-blink" />
            SEVERE {severeCount}
          </div>
        )}
        {highCount > 0 && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
            style={{
              background: "rgba(249,115,22,0.12)",
              border: "1px solid rgba(249,115,22,0.35)",
              color: "#FDBA74",
            }}
          >
            HIGH {highCount}
          </div>
        )}
      </div>

      {/* Demo badge */}
      <div
        className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium shrink-0"
        style={{
          background: "rgba(139,92,246,0.14)",
          border: "1px solid rgba(139,92,246,0.35)",
          color: "#C4B5FD",
        }}
      >
        ◐ Demo
      </div>
    </header>
  );
}
