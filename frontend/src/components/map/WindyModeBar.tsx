"use client";

import type { LayerMode } from "./CleanLayerSwitcher";

interface ModeConfig {
  id: LayerMode;
  icon: string;
  label: string;
  ariaLabel: string;
  color: string;
  badgeText: string;
}

const MODES: ModeConfig[] = [
  { id: "risk",     icon: "⚠",  label: "RISK",    ariaLabel: "Toggle Risk layer",           color: "#FF0040", badgeText: "Grid Risk ON" },
  { id: "rainfall", icon: "🌧",  label: "RAIN",    ariaLabel: "Toggle Rain Animation layer", color: "#00D4FF", badgeText: "Rainfall ON" },
  { id: "wind",     icon: "💨",  label: "WIND",    ariaLabel: "Toggle Wind Vectors layer",   color: "#7DD3FC", badgeText: "Wind ON" },
  { id: "weather",  icon: "🌡",  label: "WEATHER", ariaLabel: "Toggle Weather layer",        color: "#FFE500", badgeText: "Weather ON" },
  { id: "sar",      icon: "🛰",  label: "SAR",     ariaLabel: "Toggle SAR layer",            color: "#9B59FF", badgeText: "SAR ON" },
  { id: "history",  icon: "📅",  label: "HIST",    ariaLabel: "Toggle History layer",        color: "#FF7700", badgeText: "History ON" },
];

interface Props {
  mode: LayerMode;
  onChange: (mode: LayerMode) => void;
}

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)).join(",");
}

export function WindyModeBar({ mode, onChange }: Props) {
  const activeCfg = MODES.find((m) => m.id === mode) ?? MODES[0];

  return (
    <aside
      aria-label="Layer controls"
      style={{
        position: "absolute",
        left: 16,
        bottom: 88,
        zIndex: 600,
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: "4px 6px",
        background: "rgba(10,15,30,0.92)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        border: "1px solid rgba(0,255,209,0.14)",
        borderRadius: 14,
        boxShadow: "0 8px 32px rgba(0,0,0,0.55)",
      }}
    >
      {MODES.map(({ id, icon, label, ariaLabel, color }) => {
        const isActive = mode === id;
        const rgb = hexToRgb(color);
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            aria-label={ariaLabel}
            aria-pressed={isActive}
            style={{
              height: 44,
              padding: "0 10px",
              borderRadius: 10,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 3,
              background: isActive ? `rgba(${rgb},0.12)` : "transparent",
              border: isActive ? `1px solid rgba(${rgb},0.45)` : "1px solid transparent",
              cursor: "pointer",
              transition: "all 0.14s ease",
              boxShadow: isActive ? `0 0 14px rgba(${rgb},0.22)` : "none",
              minWidth: 48,
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.background = "rgba(255,255,255,0.06)";
                e.currentTarget.style.border = "1px solid rgba(255,255,255,0.08)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isActive ? `rgba(${rgb},0.12)` : "transparent";
              e.currentTarget.style.border = isActive ? `1px solid rgba(${rgb},0.45)` : "1px solid transparent";
            }}
          >
            <span style={{ fontSize: 16, lineHeight: 1 }}>{icon}</span>
            <span
              style={{
                fontSize: 8,
                fontWeight: 700,
                color: isActive ? color : "#3B6070",
                letterSpacing: "0.12em",
                fontFamily: "var(--font-geist-mono, monospace)",
              }}
            >
              {label}
            </span>
          </button>
        );
      })}

      {/* Divider */}
      <div style={{ width: 1, height: 28, background: "rgba(0,255,209,0.12)", margin: "0 4px", flexShrink: 0 }} />

      {/* Active mode badge — inside pill, right side */}
      <div
        aria-label="Active layers status"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          paddingLeft: 4,
          paddingRight: 4,
          color: activeCfg.color,
          fontSize: 10,
          fontWeight: 700,
          fontFamily: "var(--font-geist-mono, monospace)",
          letterSpacing: "0.08em",
          whiteSpace: "nowrap",
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: activeCfg.color,
            boxShadow: `0 0 6px ${activeCfg.color}`,
            flexShrink: 0,
          }}
        />
        {activeCfg.badgeText}
      </div>
    </aside>
  );
}
