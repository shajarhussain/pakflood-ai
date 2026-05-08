"use client";

import { useState } from "react";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";

interface Props {
  district: MockRiskEntry;
  explanation: RiskExplanation;
}

const CITIZEN_CHECKLIST = [
  "Store 72-hour water supply in sealed containers",
  "Charge all devices, power banks, and emergency radios",
  "Prepare emergency kit: ID documents, medicine, cash",
  "Know the nearest elevated evacuation shelter",
  "Avoid travel on low-lying roads and bridges",
  "Follow NDMA, PDMA, and local authority alerts in real-time",
  "Do not wait for floodwater to enter home before evacuating",
];

const AUTHORITY_CHECKLIST = [
  "Monitor river gauge readings at nearest barrage (FFD / IRSA)",
  "Pre-position rescue boats at identified high-risk wards",
  "Review 2010 / 2022 event evacuation route maps",
  "Alert PDMA for resource pre-staging and logistics coordination",
  "Verify hospital backup power is operational",
  "Coordinate with NDMA on national early warning timeline",
  "Activate emergency operations center if risk reaches SEVERE",
];

const MONITORING_CHECKLIST = [
  "GloFAS discharge: review next 24h forecast update",
  "PMD rainfall bulletin: next advisory expected at 06:00 / 18:00",
  "FFD river level alert threshold — watch for High / Severe",
  "ReliefWeb: incoming Pakistan situation reports",
  "NDMA daily situation report",
  "Local community reporting via 1129 NDMA hotline",
];

export function ResponsePlan({ district, explanation }: Props) {
  const [citizenChecked,   setCitizenChecked]   = useState<Set<number>>(new Set());
  const [authorityChecked, setAuthorityChecked] = useState<Set<number>>(new Set());
  const [monitorChecked,   setMonitorChecked]   = useState<Set<number>>(new Set());

  const totalItems = CITIZEN_CHECKLIST.length + AUTHORITY_CHECKLIST.length + MONITORING_CHECKLIST.length;
  const totalChecked = citizenChecked.size + authorityChecked.size + monitorChecked.size;
  const readinessPct = Math.round((totalChecked / totalItems) * 100);

  const responsePriority =
    explanation.risk_level === "Severe"   ? 91 :
    explanation.risk_level === "High"     ? 72 :
    explanation.risk_level === "Moderate" ? 45 : 20;

  function toggle(set: Set<number>, idx: number, setter: (s: Set<number>) => void) {
    const next = new Set(set);
    if (next.has(idx)) { next.delete(idx); } else { next.add(idx); }
    setter(next);
  }

  const advisory = `[EDUCATIONAL DRAFT — NOT OFFICIAL]

FLOOD INTELLIGENCE ALERT
${district.name.toUpperCase()} DISTRICT, ${district.province.toUpperCase()}
PakFlood AI Command Center (Educational Prototype)

Risk: ${explanation.risk_level.toUpperCase()} | Score: ${(district.risk_score * 100).toFixed(0)}% | Confidence: ${(explanation.confidence * 100).toFixed(0)}%

Key factors: ${district.top_factors.join(", ")}

Actions: ${explanation.suggested_actions.slice(0, 3).join(" · ")}

⚠ Follow PMD · FFD · NDMA · PDMA for official instructions.`;

  return (
    <div className="flex flex-col gap-4 animate-fade-up">
      {/* Response priority */}
      <div
        className="rounded-xl p-3.5"
        style={{ background: "#111E35", border: "1px solid rgba(255,255,255,0.08)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: "#4B6280" }}>
            Response Priority Score
          </p>
          <span
            className="text-lg font-black"
            style={{
              color: responsePriority >= 80 ? "#EF4444" : responsePriority >= 60 ? "#F97316" : "#F59E0B",
            }}
          >
            {responsePriority} / 100
          </span>
        </div>
        <div className="rounded-full overflow-hidden" style={{ height: 6, background: "rgba(255,255,255,0.08)" }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${responsePriority}%`,
              background: responsePriority >= 80
                ? "linear-gradient(90deg, #F97316, #EF4444)"
                : "linear-gradient(90deg, #F59E0B, #F97316)",
              boxShadow: `0 0 8px rgba(239,68,68,0.5)`,
            }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <p className="text-[10px]" style={{ color: "#4B6280" }}>
            Readiness: {readinessPct}% ({totalChecked}/{totalItems} actions)
          </p>
          <p className="text-[10px]" style={{ color: "#4B6280" }}>
            {explanation.risk_level} risk
          </p>
        </div>
      </div>

      {/* Citizen checklist */}
      <Checklist
        title="Citizen Preparedness"
        icon="🏃"
        color="#22D3EE"
        items={CITIZEN_CHECKLIST}
        checked={citizenChecked}
        onToggle={(i) => toggle(citizenChecked, i, setCitizenChecked)}
      />

      {/* Authority checklist */}
      <Checklist
        title="Local Authority Actions"
        icon="🏛"
        color="#3B82F6"
        items={AUTHORITY_CHECKLIST}
        checked={authorityChecked}
        onToggle={(i) => toggle(authorityChecked, i, setAuthorityChecked)}
      />

      {/* Monitoring checklist */}
      <Checklist
        title="Monitoring Priority"
        icon="📡"
        color="#F59E0B"
        items={MONITORING_CHECKLIST}
        checked={monitorChecked}
        onToggle={(i) => toggle(monitorChecked, i, setMonitorChecked)}
      />

      {/* Vulnerable populations */}
      <div>
        <p
          className="text-[9px] font-bold uppercase tracking-[0.12em] mb-2 pb-1.5"
          style={{ color: "#4B6280", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        >
          Vulnerable Population Priority
        </p>
        <div
          className="rounded-lg p-3 text-[11px] leading-relaxed"
          style={{ background: "rgba(249,115,22,0.07)", border: "1px solid rgba(249,115,22,0.18)", color: "#CBD5E1" }}
        >
          <ul className="space-y-1">
            <li>● Rural communities near Indus / river banks</li>
            <li>● Agricultural workers — low mobility in flood season</li>
            <li>● Informal settlements at elevation &lt;10m above river</li>
            <li>● Elderly, disabled, and young children requiring assistance</li>
          </ul>
          <p className="mt-2 text-[10px]" style={{ color: "#4B6280" }}>
            Source: historical 2010 / 2022 impact patterns (seed data)
          </p>
        </div>
      </div>

      {/* Draft advisory */}
      <div>
        <p
          className="text-[9px] font-bold uppercase tracking-[0.12em] mb-2 pb-1.5"
          style={{ color: "#4B6280", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
        >
          Draft Advisory Preview
        </p>
        <div
          className="rounded-lg p-3 text-[10px] leading-relaxed font-mono whitespace-pre-wrap"
          style={{
            background: "#080E1A",
            border: "1px solid rgba(255,255,255,0.10)",
            color: "#94A3B8",
            maxHeight: 200,
            overflowY: "auto",
          }}
        >
          {advisory}
        </div>
        <button
          onClick={() => navigator.clipboard?.writeText(advisory)}
          className="mt-1.5 text-[10px] px-2 py-1 rounded transition"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#64748B",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#94A3B8")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "#64748B")}
        >
          Copy draft
        </button>
      </div>
    </div>
  );
}

function Checklist({
  title, icon, color, items, checked, onToggle,
}: {
  title: string; icon: string; color: string;
  items: string[]; checked: Set<number>; onToggle: (i: number) => void;
}) {
  return (
    <div>
      <p
        className="text-[9px] font-bold uppercase tracking-[0.12em] mb-2 pb-1.5 flex items-center gap-1.5"
        style={{ color: "#4B6280", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <span>{icon}</span>{title}
        <span className="ml-auto font-normal" style={{ color }}>
          {checked.size}/{items.length}
        </span>
      </p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i}>
            <button
              onClick={() => onToggle(i)}
              className="flex items-start gap-2 w-full text-left"
            >
              <span
                className="w-4 h-4 rounded flex items-center justify-center shrink-0 mt-0.5 transition"
                style={{
                  background: checked.has(i) ? `${color}22` : "rgba(255,255,255,0.05)",
                  border: checked.has(i) ? `1px solid ${color}66` : "1px solid rgba(255,255,255,0.12)",
                }}
              >
                {checked.has(i) && (
                  <span style={{ color, fontSize: 9, fontWeight: 700 }}>✓</span>
                )}
              </span>
              <span
                className="text-[11px] leading-snug"
                style={{ color: checked.has(i) ? "#4B6280" : "#CBD5E1", textDecoration: checked.has(i) ? "line-through" : "none" }}
              >
                {item}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
