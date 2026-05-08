"use client";

import { useState } from "react";
import type { LayerVisibility } from "@/components/map/MapDashboard";

interface Props {
  layers: LayerVisibility;
  onToggle: (key: keyof LayerVisibility) => void;
}

interface LayerDef {
  key: keyof LayerVisibility;
  icon: string;
  label: string;
  source: string;
  color: string;
  available: boolean;
}

const LAYERS: LayerDef[] = [
  { key: "risk",         icon: "🗺",  label: "Risk Zones",      source: "RF Model",  color: "#EF4444", available: true  },
  { key: "boundaries",   icon: "▣",   label: "Boundaries",      source: "HDX",       color: "#94A3B8", available: true  },
  { key: "grid",         icon: "⬡",   label: "Grid Risk",       source: "Turf.js",   color: "#F97316", available: true  },
  { key: "rainfall",     icon: "🌧",  label: "Rain Animation",  source: "IMERG sim", color: "#22D3EE", available: true  },
  { key: "wind",         icon: "💨",  label: "Wind Vectors",    source: "Demo IDW",  color: "#7DD3FC", available: true  },
  { key: "cityLabels",   icon: "🌡",  label: "City Weather",    source: "Demo data", color: "#FCD34D", available: true  },
  { key: "sarReference", icon: "🛰",  label: "SAR Evidence",    source: "Planned",   color: "#8B5CF6", available: false },
];

export function LayerRail({ layers, onToggle }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <aside
      aria-label="Layer controls"
      className="hidden md:flex flex-col shrink-0 overflow-hidden transition-all duration-300"
      style={{
        width: expanded ? 216 : 52,
        background: "#0D1526",
        borderRight: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {/* Expand toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center justify-center transition"
        style={{ height: 44, color: "#4B6280", flexShrink: 0 }}
        aria-label={expanded ? "Collapse layer panel" : "Expand layer panel"}
        title={expanded ? "Collapse" : "Expand layers"}
        onMouseEnter={(e) => (e.currentTarget.style.color = "#22D3EE")}
        onMouseLeave={(e) => (e.currentTarget.style.color = "#4B6280")}
      >
        {expanded ? "◀" : "☰"}
      </button>

      <div
        className="shrink-0 mx-2"
        style={{ height: 1, background: "rgba(255,255,255,0.06)" }}
      />

      {/* Layer buttons */}
      <div className="flex flex-col gap-1 p-1.5 flex-1">
        {expanded && (
          <p
            className="text-[10px] font-semibold uppercase tracking-widest px-2 py-1.5"
            style={{ color: "#4B6280" }}
          >
            Map Layers
          </p>
        )}

        {LAYERS.map(({ key, icon, label, source, color, available }) => {
          const active = layers[key];
          return (
            <button
              key={key}
              onClick={() => available && onToggle(key)}
              disabled={!available}
              aria-pressed={active}
              aria-label={`Toggle ${label} layer`}
              title={!expanded ? label : undefined}
              className="flex items-center rounded-lg transition text-left"
              style={{
                gap: expanded ? 10 : 0,
                padding: expanded ? "8px 10px" : "10px 0",
                justifyContent: expanded ? "flex-start" : "center",
                background: active && available ? "rgba(34,211,238,0.10)" : "transparent",
                border: active && available
                  ? "1px solid rgba(34,211,238,0.25)"
                  : "1px solid transparent",
                opacity: available ? 1 : 0.4,
                cursor: available ? "pointer" : "not-allowed",
              }}
              onMouseEnter={(e) => {
                if (available) e.currentTarget.style.background = "rgba(255,255,255,0.05)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background =
                  active && available ? "rgba(34,211,238,0.10)" : "transparent";
              }}
            >
              {/* Active dot */}
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0 transition"
                style={{
                  background: active && available ? color : "rgba(255,255,255,0.15)",
                  boxShadow: active && available ? `0 0 6px ${color}88` : "none",
                  ...(expanded ? {} : { display: "none" }),
                }}
              />

              <span className="text-base leading-none" style={{ minWidth: 20, textAlign: "center" }}>
                {icon}
              </span>

              {expanded && (
                <div className="flex-1 min-w-0">
                  <div
                    className="text-xs font-medium truncate"
                    style={{ color: active && available ? "#F1F5F9" : "#94A3B8" }}
                  >
                    {label}
                  </div>
                  <div className="text-[10px] truncate" style={{ color: "#4B6280" }}>
                    {source}
                  </div>
                </div>
              )}

              {expanded && !available && (
                <span
                  className="text-[9px] font-semibold px-1 py-0.5 rounded shrink-0"
                  style={{ background: "rgba(139,92,246,0.20)", color: "#A78BFA" }}
                >
                  v2
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom: v2 note */}
      {expanded && (
        <div className="p-2 mt-auto">
          <div
            className="rounded-lg p-2 text-[10px] leading-relaxed"
            style={{
              background: "rgba(139,92,246,0.07)",
              border: "1px solid rgba(139,92,246,0.18)",
              color: "#7C3AED",
            }}
          >
            <span style={{ color: "#A78BFA", fontWeight: 600 }}>v2 planned:</span>
            <br />Live SAR · River discharge · Copernicus EMS
          </div>
        </div>
      )}
    </aside>
  );
}
