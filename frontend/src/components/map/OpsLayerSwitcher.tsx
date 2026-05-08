"use client";

export type { LayerMode } from "./CleanLayerSwitcher";
import type { LayerMode } from "./CleanLayerSwitcher";

interface ModeConfig {
  id: LayerMode;
  icon: string;
  label: string;
  ariaLabel: string;
  color: string;
}

const MODES: ModeConfig[] = [
  { id: "risk",     icon: "⚠",  label: "Risk",    ariaLabel: "Toggle Risk layer",           color: "#FF2D55" },
  { id: "rainfall", icon: "🌧",  label: "Rain",    ariaLabel: "Toggle Rain Animation layer", color: "#00FFD1" },
  { id: "wind",     icon: "💨",  label: "Wind",    ariaLabel: "Toggle Wind Vectors layer",   color: "#7DD3FC" },
  { id: "weather",  icon: "🌡",  label: "Weather", ariaLabel: "Toggle Weather layer",        color: "#FFD60A" },
  { id: "sar",      icon: "🛰",  label: "SAR",     ariaLabel: "Toggle SAR layer",            color: "#9B59FF" },
  { id: "history",  icon: "📅",  label: "History", ariaLabel: "Toggle History layer",        color: "#FF6B00" },
];

interface Props {
  mode: LayerMode;
  onChange: (mode: LayerMode) => void;
}

export function OpsLayerSwitcher({ mode, onChange }: Props) {
  return (
    <aside
      aria-label="Layer controls"
      style={{
        position: "absolute",
        left: 12,
        top: "50%",
        transform: "translateY(-50%)",
        zIndex: 600,
        display: "flex",
        flexDirection: "column",
        gap: 2,
        padding: "10px 6px 8px",
        background: "rgba(5,12,20,0.92)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        border: "1px solid rgba(0,255,209,0.12)",
        borderRadius: 16,
        boxShadow: "0 8px 32px rgba(0,0,0,0.55), inset 0 1px 0 rgba(0,255,209,0.06)",
      }}
    >
      {/* Panel header label */}
      <div
        style={{
          fontSize: 8,
          fontWeight: 700,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: "#00C8AA",
          textAlign: "center",
          paddingBottom: 6,
          fontFamily: "var(--font-geist-mono, monospace)",
          borderBottom: "1px solid rgba(0,255,209,0.10)",
          marginBottom: 2,
        }}
      >
        LAYERS
      </div>

      {MODES.map(({ id, icon, label, ariaLabel, color }) => {
        const isActive = mode === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            aria-label={ariaLabel}
            aria-pressed={isActive}
            title={label}
            style={{
              width: 68,
              height: 56,
              borderRadius: 12,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 3,
              background: isActive ? `rgba(${hexToRgb(color)},0.08)` : "transparent",
              border: isActive
                ? `1px solid rgba(${hexToRgb(color)},0.35)`
                : "1px solid transparent",
              cursor: "pointer",
              transition: "all 0.15s ease",
              boxShadow: isActive ? `0 0 14px rgba(${hexToRgb(color)},0.18)` : "none",
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.background = "rgba(0,255,209,0.05)";
                e.currentTarget.style.border = "1px solid rgba(0,255,209,0.12)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isActive
                ? `rgba(${hexToRgb(color)},0.08)`
                : "transparent";
              e.currentTarget.style.border = isActive
                ? `1px solid rgba(${hexToRgb(color)},0.35)`
                : "1px solid transparent";
            }}
          >
            <span style={{ fontSize: 20, lineHeight: 1 }}>{icon}</span>
            <span
              style={{
                fontSize: 9,
                fontWeight: 700,
                color: isActive ? color : "#3B6070",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                fontFamily: "var(--font-geist-mono, monospace)",
              }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </aside>
  );
}

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `${r},${g},${b}`;
}
