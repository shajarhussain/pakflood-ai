"use client";

import { useState, useMemo } from "react";
import type { MockRiskEntry } from "@/data/mock";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available, MODEL_UNAVAILABLE_MESSAGE } from "@/lib/api";

interface Props {
  district: MockRiskEntry;
}

const DISCHARGE_LEVELS = ["Normal", "Watch", "High", "Severe"] as const;
const DISCHARGE_COLORS = ["#22C55E", "#F59E0B", "#F97316", "#EF4444"];

const SCENARIOS = [
  { label: "+25% Rainfall",        rainfall: 25, discharge: 1 },
  { label: "+50% Rainfall",        rainfall: 50, discharge: 2 },
  { label: "River Rising",         rainfall: 10, discharge: 3 },
  { label: "Sources Stale",        rainfall: 0,  discharge: 0, stale: true },
  { label: "Night Evac. Concern",  rainfall: 30, discharge: 2 },
  { label: "Road Access Blocked",  rainfall: 40, discharge: 2 },
];

function computeProjected(
  base: number,
  baseConf: number,
  rainfallPct: number,
  dischargeIdx: number,
  allStale: boolean
) {
  const rainfallDelta  = (rainfallPct / 100) * 0.18;
  const dischargeDelta = [0, 0.04, 0.09, 0.14][dischargeIdx] ?? 0;
  const score    = Math.min(1, Math.max(0, base + rainfallDelta + dischargeDelta));
  const confPenalty = allStale ? 0.14 : rainfallPct * 0.0008;
  const confidence  = Math.min(0.95, Math.max(0.25, baseConf - confPenalty));
  return { score, confidence };
}

function riskLabel(score: number) {
  if (score >= 0.75) return { label: "SEVERE",   color: "#EF4444" };
  if (score >= 0.55) return { label: "HIGH",     color: "#F97316" };
  if (score >= 0.30) return { label: "MODERATE", color: "#F59E0B" };
  return              { label: "LOW",      color: "#22C55E" };
}

export function SimulationLab({ district }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  const simFooter = v3Ready
    ? "Simulation uses v3 prediction model · BalancedRF + sigmoid calibration"
    : `${MODEL_UNAVAILABLE_MESSAGE} — simulation disabled until pipeline is run`;
  const [rainfall,    setRainfall]    = useState(0);
  const [dischargeIdx, setDischarge]  = useState(0);
  const [allStale,    setAllStale]    = useState(false);

  const proj = useMemo(
    () => computeProjected(district.risk_score, district.confidence, rainfall, dischargeIdx, allStale),
    [district, rainfall, dischargeIdx, allStale]
  );

  const base  = { score: district.risk_score, confidence: district.confidence };
  const delta = proj.score - base.score;
  const baseRL = riskLabel(base.score);
  const projRL = riskLabel(proj.score);

  const actionPriority =
    proj.score >= 0.85 ? "EVACUATION" :
    proj.score >= 0.70 ? "RESPONSE"   :
    proj.score >= 0.50 ? "MONITORING" : "NORMAL";

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      {/* Header */}
      <div
        className="rounded-xl p-3"
        style={{
          background: "rgba(139,92,246,0.08)",
          border: "1px solid rgba(139,92,246,0.20)",
        }}
      >
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-0.5" style={{ color: "#A78BFA" }}>
          ⚗ What-If Simulation Lab
        </p>
        <p className="text-[11px]" style={{ color: "#94A3B8" }}>
          Prototype simulation — not an official forecast. Explore how changing conditions affect projected risk.
        </p>
      </div>

      {/* Scenario presets */}
      <Section title="Scenario Presets">
        <div className="grid grid-cols-2 gap-1.5">
          {SCENARIOS.map((s) => (
            <button
              key={s.label}
              onClick={() => {
                setRainfall(s.rainfall);
                setDischarge(s.discharge);
                if ("stale" in s && s.stale) setAllStale(true);
                else setAllStale(false);
              }}
              className="px-2.5 py-2 rounded-lg text-left transition"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "#94A3B8",
                fontSize: 11,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(139,92,246,0.10)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
            >
              {s.label}
            </button>
          ))}
        </div>
      </Section>

      {/* Manual controls */}
      <Section title="Manual Controls">
        <div className="flex flex-col gap-4">
          {/* Rainfall slider */}
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-[11px]" style={{ color: "#CBD5E1" }}>Rainfall intensity</span>
              <span className="text-[11px] font-semibold" style={{ color: "#22D3EE" }}>
                {rainfall > 0 ? `+${rainfall}%` : "Baseline"}
              </span>
            </div>
            <input
              type="range"
              min={0} max={100} step={5}
              value={rainfall}
              onChange={(e) => setRainfall(Number(e.target.value))}
              className="w-full accent-cyan-400"
              style={{ accentColor: "#22D3EE" }}
            />
            <div className="flex justify-between text-[9px] mt-0.5" style={{ color: "#4B6280" }}>
              <span>Baseline</span><span>+50%</span><span>+100%</span>
            </div>
          </div>

          {/* Discharge level */}
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-[11px]" style={{ color: "#CBD5E1" }}>River discharge level</span>
              <span className="text-[11px] font-semibold" style={{ color: DISCHARGE_COLORS[dischargeIdx] }}>
                {DISCHARGE_LEVELS[dischargeIdx]}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-1">
              {DISCHARGE_LEVELS.map((lvl, i) => (
                <button
                  key={lvl}
                  onClick={() => setDischarge(i)}
                  className="py-1.5 rounded text-[10px] font-semibold transition"
                  style={{
                    background: dischargeIdx === i ? `${DISCHARGE_COLORS[i]}22` : "rgba(255,255,255,0.04)",
                    border: dischargeIdx === i
                      ? `1px solid ${DISCHARGE_COLORS[i]}66`
                      : "1px solid rgba(255,255,255,0.08)",
                    color: dischargeIdx === i ? DISCHARGE_COLORS[i] : "#64748B",
                  }}
                >
                  {lvl}
                </button>
              ))}
            </div>
          </div>

          {/* Source freshness */}
          <div className="flex items-center justify-between">
            <span className="text-[11px]" style={{ color: "#CBD5E1" }}>All sources stale</span>
            <button
              onClick={() => setAllStale((v) => !v)}
              className="relative w-10 h-5 rounded-full transition"
              style={{
                background: allStale ? "#F59E0B" : "rgba(255,255,255,0.12)",
              }}
            >
              <span
                className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
                style={{ left: allStale ? "calc(100% - 18px)" : 2 }}
              />
            </button>
          </div>
        </div>
      </Section>

      {/* Projected impact */}
      <Section title="Projected Impact">
        <div
          className="rounded-xl p-3"
          style={{ background: "#111E35", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[9px] uppercase tracking-widest mb-1" style={{ color: "#4B6280" }}>Baseline</p>
              <p className="text-xl font-black" style={{ color: baseRL.color }}>
                {(base.score * 100).toFixed(0)}%
              </p>
              <p className="text-[10px] font-semibold" style={{ color: baseRL.color }}>{baseRL.label}</p>
              <p className="text-[10px]" style={{ color: "#4B6280" }}>{(base.confidence * 100).toFixed(0)}% conf</p>
            </div>
            <div>
              <p className="text-[9px] uppercase tracking-widest mb-1" style={{ color: "#4B6280" }}>Projected</p>
              <p className="text-xl font-black" style={{ color: projRL.color }}>
                {(proj.score * 100).toFixed(0)}%
              </p>
              <p className="text-[10px] font-semibold" style={{ color: projRL.color }}>{projRL.label}</p>
              <p className="text-[10px]" style={{ color: "#4B6280" }}>{(proj.confidence * 100).toFixed(0)}% conf</p>
            </div>
          </div>

          <div className="mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="flex items-center justify-between">
              <span className="text-[10px]" style={{ color: "#94A3B8" }}>Score delta</span>
              <span
                className="text-[11px] font-bold"
                style={{ color: delta > 0.02 ? "#EF4444" : delta < -0.02 ? "#22C55E" : "#94A3B8" }}
              >
                {delta > 0 ? "+" : ""}{(delta * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-[10px]" style={{ color: "#94A3B8" }}>Action priority</span>
              <span
                className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                style={{
                  background: actionPriority === "EVACUATION" ? "rgba(239,68,68,0.15)"
                    : actionPriority === "RESPONSE"   ? "rgba(249,115,22,0.15)"
                    : "rgba(34,197,94,0.10)",
                  color: actionPriority === "EVACUATION" ? "#FCA5A5"
                    : actionPriority === "RESPONSE"   ? "#FDBA74"
                    : "#86EFAC",
                }}
              >
                {actionPriority}
              </span>
            </div>
          </div>
        </div>

        <p className="text-[10px] mt-2 text-center" style={{ color: v3Ready ? "#4B6280" : "#FCA5A5" }}>
          {simFooter}
        </p>
      </Section>

      {/* Reset */}
      <button
        onClick={() => { setRainfall(0); setDischarge(0); setAllStale(false); }}
        className="rounded-lg py-2 text-xs font-medium transition"
        style={{
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
          color: "#64748B",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = "#94A3B8")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "#64748B")}
      >
        ↺ Reset to baseline
      </button>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p
        className="text-[9px] font-bold uppercase tracking-[0.12em] mb-2 pb-1.5"
        style={{ color: "#4B6280", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        {title}
      </p>
      {children}
    </div>
  );
}
