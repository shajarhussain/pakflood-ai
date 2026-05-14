"use client";

import type { LayerVisibility } from "@/components/map/MapDashboard";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available, isLitePrediction, modelBadgeLabel } from "@/lib/api";

const SOURCES = [
  { id: "IMERG",     dot: "#F59E0B", label: "stale 4h",  pulse: false },
  { id: "CHIRPS",    dot: "#22C55E", label: "fresh",      pulse: true  },
  { id: "GloFAS",    dot: "#22C55E", label: "fresh",      pulse: true  },
  { id: "ReliefWeb", dot: "#22D3EE", label: "live",       pulse: true  },
  { id: "FFD/PMD",   dot: "#8B5CF6", label: "demo",       pulse: false },
  { id: "SAR",       dot: "#6B7280", label: "planned",    pulse: false },
];

const LAYER_LABELS: Partial<Record<keyof LayerVisibility, { label: string; color: string }>> = {
  rainfall:   { label: "Rainfall ON", color: "#22D3EE" },
  grid:       { label: "Grid Risk ON", color: "#F97316" },
  wind:       { label: "Wind ON", color: "#7DD3FC" },
  cityLabels: { label: "Weather ON", color: "#FCD34D" },
};

interface Props {
  activeLayers?: LayerVisibility;
}

export function StatusBar({ activeLayers }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  const lite    = isLitePrediction(modelStatus);
  const modelLabel = modelBadgeLabel(modelStatus);
  const modelLabelColor = v3Ready ? (lite ? "#FCD34D" : "#94A3B8") : "#FCA5A5";

  const activeLayerBadges = activeLayers
    ? (Object.entries(LAYER_LABELS) as [keyof LayerVisibility, { label: string; color: string }][])
        .filter(([key]) => activeLayers[key])
    : [];

  return (
    <div
      className="flex items-center gap-0 px-4 shrink-0 overflow-x-auto"
      style={{
        height: 30,
        background: "#080E1A",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}
    >
      <span
        className="text-[10px] font-semibold uppercase tracking-widest shrink-0 pr-3 mr-1"
        style={{ color: "#4B6280", borderRight: "1px solid rgba(255,255,255,0.07)" }}
      >
        Sources
      </span>

      <div className="flex items-center gap-4 pl-3">
        {SOURCES.map((s) => (
          <div key={s.id} className="flex items-center gap-1.5 shrink-0">
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{
                background: s.dot,
                boxShadow: `0 0 4px ${s.dot}88`,
                animation: s.pulse ? "live-blink 2s ease-in-out infinite" : "none",
              }}
            />
            <span className="text-[10px] font-semibold" style={{ color: "#94A3B8" }}>{s.id}</span>
            <span className="text-[10px]" style={{ color: "#4B6280" }}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Active layer badges */}
      {activeLayerBadges.length > 0 && (
        <div className="flex items-center gap-2 pl-4 ml-2" style={{ borderLeft: "1px solid rgba(255,255,255,0.07)" }}>
          {activeLayerBadges.map(([key, { label, color }]) => (
            <span
              key={key}
              className="text-[9px] font-bold px-1.5 py-0.5 rounded"
              style={{ background: `${color}22`, color, border: `1px solid ${color}44` }}
            >
              {label}
            </span>
          ))}
        </div>
      )}

      <div
        className="ml-auto flex items-center gap-3 pl-3 shrink-0"
        style={{ borderLeft: "1px solid rgba(255,255,255,0.07)" }}
      >
        <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: "#4B6280" }}>
          Model
        </span>
        <span className="text-[10px]" style={{ color: modelLabelColor }}>{modelLabel}</span>
        {lite && (
          <span
            className="text-[10px] uppercase tracking-wider"
            style={{
              color: "#FCD34D", background: "rgba(252,211,77,0.08)",
              border: "1px solid rgba(252,211,77,0.30)",
              borderRadius: 4, padding: "1px 6px",
            }}
          >
            Weak-label public-data prototype
          </span>
        )}
        {v3Ready && modelStatus?.calibration_method && (
          <span className="text-[10px]" style={{ color: "#4B6280" }}>{`calibrated · ${modelStatus.calibration_method}`}</span>
        )}
      </div>
    </div>
  );
}
