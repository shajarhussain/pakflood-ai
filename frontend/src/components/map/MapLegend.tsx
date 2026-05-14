"use client";

import { RISK_COLORS, RISK_ICONS } from "@/lib/risk-colors";
import type { RiskLevel } from "@/lib/types";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available, MODEL_UNAVAILABLE_MESSAGE } from "@/lib/api";

const DISTRICT_LEVELS: { level: RiskLevel; label: string; range: string }[] = [
  { level: "Severe",   label: "Severe",   range: ">75%" },
  { level: "High",     label: "High",     range: "55–75%" },
  { level: "Moderate", label: "Moderate", range: "30–55%" },
  { level: "Low",      label: "Low",      range: "<30%" },
];

const GRID_ZONES: { color: string; label: string; desc: string }[] = [
  { color: "#EF4444", label: "Severe",   desc: "Sindh floodplain" },
  { color: "#F97316", label: "High",     desc: "Punjab / KP" },
  { color: "#F59E0B", label: "Moderate", desc: "Transitional" },
  { color: "#22C55E", label: "Low",      desc: "Highland / arid" },
  { color: "#475569", label: "Minimal",  desc: "Semi-arid" },
];

interface Props {
  showGrid?: boolean;
  panelOpen?: boolean;
}

export function MapLegend({ showGrid = false, panelOpen = false }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);
  const footer = v3Ready ? "v3 flood probability (calibrated)" : MODEL_UNAVAILABLE_MESSAGE;
  return (
    <div
      aria-label="Flood risk level legend"
      style={{
        position: "absolute",
        bottom: 88,
        right: panelOpen ? 316 : 16,
        zIndex: 400,
        pointerEvents: "none",
        background: "rgba(13,21,38,0.88)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        border: "1px solid rgba(255,255,255,0.09)",
        borderRadius: 10,
        padding: "10px 14px",
        minWidth: 158,
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        transition: "right 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >
      {/* District risk levels */}
      <p
        className="text-[9px] font-bold uppercase tracking-[0.14em] mb-2"
        style={{ color: "#4B6280" }}
      >
        District Risk
      </p>
      <ul className="space-y-1.5">
        {DISTRICT_LEVELS.map(({ level, label, range }) => (
          <li key={level} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="w-3 h-3 rounded-sm shrink-0"
              style={{
                backgroundColor: RISK_COLORS[level],
                boxShadow: `0 0 6px ${RISK_COLORS[level]}88`,
              }}
            />
            <span
              aria-hidden="true"
              className="text-[11px] font-bold shrink-0 w-3 text-center"
              style={{ color: RISK_COLORS[level] }}
            >
              {RISK_ICONS[level]}
            </span>
            <span className="text-[11px] font-medium" style={{ color: "#CBD5E1" }}>
              {label}
            </span>
            <span className="text-[10px] ml-auto" style={{ color: "#4B6280" }}>
              {range}
            </span>
          </li>
        ))}
      </ul>

      {/* Grid zone legend — only when grid layer is on */}
      {showGrid && (
        <>
          <div
            className="my-2.5"
            style={{ height: 1, background: "rgba(255,255,255,0.06)" }}
          />
          <p
            className="text-[9px] font-bold uppercase tracking-[0.14em] mb-2"
            style={{ color: "#4B6280" }}
          >
            Grid Zones
          </p>
          <ul className="space-y-1.5">
            {GRID_ZONES.map(({ color, label, desc }) => (
              <li key={label} className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className="w-3 h-3 shrink-0"
                  style={{
                    backgroundColor: color,
                    opacity: 0.65,
                    borderRadius: 2,
                    boxShadow: `0 0 4px ${color}66`,
                  }}
                />
                <span className="text-[11px] font-medium" style={{ color: "#CBD5E1" }}>
                  {label}
                </span>
                <span className="text-[9px] ml-auto truncate" style={{ color: "#4B6280", maxWidth: 60 }}>
                  {desc}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      <div
        className="mt-2.5 pt-2 text-[9px]"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)", color: v3Ready ? "#4B6280" : "#FCA5A5" }}
      >
        {footer}
      </div>
    </div>
  );
}
