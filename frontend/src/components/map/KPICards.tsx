"use client";

import type { MockRiskEntry } from "@/data/mock";

interface Props {
  riskData: Map<string, MockRiskEntry>;
  selectedDistrict: MockRiskEntry | null;
}

export function KPICards({ riskData, selectedDistrict }: Props) {
  const entries = Array.from(riskData.values());
  const severeCount = entries.filter((e) => e.risk_level === "Severe").length;
  const highCount   = entries.filter((e) => e.risk_level === "High").length;
  const freshSources = 4;
  const totalSources = 6;

  return (
    <div
      className="absolute bottom-6 left-3 z-[400] flex flex-col gap-2 pointer-events-none"
      aria-hidden="true"
    >
      <KPI
        label="Districts Monitored"
        value={String(entries.length)}
        sub="MVP dataset"
        accent="#22D3EE"
      />
      <KPI
        label="Severe Risk Zones"
        value={severeCount > 0 ? String(severeCount) : "0"}
        sub={severeCount > 0 ? "active ● pulsing" : "none active"}
        accent="#EF4444"
        pulse={severeCount > 0}
      />
      <KPI
        label="High Risk Zones"
        value={String(highCount)}
        sub="elevated alert"
        accent="#F97316"
      />
      <KPI
        label="Source Health"
        value={`${freshSources}/${totalSources}`}
        sub="sources fresh"
        accent="#22C55E"
        dots={Array.from({ length: totalSources }, (_, i) =>
          i < freshSources ? "#22C55E" : "#F59E0B"
        )}
      />
      {selectedDistrict && (
        <KPI
          label={selectedDistrict.name}
          value={(selectedDistrict.risk_score * 100).toFixed(0) + "%"}
          sub={`${selectedDistrict.risk_level} · ${(selectedDistrict.confidence * 100).toFixed(0)}% conf`}
          accent={
            selectedDistrict.risk_level === "Severe" ? "#EF4444"
            : selectedDistrict.risk_level === "High"   ? "#F97316"
            : selectedDistrict.risk_level === "Moderate" ? "#F59E0B"
            : "#22C55E"
          }
        />
      )}
    </div>
  );
}

function KPI({
  label,
  value,
  sub,
  accent,
  pulse,
  dots,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
  pulse?: boolean;
  dots?: string[];
}) {
  return (
    <div
      className="rounded-xl px-3 py-2.5"
      style={{
        background: "rgba(13,21,38,0.88)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        border: `1px solid ${accent}33`,
        borderLeft: `3px solid ${accent}`,
        minWidth: 148,
        boxShadow: `0 4px 16px rgba(0,0,0,0.4), 0 0 12px ${accent}18`,
      }}
    >
      <p
        className="text-[9px] font-semibold uppercase tracking-widest mb-0.5"
        style={{ color: accent }}
      >
        {label}
      </p>
      <div className="flex items-baseline gap-2">
        <span
          className="text-xl font-bold leading-none"
          style={{
            color: "#F1F5F9",
            animation: pulse ? "severe-pulse 2s ease-in-out infinite" : "none",
          }}
        >
          {value}
        </span>
      </div>
      <p className="text-[10px] mt-0.5" style={{ color: "#64748B" }}>
        {sub}
      </p>
      {dots && (
        <div className="flex gap-0.5 mt-1.5">
          {dots.map((c, i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-sm"
              style={{ background: c, boxShadow: `0 0 4px ${c}66` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
