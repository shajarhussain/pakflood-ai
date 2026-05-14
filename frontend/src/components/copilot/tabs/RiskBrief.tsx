"use client";

import type { MockRiskEntry } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import { RISK_COLORS } from "@/lib/risk-colors";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available, MODEL_UNAVAILABLE_MESSAGE } from "@/lib/api";

interface Props {
  district: MockRiskEntry;
  explanation: RiskExplanation;
}

const RISK_GLOW: Record<string, string> = {
  Severe:   "rgba(239,68,68,0.25)",
  High:     "rgba(249,115,22,0.20)",
  Moderate: "rgba(245,158,11,0.18)",
  Low:      "rgba(34,197,94,0.18)",
};
const RISK_BG: Record<string, string> = {
  Severe:   "rgba(239,68,68,0.12)",
  High:     "rgba(249,115,22,0.10)",
  Moderate: "rgba(245,158,11,0.10)",
  Low:      "rgba(34,197,94,0.10)",
};

const SOURCES = [
  { id: "IMERG",     dot: "#F59E0B", status: "stale 4h",  role: "rainfall signal"  },
  { id: "CHIRPS",    dot: "#22C55E", status: "fresh",      role: "anomaly baseline" },
  { id: "GloFAS",    dot: "#22C55E", status: "fresh",      role: "river discharge"  },
  { id: "ReliefWeb", dot: "#22D3EE", status: "live",       role: "situation intel"  },
  { id: "FFD/PMD",   dot: "#8B5CF6", status: "demo mode",  role: "official bulletin"},
];

const MOCK_FACTORS = [
  { label: "7-day rainfall anomaly",      weight: 0.91 },
  { label: "Near Indus floodplain",       weight: 0.78 },
  { label: "Historical flood frequency",  weight: 0.65 },
  { label: "Low elevation & slope",       weight: 0.52 },
  { label: "High population density",     weight: 0.44 },
];

export function RiskBrief({ district, explanation }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  const trained = modelStatus?.last_trained_iso?.slice(0, 10) ?? "";
  const modelLabel = v3Ready
    ? `Model: Real prediction v3 · BalancedRF + ${modelStatus?.calibration_method ?? "sigmoid"}${trained ? ` (last trained ${trained})` : ""}`
    : `Model: ${MODEL_UNAVAILABLE_MESSAGE}`;
  const color  = RISK_COLORS[explanation.risk_level] ?? "#94A3B8";
  const glow   = RISK_GLOW[explanation.risk_level]   ?? "transparent";
  const bg     = RISK_BG[explanation.risk_level]     ?? "transparent";
  const confPct = (explanation.confidence * 100).toFixed(0);
  const factors = district.top_factors.length > 0
    ? district.top_factors.map((f, i) => ({ label: f, weight: MOCK_FACTORS[i]?.weight ?? 0.5 }))
    : MOCK_FACTORS.slice(0, 3);

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      {/* Risk score card */}
      <div
        className="rounded-xl p-4"
        style={{ background: bg, border: `1px solid ${color}44`, boxShadow: `0 0 20px ${glow}` }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-1" style={{ color }}>
              Risk Assessment
            </p>
            <p className="text-2xl font-black tracking-tight" style={{ color }}>
              {explanation.risk_level.toUpperCase()}
            </p>
            <p className="text-xs mt-0.5" style={{ color: "#94A3B8" }}>
              Flood Intelligence · 72h window
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-black" style={{ color: "#F1F5F9" }}>
              {(district.risk_score * 100).toFixed(0)}%
            </div>
            <div className="text-[10px]" style={{ color: "#64748B" }}>Risk Score</div>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="mt-3">
          <div className="flex justify-between mb-1">
            <span className="text-[10px]" style={{ color: "#64748B" }}>Confidence</span>
            <span className="text-[10px] font-semibold" style={{ color: "#94A3B8" }}>{confPct}%</span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 4, background: "rgba(255,255,255,0.08)" }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${confPct}%`,
                background: `linear-gradient(90deg, ${color}88, ${color})`,
              }}
            />
          </div>
        </div>

        <p className="text-[10px] mt-2" style={{ color: v3Ready ? "#4B6280" : "#FCA5A5" }}>
          {modelLabel}
        </p>
      </div>

      {/* Source health */}
      <Section title="Source Health">
        <div className="flex flex-col gap-1.5">
          {SOURCES.map((s) => (
            <div key={s.id} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: s.dot, boxShadow: `0 0 4px ${s.dot}` }}
                />
                <span className="text-xs font-semibold" style={{ color: "#94A3B8" }}>{s.id}</span>
              </div>
              <div className="text-right">
                <span className="text-[10px]" style={{ color: "#4B6280" }}>{s.status} · {s.role}</span>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Top risk factors */}
      <Section title="Why This District Is At Risk">
        <div className="flex flex-col gap-2">
          {factors.map((f) => (
            <div key={f.label}>
              <div className="flex justify-between mb-0.5">
                <span className="text-[11px]" style={{ color: "#CBD5E1" }}>{f.label}</span>
                <span className="text-[10px] font-semibold" style={{ color: "#94A3B8" }}>
                  {(f.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div className="rounded-full overflow-hidden" style={{ height: 3, background: "rgba(255,255,255,0.08)" }}>
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${f.weight * 100}%`,
                    background: `linear-gradient(90deg, #22D3EE88, #22D3EE)`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Historical exposure */}
      <Section title="Historical Exposure">
        <ul className="space-y-1">
          {explanation.historical_evidence.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-[11px]" style={{ color: "#CBD5E1" }}>
              <span style={{ color: "#F59E0B", marginTop: 1 }}>›</span>
              {item}
            </li>
          ))}
        </ul>
      </Section>

      {/* Confidence limitations */}
      <Section title="Confidence & Limitations">
        <div
          className="rounded-lg p-3 text-[11px] leading-relaxed"
          style={{
            background: "rgba(245,158,11,0.07)",
            border: "1px solid rgba(245,158,11,0.20)",
            color: "#94A3B8",
          }}
        >
          <p className="font-semibold mb-1" style={{ color: "#FCD34D" }}>
            ⚠ {confPct}% confidence — uncertainty sources:
          </p>
          <ul className="space-y-0.5">
            <li>· IMERG data stale (4h delay)</li>
            <li>· Synthetic training data (10 districts)</li>
            <li>· No live PMD/FFD bulletins in demo</li>
            <li>· Operational validation requires official satellite + gauge datasets</li>
          </ul>
        </div>
      </Section>

      {/* Disclaimer */}
      <div
        className="rounded-lg p-3 text-[11px] leading-relaxed"
        role="note"
        aria-label="Official warning disclaimer"
        style={{
          background: "rgba(239,68,68,0.07)",
          border: "1px solid rgba(239,68,68,0.20)",
          color: "#FCA5A5",
        }}
      >
        ⚠ {explanation.disclaimer}
      </div>
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
