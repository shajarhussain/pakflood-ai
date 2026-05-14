"use client";

import type { MockRiskEntry } from "@/data/mock";
import { useModelStatus } from "@/lib/useModelStatus";
import { isV3Available } from "@/lib/api";

interface Props {
  riskData: Map<string, MockRiskEntry>;
}

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono, monospace)" };

export function RiskIndexBadge({ riskData }: Props) {
  const modelStatus = useModelStatus();
  const v3Ready = isV3Available(modelStatus);

  // v3 strict: do not surface mock severity counts as if they were real v3 output.
  if (!v3Ready) {
    return (
      <div
        data-testid="risk-index-badge-unavailable"
        style={{
          position: "absolute",
          left: 16,
          bottom: 156,
          zIndex: 600,
          background: "rgba(10,15,30,0.92)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          border: "1px solid rgba(252,165,165,0.30)",
          borderRadius: 12,
          padding: "9px 12px",
          width: 222,
          boxShadow: "0 8px 24px rgba(0,0,0,0.55)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6, ...mono }}>
          <span
            style={{ width: 7, height: 7, borderRadius: "50%", background: "#64748B", flexShrink: 0 }}
          />
          <span style={{ fontSize: 9, fontWeight: 700, color: "#94A3B8", letterSpacing: "0.14em" }}>
            PAKISTAN RISK INDEX
          </span>
        </div>
        <div style={{ fontSize: 10, color: "#FCA5A5", lineHeight: 1.4, ...mono }}>
          Demo risk layer disabled in real_prediction mode
        </div>
      </div>
    );
  }

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

      <div
        style={{
          width: "100%", height: 3, background: "rgba(255,255,255,0.07)",
          borderRadius: 2, overflow: "hidden", marginBottom: 6,
        }}
      >
        <div
          style={{
            width: `${Math.max(progressPct, 8)}%`, height: "100%",
            background: `linear-gradient(90deg, ${levelColor}88, ${levelColor})`,
            borderRadius: 2, boxShadow: `0 0 6px ${levelColor}55`,
          }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", ...mono }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: levelColor }}>
          {worstLevel.toUpperCase()}
        </span>
        <span style={{ fontSize: 9, color: "#3B6070", display: "flex", gap: 5 }}>
          {severeCount > 0 && <span style={{ color: "#FF0040" }}>{severeCount} SEV</span>}
          {highCount > 0 && <span style={{ color: "#FF7700" }}>{highCount} HIGH</span>}
          {alertCount === 0 && <span style={{ color: "#00FF88" }}>NOMINAL</span>}
        </span>
      </div>
    </div>
  );
}
