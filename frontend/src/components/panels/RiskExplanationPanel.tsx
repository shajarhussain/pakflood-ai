"use client";

import type { RiskExplanation } from "@/lib/types";
import type { MockRiskEntry } from "@/data/mock";
import { RISK_BG, RISK_ICONS, riskColor } from "@/lib/risk-colors";

interface Props {
  district: MockRiskEntry | null;
  explanation: RiskExplanation | null;
  onClose: () => void;
}

export function RiskExplanationPanel({ district, explanation, onClose }: Props) {
  return (
    <aside
      aria-label="Risk explanation panel"
      className="hidden lg:flex flex-col w-80 shrink-0 bg-slate-900 border-l border-slate-700 overflow-y-auto"
    >
      {explanation && district ? (
        <FilledPanel explanation={explanation} district={district} onClose={onClose} />
      ) : (
        <EmptyState />
      )}
    </aside>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center gap-3">
      <div className="text-4xl opacity-30">🗺</div>
      <p className="text-slate-400 text-sm font-medium">Select a district</p>
      <p className="text-slate-600 text-xs leading-relaxed">
        Click any district on the map or use the search bar to view flood risk analysis and AI
        explanation.
      </p>
    </div>
  );
}

function FilledPanel({
  explanation,
  district,
  onClose,
}: {
  explanation: RiskExplanation;
  district: MockRiskEntry;
  onClose: () => void;
}) {
  const {
    risk_level,
    main_causes,
    historical_evidence,
    suggested_actions,
    confidence,
    data_sources,
    disclaimer,
  } = explanation;

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 shrink-0">
        <div>
          <p className="text-white font-bold text-sm">Flood Risk</p>
          <p className="text-slate-400 text-xs">
            {district.name} · {district.province}
          </p>
        </div>
        <button
          onClick={onClose}
          aria-label="Close risk panel"
          className="text-slate-400 hover:text-white transition p-1"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-sm">
        {/* Risk score + confidence */}
        <div
          className={`rounded-lg border p-3 flex items-center gap-3 ${RISK_BG[risk_level]}`}
        >
          <span className="text-2xl" aria-hidden="true">
            {RISK_ICONS[risk_level]}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-slate-400">Risk Level</p>
            <p className="font-bold" style={{ color: riskColor(risk_level) }}>
              {risk_level}
            </p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-slate-400">Score</p>
            <p className="font-bold text-white">{(district.risk_score * 100).toFixed(0)}%</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-xs text-slate-400">Confidence</p>
            <p className="font-medium text-slate-300">{(confidence * 100).toFixed(0)}%</p>
          </div>
        </div>

        <Section title="Main Causes" items={main_causes} bulletColor="text-red-400" />
        <Section title="Historical Evidence" items={historical_evidence} bulletColor="text-yellow-400" />
        <Section title="Suggested Actions" items={suggested_actions} bulletColor="text-cyan-400" />

        {/* Data sources */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
            Official sources
          </p>
          <ul className="space-y-1">
            {data_sources.map((s, i) => (
              <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                <span className="text-slate-600 shrink-0">·</span>
                {s}
              </li>
            ))}
          </ul>
        </div>

        {/* Disclaimer */}
        <div
          role="note"
          aria-label="Official warning disclaimer"
          className="text-xs text-yellow-300/90 border border-yellow-800/60 rounded-lg p-3 leading-relaxed"
        >
          ⚠ {disclaimer}
        </div>
      </div>
    </>
  );
}

function Section({
  title,
  items,
  bulletColor,
}: {
  title: string;
  items: string[];
  bulletColor: string;
}) {
  return (
    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
            <span className={`${bulletColor} shrink-0 mt-0.5`}>›</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
