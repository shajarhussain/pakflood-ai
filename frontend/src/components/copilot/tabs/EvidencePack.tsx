"use client";

import type { MockRiskEntry } from "@/data/mock";

interface Props {
  district: MockRiskEntry;
}

interface SourceCard {
  id: string;
  name: string;
  icon: string;
  dot: string;
  status: string;
  role: string;
  details: string[];
  note: string;
}

const SOURCES: SourceCard[] = [
  {
    id: "imerg",
    name: "NASA GPM IMERG",
    icon: "🛰",
    dot: "#F59E0B",
    status: "stale 4h",
    role: "Primary rainfall signal",
    details: [
      "1-day:  ~48mm (simulated)",
      "3-day:  ~142mm",
      "7-day:  ~320mm  +340% anomaly",
    ],
    note: "IMERG-style rainfall simulation · Live source disabled in demo mode",
  },
  {
    id: "glofas",
    name: "GloFAS · ECMWF",
    icon: "💧",
    dot: "#22C55E",
    status: "fresh",
    role: "River discharge forecast",
    details: [
      "Alert level:  HIGH (simulated)",
      "Discharge:   ~8,400 m³/s Indus",
      "Upstream:    ELEVATED pressure",
    ],
    note: "GloFAS ERA5 simulation · Live river data planned for v2",
  },
  {
    id: "chirps",
    name: "CHIRPS · UCSB",
    icon: "🌍",
    dot: "#22C55E",
    status: "fresh",
    role: "30-year rainfall baseline",
    details: [
      "Anomaly:  +2.8σ (extreme)",
      "Baseline: 30-year avg",
      "Period:   Seasonal",
    ],
    note: "30-year climatology · used for anomaly calculation",
  },
  {
    id: "reliefweb",
    name: "ReliefWeb · OCHA",
    icon: "📰",
    dot: "#22D3EE",
    status: "live",
    role: "Humanitarian situation reports",
    details: [
      "Latest articles fetched live",
      "Pakistan flood queries",
      "Source confidence: ≥0.6",
    ],
    note: "Live public API · Articles shown where confidence ≥0.6",
  },
  {
    id: "historical",
    name: "Historical Event Match",
    icon: "📜",
    dot: "#F59E0B",
    status: "seed data",
    role: "Historical flood context",
    details: [
      "2010: Severely inundated",
      "2022: Catastrophic flooding",
      "Current signature → 2010 match",
    ],
    note: "Seed data from HDX · Not real-time",
  },
  {
    id: "sar",
    name: "Sentinel-1 SAR · ESA",
    icon: "🛰",
    dot: "#6B7280",
    status: "planned",
    role: "Flood extent mapping",
    details: [
      "Flood area detection",
      "Change detection",
      "10m resolution planned",
    ],
    note: "Satellite/SAR detection planned for v2 · ESA Copernicus feeds",
  },
];

export function EvidencePack({ district }: Props) {
  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      <div
        className="rounded-xl p-3"
        style={{ background: "rgba(59,130,246,0.07)", border: "1px solid rgba(59,130,246,0.18)" }}
      >
        <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: "#60A5FA" }}>
          Evidence & Source Pack · {district.name}
        </p>
        <p className="text-[11px] mt-0.5" style={{ color: "#64748B" }}>
          All data contributing to this risk assessment
        </p>
      </div>

      {SOURCES.map((s) => (
        <div
          key={s.id}
          className="rounded-xl p-3.5"
          style={{ background: "#111E35", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-base">{s.icon}</span>
              <div>
                <p className="text-xs font-semibold" style={{ color: "#F1F5F9" }}>{s.name}</p>
                <p className="text-[10px]" style={{ color: "#4B6280" }}>{s.role}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: s.dot, boxShadow: `0 0 4px ${s.dot}` }}
              />
              <span className="text-[10px] font-semibold" style={{ color: s.dot }}>{s.status}</span>
            </div>
          </div>

          <ul className="space-y-0.5 mb-2">
            {s.details.map((d, i) => (
              <li key={i} className="text-[11px] font-mono" style={{ color: "#94A3B8" }}>
                {d}
              </li>
            ))}
          </ul>

          {/* Mini bar for IMERG rainfall */}
          {s.id === "imerg" && (
            <div className="mb-2 space-y-1">
              {[
                { label: "1d", pct: 15 },
                { label: "3d", pct: 44 },
                { label: "7d", pct: 100 },
              ].map(({ label, pct }) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-[9px] w-4 shrink-0" style={{ color: "#4B6280" }}>{label}</span>
                  <div className="flex-1 rounded-full overflow-hidden" style={{ height: 3, background: "rgba(255,255,255,0.07)" }}>
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, background: `linear-gradient(90deg, #22D3EE88, #22D3EE)` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Discharge meter for GloFAS */}
          {s.id === "glofas" && (
            <div className="mb-2">
              <div className="flex gap-1">
                {["Normal","Watch","High","Severe"].map((lvl, i) => (
                  <div
                    key={lvl}
                    className="flex-1 h-1.5 rounded-sm"
                    style={{
                      background: i <= 2
                        ? ["#22C55E","#F59E0B","#F97316","#EF4444"][i]
                        : "rgba(255,255,255,0.08)",
                      opacity: i <= 2 ? 1 : 0.3,
                    }}
                  />
                ))}
              </div>
              <div className="flex justify-between mt-0.5">
                {["Normal","Watch","HIGH","Severe"].map((lvl) => (
                  <span key={lvl} className="text-[8px]" style={{ color: lvl === "HIGH" ? "#F97316" : "#4B6280" }}>
                    {lvl}
                  </span>
                ))}
              </div>
            </div>
          )}

          <p
            className="text-[10px] pt-2 leading-relaxed"
            style={{ color: "#4B6280", borderTop: "1px solid rgba(255,255,255,0.06)" }}
          >
            {s.note}
          </p>
        </div>
      ))}

      {/* Pipeline note */}
      <div
        className="rounded-lg p-3 text-[10px] leading-relaxed text-center"
        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", color: "#4B6280" }}
      >
        Source → Adapter → Registry → Features → ML Model → Explainer → UI
        <br />
        <span style={{ color: "#22D3EE" }}>Clean architecture · Circuit Breaker per adapter · Fallback to mock</span>
      </div>
    </div>
  );
}
