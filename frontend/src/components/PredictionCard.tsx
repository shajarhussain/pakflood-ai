"use client";
import type { PredictionResponse } from "@/lib/types";
import { RISK_COLORS, RISK_BG, RISK_ICONS } from "@/lib/risk-colors";

interface Props {
  prediction: PredictionResponse;
  location: { lat: number; lng: number };
  onDismiss: () => void;
}

export default function PredictionCard({ prediction, location, onDismiss }: Props) {
  const { flood_probability, risk_level, confidence, top_factors, disclaimer } = prediction;
  // "Unknown" is the fallback when the model artifact isn't loaded
  const safeLevel = (risk_level === "Unknown" ? "Low" : risk_level) as keyof typeof RISK_COLORS;
  const color = RISK_COLORS[safeLevel];
  const bg = RISK_BG[safeLevel];
  const icon = risk_level === "Unknown" ? "?" : RISK_ICONS[safeLevel];
  const pct = Math.round(flood_probability * 100);
  const confPct = Math.round(confidence * 100);

  return (
    <div className="animate-fade-up w-full max-w-sm bg-slate-900/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-sm">
      {/* Header */}
      <div className={`px-5 py-4 border-b border-white/10 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold border ${bg}`}
            style={{ color }}
          >
            <span>{icon}</span>
            {risk_level === "Unknown" ? "Model Unavailable" : `${risk_level} Risk`}
          </span>
          <span className="text-slate-400 text-xs">
            {location.lat.toFixed(3)}°N, {location.lng.toFixed(3)}°E
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>

      {/* Probability */}
      <div className="px-5 py-4 border-b border-white/10">
        <div className="flex items-end justify-between mb-2">
          <span className="text-slate-400 text-xs uppercase tracking-wider">Flood Probability</span>
          <span className="text-2xl font-bold" style={{ color }}>{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
      </div>

      {/* Confidence */}
      <div className="px-5 py-3 border-b border-white/10">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-slate-400 text-xs uppercase tracking-wider">Model Confidence</span>
          <span className="text-slate-300 text-sm font-semibold">{confPct}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-slate-400 transition-all duration-700"
            style={{ width: `${confPct}%` }}
          />
        </div>
      </div>

      {/* Top factors */}
      {top_factors && top_factors.length > 0 && (
        <div className="px-5 py-4 border-b border-white/10">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-3">Key Factors</p>
          <ul className="space-y-2.5">
            {top_factors.slice(0, 3).map((f, i) => {
              const imp = typeof f.importance === "number" ? f.importance : 0;
              const impPct = Math.round(Math.min(imp * 100, 100));
              return (
                <li key={i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-300 text-xs">{f.name}</span>
                    <span className="text-slate-500 text-xs">{impPct}%</span>
                  </div>
                  <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${impPct}%`, background: color }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="px-5 py-3">
        <p className="text-slate-500 text-[10px] leading-relaxed">{disclaimer}</p>
      </div>
    </div>
  );
}
