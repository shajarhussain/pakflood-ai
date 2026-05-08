"use client";

import type { MockRiskEntry } from "@/data/mock";

interface Props {
  riskData: Map<string, MockRiskEntry>;
}

export function RiskIndexBadge({ riskData }: Props) {
  const entries     = Array.from(riskData.values());
  const severeCount = entries.filter((e) => e.risk_level === "Severe").length;
  const highCount   = entries.filter((e) => e.risk_level === "High").length;
  const total       = entries.length;
  const alertCount  = severeCount + highCount;
  const progressPct = Math.round((alertCount / Math.max(total, 1)) * 100);

  const worstLevel  = severeCount > 0 ? "Severe" : highCount > 0 ? "High" : "Moderate";
  const levelColor  =
    worstLevel === "Severe" ? "#FF0040" :
    worstLevel === "High"   ? "#FF7700" : "#FFE500";

  const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono, monospace)" };

  return (
    <div
      style={{
        position: "absolute",
        left: 16,
        bottom: 156,
        zIndex: 600,
        background: "rgba(10,15,30,0.92)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 12,
        padding: "9px 12px",
        width: 202,
        boxShadow: "0 8px 24px rgba(0,0,0,0.55)",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 7, ...mono }}>
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: levelColor,
            boxShadow: `0 0 7px ${levelColor}`,
            flexShrink: 0,
            animation: worstLevel === "Severe" ? "ops-active-blink 1s ease-in-out infinite" : undefined,
          }}
        />
        <span style={{ fontSize: 9, fontWeight: 700, color: "#00C8AA", letterSpacing: "0.14em" }}>
          PAKISTAN RISK INDEX
        </span>
      </div>

      {/* Progress bar */}
      <div
        style={{
          width: "100%",
          height: 3,
          background: "rgba(255,255,255,0.07)",
          borderRadius: 2,
          overflow: "hidden",
          marginBottom: 6,
        }}
      >
        <div
          style={{
            width: `${Math.max(progressPct, 8)}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${levelColor}88, ${levelColor})`,
            borderRadius: 2,
            boxShadow: `0 0 6px ${levelColor}55`,
          }}
        />
      </div>

      {/* Level + counts */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", ...mono }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: levelColor }}>
          {worstLevel.toUpperCase()}
        </span>
        <span style={{ fontSize: 9, color: "#3B6070", display: "flex", gap: 5 }}>
          {severeCount > 0 && (
            <span style={{ color: "#FF0040" }}>{severeCount} SEV</span>
          )}
          {highCount > 0 && (
            <span style={{ color: "#FF7700" }}>{highCount} HIGH</span>
          )}
          {alertCount === 0 && (
            <span style={{ color: "#00FF88" }}>NOMINAL</span>
          )}
        </span>
      </div>
    </div>
  );
}
