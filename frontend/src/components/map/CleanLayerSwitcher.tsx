"use client";

export type LayerMode = "risk" | "rainfall" | "wind" | "weather" | "sar" | "history";

interface ModeConfig {
  id: LayerMode;
  icon: string;
  label: string;
  ariaLabel: string;
  color: string;
}

const MODES: ModeConfig[] = [
  { id: "risk",     icon: "⚠",  label: "Risk",    ariaLabel: "Toggle Risk layer",           color: "#EF4444" },
  { id: "rainfall", icon: "🌧",  label: "Rain",    ariaLabel: "Toggle Rain Animation layer", color: "#22D3EE" },
  { id: "wind",     icon: "💨",  label: "Wind",    ariaLabel: "Toggle Wind Vectors layer",   color: "#7DD3FC" },
  { id: "weather",  icon: "🌡",  label: "Weather", ariaLabel: "Toggle Weather layer",        color: "#FCD34D" },
  { id: "sar",      icon: "🛰",  label: "SAR",     ariaLabel: "Toggle SAR layer",            color: "#A78BFA" },
  { id: "history",  icon: "📅",  label: "History", ariaLabel: "Toggle History layer",        color: "#F59E0B" },
];

interface Props {
  mode: LayerMode;
  onChange: (mode: LayerMode) => void;
}

export function CleanLayerSwitcher({ mode, onChange }: Props) {
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
        gap: 3,
        padding: "8px 5px",
        background: "rgba(13, 19, 35, 0.90)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        border: "1px solid rgba(148, 163, 184, 0.11)",
        borderRadius: 14,
        boxShadow: "0 8px 32px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)",
      }}
    >
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
              width: 42,
              height: 42,
              borderRadius: 10,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 2,
              background: isActive ? `${color}18` : "transparent",
              border: isActive ? `1px solid ${color}50` : "1px solid transparent",
              cursor: "pointer",
              transition: "all 0.15s ease",
              boxShadow: isActive ? `0 0 12px ${color}22` : "none",
            }}
            onMouseEnter={(e) => {
              if (!isActive) e.currentTarget.style.background = "rgba(255,255,255,0.05)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isActive ? `${color}18` : "transparent";
            }}
          >
            <span style={{ fontSize: 17, lineHeight: 1 }}>{icon}</span>
            <span
              style={{
                fontSize: 8,
                fontWeight: 700,
                color: isActive ? color : "#475569",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
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
