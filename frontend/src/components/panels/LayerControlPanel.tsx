"use client";

import type { LayerVisibility } from "@/components/map/MapDashboard";
import { DataSourcesPanel } from "@/components/panels/DataSourcesPanel";

interface Props {
  layers: LayerVisibility;
  onToggle: (key: keyof LayerVisibility) => void;
}

interface LayerDef {
  key: keyof LayerVisibility;
  label: string;
  icon: string;
  phase: string | null; // null = available, otherwise "Phase N"
  color: string;
}

const LAYER_DEFS: LayerDef[] = [
  { key: "risk", label: "Risk Layer", icon: "🟥", phase: null, color: "text-red-400" },
  { key: "boundaries", label: "Boundaries", icon: "⬜", phase: null, color: "text-slate-300" },
  { key: "rainfall", label: "Rainfall", icon: "🌧", phase: "Phase 3", color: "text-cyan-400" },
  { key: "sarReference", label: "Satellite SAR", icon: "🛰", phase: "Phase 3", color: "text-purple-400" },
];

export function LayerControlPanel({ layers, onToggle }: Props) {
  return (
    <aside
      aria-label="Layer controls"
      className="hidden md:flex flex-col w-44 shrink-0 bg-slate-900 border-r border-slate-700 p-3 gap-1"
    >
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Layers</p>

      {LAYER_DEFS.map(({ key, label, icon, phase, color }) => {
        const available = phase === null;
        const active = layers[key];

        return (
          <button
            key={key}
            onClick={() => available && onToggle(key)}
            disabled={!available}
            aria-pressed={active}
            aria-label={`Toggle ${label} layer`}
            title={phase ? `Available in ${phase}` : undefined}
            className={[
              "flex items-center gap-2 px-2 py-2 rounded text-sm text-left transition",
              available
                ? "cursor-pointer hover:bg-slate-800"
                : "cursor-not-allowed opacity-40",
              active && available ? "bg-slate-800 ring-1 ring-slate-600" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {/* Toggle indicator */}
            <span
              className={[
                "w-3 h-3 rounded-sm border flex-shrink-0 transition",
                active && available
                  ? "bg-cyan-500 border-cyan-500"
                  : "bg-transparent border-slate-500",
              ].join(" ")}
            />
            <span className={`${color} text-xs`}>{icon}</span>
            <span className="text-slate-200 flex-1 text-xs leading-tight">{label}</span>
            {phase && (
              <span className="text-slate-600 text-[10px] leading-tight">{phase}</span>
            )}
          </button>
        );
      })}

      <div className="mt-auto">
        <DataSourcesPanel />
      </div>
    </aside>
  );
}
