"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";
import { getGridCellColor } from "@/lib/grid-risk";

const RiskBrief              = dynamic(() => import("./tabs/RiskBrief").then((m) => m.RiskBrief),                       { ssr: false });
const CopilotChat            = dynamic(() => import("./tabs/CopilotChat").then((m) => m.CopilotChat),                   { ssr: false });
const SimulationLab          = dynamic(() => import("./tabs/SimulationLab").then((m) => m.SimulationLab),               { ssr: false });
const ResponsePlan           = dynamic(() => import("./tabs/ResponsePlan").then((m) => m.ResponsePlan),                 { ssr: false });
const EvidencePack           = dynamic(() => import("./tabs/EvidencePack").then((m) => m.EvidencePack),                 { ssr: false });
const SAREvidencePanel       = dynamic(() => import("./tabs/SAREvidencePanel").then((m) => m.SAREvidencePanel),         { ssr: false });
const EducationalSourcesPanel = dynamic(() => import("./tabs/EducationalSourcesPanel").then((m) => m.EducationalSourcesPanel), { ssr: false });

interface Props {
  district: MockRiskEntry | null;
  explanation: RiskExplanation | null;
  selectedGridCell: GridCell | null;
  selectedCity: CityWeather | null;
  onClose: () => void;
}

type Tab = { id: string; short: string; requiresDistrict: boolean };
const TABS: Tab[] = [
  { id: "brief",    short: "Brief",   requiresDistrict: true  },
  { id: "copilot",  short: "Copilot", requiresDistrict: true  },
  { id: "simulate", short: "Sim",     requiresDistrict: true  },
  { id: "response", short: "Action",  requiresDistrict: true  },
  { id: "evidence", short: "Data",    requiresDistrict: true  },
  { id: "sar",      short: "SAR",     requiresDistrict: false },
  { id: "sources",  short: "Sources", requiresDistrict: false },
];

export function CopilotPanel({ district, explanation, selectedGridCell, selectedCity, onClose }: Props) {
  const [activeTab, setActiveTab] = useState("brief");

  const riskColor =
    explanation?.risk_level === "Severe"   ? "#EF4444"
    : explanation?.risk_level === "High"   ? "#F97316"
    : explanation?.risk_level === "Moderate" ? "#F59E0B"
    : "#22C55E";

  const showHeader = district && explanation;

  return (
    <aside
      aria-label="Risk explanation panel"
      className="flex flex-col flex-1 overflow-hidden"
      style={{
        width: "100%",
        background: "#0D1526",
        borderLeft: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Panel header — only when district selected */}
      {showHeader && (
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-2 h-8 rounded-full shrink-0"
              style={{ background: riskColor, boxShadow: `0 0 8px ${riskColor}88` }}
            />
            <div>
              <p className="text-sm font-bold" style={{ color: "#F1F5F9" }}>{district.name}</p>
              <p className="text-[10px]" style={{ color: "#4B6280" }}>
                {district.province} ·{" "}
                <span style={{ color: riskColor, fontWeight: 600 }}>{explanation.risk_level}</span>
                {" "}· {(district.risk_score * 100).toFixed(0)}% risk
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close risk panel"
            className="w-7 h-7 rounded-lg flex items-center justify-center transition text-sm"
            style={{ color: "#4B6280", background: "rgba(255,255,255,0.05)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#F1F5F9"; e.currentTarget.style.background = "rgba(255,255,255,0.10)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#4B6280"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Grid cell header */}
      {!showHeader && selectedGridCell && (
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-2 h-8 rounded-full shrink-0"
              style={{
                background: getGridCellColor(selectedGridCell.risk_level),
                boxShadow: `0 0 8px ${getGridCellColor(selectedGridCell.risk_level)}88`,
              }}
            />
            <div>
              <p className="text-sm font-bold" style={{ color: "#F1F5F9" }}>{selectedGridCell.zone_label}</p>
              <p className="text-[10px]" style={{ color: "#4B6280" }}>
                Grid Zone ·{" "}
                <span style={{ color: getGridCellColor(selectedGridCell.risk_level), fontWeight: 600 }}>
                  {selectedGridCell.risk_level}
                </span>
                {" "}· {Math.round(selectedGridCell.score * 100)}% score
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close risk panel"
            className="w-7 h-7 rounded-lg flex items-center justify-center transition text-sm"
            style={{ color: "#4B6280", background: "rgba(255,255,255,0.05)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#F1F5F9"; e.currentTarget.style.background = "rgba(255,255,255,0.10)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#4B6280"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
          >
            ✕
          </button>
        </div>
      )}

      {/* City weather header */}
      {!showHeader && !selectedGridCell && selectedCity && (
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-lg"
              style={{ background: "rgba(252,211,77,0.12)", border: "1px solid rgba(252,211,77,0.22)" }}
            >
              {selectedCity.icon}
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: "#F1F5F9" }}>{selectedCity.name}</p>
              <p className="text-[10px]" style={{ color: "#4B6280" }}>
                {selectedCity.temp_c}°C · {selectedCity.condition} · {selectedCity.rainfall_mm_24h}mm/24h
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close risk panel"
            className="w-7 h-7 rounded-lg flex items-center justify-center transition text-sm"
            style={{ color: "#4B6280", background: "rgba(255,255,255,0.05)" }}
            onMouseEnter={(e) => { e.currentTarget.style.color = "#F1F5F9"; e.currentTarget.style.background = "rgba(255,255,255,0.10)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = "#4B6280"; e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Empty state header when nothing selected */}
      {!showHeader && !selectedGridCell && !selectedCity && (
        <div
          className="flex items-center gap-2.5 px-4 py-3 shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
            style={{ background: "rgba(0,255,209,0.10)", border: "1px solid rgba(0,255,209,0.18)" }}
          >
            🗺
          </div>
          <div>
            <p className="text-sm font-bold" style={{ color: "#F1F5F9" }}>AI Flood Copilot</p>
            <p className="text-[10px]" style={{ color: "#4B6280" }}>Select a district, grid zone, or city</p>
          </div>
        </div>
      )}

      {/* Tab bar — always visible */}
      <div
        className="flex shrink-0 overflow-x-auto"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        {TABS.map((tab) => {
          const disabled = tab.requiresDistrict && !district;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => !disabled && setActiveTab(tab.id)}
              disabled={disabled}
              className="flex-1 py-2.5 text-[10px] font-semibold transition shrink-0 relative"
              style={{
                color: disabled ? "#2D3A50" : isActive ? "#F1F5F9" : "#4B6280",
                background: isActive ? "rgba(0,255,209,0.06)" : "transparent",
                minWidth: 48,
                cursor: disabled ? "not-allowed" : "pointer",
              }}
            >
              {tab.short}
              {isActive && (
                <span
                  className="absolute bottom-0 left-0 right-0 h-0.5 rounded-t-full"
                  style={{ background: "#00FFD1" }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
        {/* District-required tabs */}
        {TABS.filter((t) => t.requiresDistrict).map((tab) =>
          activeTab === tab.id ? (
            <div key={tab.id}>
              {district && explanation ? (
                <div className="px-4 py-4">
                  {tab.id === "brief"    && <RiskBrief district={district} explanation={explanation} />}
                  {tab.id === "copilot"  && <CopilotChat district={district} explanation={explanation} />}
                  {tab.id === "simulate" && <SimulationLab district={district} />}
                  {tab.id === "response" && <ResponsePlan district={district} explanation={explanation} />}
                  {tab.id === "evidence" && <EvidencePack district={district} />}
                </div>
              ) : selectedGridCell ? (
                <GridCellAnalysis cell={selectedGridCell} />
              ) : selectedCity ? (
                <CityAnalysis city={selectedCity} />
              ) : (
                <DistrictNudge />
              )}
            </div>
          ) : null
        )}

        {/* Global tabs — always available */}
        {activeTab === "sar"     && <SAREvidencePanel />}
        {activeTab === "sources" && <EducationalSourcesPanel />}
      </div>

      {/* Bottom disclaimer */}
      <div
        className="shrink-0 px-4 py-2.5 text-[10px] text-center"
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          color: "#4B6280",
          background: "#050C14",
        }}
      >
        ⚠ Educational prototype · Not an authoritative emergency alert ·{" "}
        <span style={{ color: "#94A3B8" }}>PMD · FFD · NDMA · PDMA</span>
      </div>
    </aside>
  );
}

function GridCellAnalysis({ cell }: { cell: GridCell }) {
  const color = getGridCellColor(cell.risk_level);
  const pct   = Math.round(cell.score * 100);
  const rainfallColor = cell.rainfall_mm >= 50 ? "#EF4444" : cell.rainfall_mm >= 25 ? "#F97316" : "#00FFD1";

  return (
    <div className="px-4 py-4 flex flex-col gap-4">
      {/* Risk score */}
      <div
        className="rounded-xl p-4"
        style={{ background: `${color}11`, border: `1px solid ${color}33` }}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-bold" style={{ color }}>
            {cell.risk_level} Flood Risk Zone
          </span>
          <span className="text-xl font-black" style={{ color }}>{pct}%</span>
        </div>
        <div className="w-full h-2 rounded-full" style={{ background: "rgba(255,255,255,0.07)" }}>
          <div
            className="h-2 rounded-full transition-all"
            style={{ width: `${pct}%`, background: color, boxShadow: `0 0 6px ${color}66` }}
          />
        </div>
        <p className="text-[10px] mt-2" style={{ color: "#64748B" }}>{cell.zone_label}</p>
      </div>

      {/* Key factors */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: "#4B6280" }}>
          Risk Factors
        </p>
        <div className="flex flex-col gap-1.5">
          {cell.main_factors.map((f, i) => (
            <div
              key={i}
              className="flex items-start gap-2 rounded-lg px-3 py-2 text-xs"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", color: "#CBD5E1" }}
            >
              <span style={{ color, flexShrink: 0 }}>▸</span>
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* Rainfall */}
      <div
        className="rounded-lg px-3 py-2.5 flex items-center justify-between"
        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
      >
        <span className="text-xs" style={{ color: "#94A3B8" }}>24h Rainfall (zone est.)</span>
        <span className="text-sm font-bold" style={{ color: rainfallColor }}>
          {cell.rainfall_mm} mm
        </span>
      </div>

      {/* Actions */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: "#4B6280" }}>
          Recommended Actions
        </p>
        {cell.risk_level === "Severe" || cell.risk_level === "High" ? (
          <div className="flex flex-col gap-1.5">
            {["Activate district emergency operations centre", "Pre-position rescue boats and relief supplies", "Issue evacuation advisories for low-lying areas", "Coordinate with NDMA/PDMA for rapid response"].map((a, i) => (
              <div key={i} className="text-xs px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.15)", color: "#FCA5A5" }}>
                {a}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {["Monitor rainfall forecasts closely", "Inspect flood protection infrastructure", "Brief community response teams"].map((a, i) => (
              <div key={i} className="text-xs px-3 py-2 rounded-lg" style={{ background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.15)", color: "#FDE68A" }}>
                {a}
              </div>
            ))}
          </div>
        )}
      </div>

      <div
        className="rounded-lg px-3 py-2 text-[10px] text-center"
        style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", color: "#4B6280" }}
      >
        Click a district for detailed AI analysis · Data: demo heuristic model
      </div>
    </div>
  );
}

function CityAnalysis({ city }: { city: CityWeather }) {
  const floodRisk = city.rainfall_mm_24h >= 50 ? { label: "High", color: "#EF4444" }
    : city.rainfall_mm_24h >= 25 ? { label: "Moderate", color: "#F97316" }
    : city.rainfall_mm_24h >= 10 ? { label: "Elevated", color: "#F59E0B" }
    : { label: "Low", color: "#22C55E" };

  const windArrow = ["↑","↗","→","↘","↓","↙","←","↖"][Math.round(((city.wind_deg % 360) / 360) * 8) % 8];
  const humidityColor = city.humidity_pct >= 80 ? "#00FFD1" : city.humidity_pct >= 60 ? "#7DD3FC" : "#4B6280";

  return (
    <div className="px-4 py-4 flex flex-col gap-4">
      {/* Weather summary card */}
      <div
        className="rounded-xl p-4"
        style={{ background: "rgba(252,211,77,0.06)", border: "1px solid rgba(252,211,77,0.18)" }}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-black" style={{ color: "#FCD34D" }}>{city.temp_c}°C</p>
            <p className="text-xs mt-0.5" style={{ color: "#94A3B8" }}>{city.icon} {city.condition}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px]" style={{ color: "#4B6280" }}>Flood Risk</p>
            <p className="text-sm font-bold" style={{ color: floodRisk.color }}>{floodRisk.label}</p>
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "Rainfall 24h", value: `${city.rainfall_mm_24h} mm`, color: city.rainfall_mm_24h >= 25 ? "#F97316" : "#00FFD1" },
          { label: "Humidity", value: `${city.humidity_pct}%`, color: humidityColor },
          { label: "Wind Speed", value: `${city.wind_kmh} km/h`, color: "#7DD3FC" },
          { label: "Wind Direction", value: `${windArrow} ${city.wind_dir}`, color: "#7DD3FC" },
        ].map((m) => (
          <div
            key={m.label}
            className="rounded-lg px-3 py-2.5"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
          >
            <p className="text-[9px] font-semibold uppercase tracking-widest" style={{ color: "#4B6280" }}>{m.label}</p>
            <p className="text-sm font-bold mt-0.5" style={{ color: m.color }}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Flood risk interpretation */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: "#4B6280" }}>
          Situation Assessment
        </p>
        <div
          className="rounded-lg px-3 py-3 text-xs leading-relaxed"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", color: "#94A3B8" }}
        >
          {city.rainfall_mm_24h >= 50
            ? `${city.name} is experiencing heavy rainfall. Combined with ${city.humidity_pct}% humidity and ${city.wind_kmh} km/h winds, surface runoff and flash flooding risk is elevated. Monitor drainage systems and low-lying areas closely.`
            : city.rainfall_mm_24h >= 25
            ? `${city.name} has moderate rainfall in the last 24h. Soil saturation may be building — watch for urban flooding if rainfall continues.`
            : `Current conditions at ${city.name} show low direct flood risk. Rainfall is within normal range. Continue monitoring upstream catchment areas.`
          }
        </div>
      </div>

      {city.is_mvp_district ? (
        <div
          className="rounded-lg px-3 py-2 flex items-center gap-2 text-[10px]"
          style={{ background: "rgba(0,255,209,0.07)", border: "1px solid rgba(0,255,209,0.18)", color: "#00FFD1" }}
        >
          <span>●</span>
          MVP monitoring district — click the district boundary for full AI risk analysis
        </div>
      ) : (
        <div
          className="rounded-lg px-3 py-3 flex flex-col gap-1.5"
          style={{ background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.22)" }}
        >
          <p className="text-[10px] font-semibold" style={{ color: "#FCD34D" }}>
            ⓘ Outside Current MVP Dataset
          </p>
          <p className="text-[10px] leading-relaxed" style={{ color: "#94A3B8" }}>
            {city.name} is included as a city weather marker but is outside the current 10-district flood-risk MVP dataset.
            District-level AI analysis, simulation, and response planning are not yet available for this location.
          </p>
          <p className="text-[10px]" style={{ color: "#64748B" }}>
            Full Pakistan district coverage planned in v2.
          </p>
        </div>
      )}

      <div
        className="rounded-lg px-3 py-2 text-[10px] text-center"
        style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", color: "#4B6280" }}
      >
        Demo weather data · Live integration planned · Source: PMD/FFD
      </div>
    </div>
  );
}

function DistrictNudge() {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center gap-4">
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
        style={{ background: "rgba(0,255,209,0.07)", border: "1px solid rgba(0,255,209,0.15)" }}
      >
        📍
      </div>
      <div>
        <p className="text-sm font-semibold" style={{ color: "#F1F5F9" }}>Select a Feature</p>
        <p className="text-xs mt-1 leading-relaxed" style={{ color: "#4B6280" }}>
          Click a district, grid zone, or city label on the map to open AI risk analysis, simulation, and response planning.
        </p>
      </div>
      <div
        className="rounded-lg px-3 py-2 text-[10px] text-center"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.07)",
          color: "#4B6280",
        }}
      >
        MVP: <span style={{ color: "#00FFD1" }}>Sukkur · Jacobabad · Larkana · Multan · and more</span>
      </div>
    </div>
  );
}
