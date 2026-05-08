"use client";

import type { MockFloodEvent } from "@/data/mock";

interface Props {
  events: MockFloodEvent[];
  activeYear: number | null;
  onYearSelect: (year: number) => void;
}

const EVENT_META: Record<number, { color: string; severity: string; icon: string }> = {
  2010: { color: "#EF4444", severity: "Catastrophic", icon: "🔴" },
  2011: { color: "#F97316", severity: "Severe",       icon: "🟠" },
  2014: { color: "#F59E0B", severity: "Significant",  icon: "🟡" },
  2022: { color: "#EF4444", severity: "Catastrophic", icon: "🔴" },
};

function humanize(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export function FloodTimeline({ events, activeYear, onYearSelect }: Props) {
  const active = events.find((e) => e.year === activeYear);

  return (
    <div
      aria-label="Flood event timeline"
      className="shrink-0 flex flex-col"
      style={{
        background: "#0A0F1E",
        borderTop: "1px solid rgba(0,255,209,0.08)",
        height: active ? 100 : 60,
        transition: "height 0.25s ease",
      }}
    >
      {/* Timeline header + events */}
      <div className="flex items-stretch" style={{ height: 60 }}>
        {/* Label */}
        <div
          className="hidden sm:flex flex-col justify-center px-4 shrink-0"
          style={{ borderRight: "1px solid rgba(255,255,255,0.07)", minWidth: 130 }}
        >
          <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "#4B6280" }}>
            Historical
          </p>
          <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "#4B6280" }}>
            Flood Atlas
          </p>
          <p className="text-[10px] mt-1" style={{ color: "#00FFD1" }}>
            {events.length} events
          </p>
        </div>

        {/* Timeline connector line */}
        <div className="flex items-center flex-1 px-4 gap-0 relative overflow-x-auto">
          {/* Horizontal line */}
          <div
            className="absolute left-4 right-4"
            style={{ height: 1, top: "50%", background: "rgba(255,255,255,0.07)", zIndex: 0 }}
          />

          <div className="flex items-center gap-8 relative z-10">
            {events.map((ev) => {
              const meta = EVENT_META[ev.year] ?? { color: "#6B7280", severity: "Event", icon: "⚪" };
              const isActive = activeYear === ev.year;

              return (
                <button
                  key={ev.id}
                  onClick={() => onYearSelect(ev.year)}
                  aria-pressed={isActive}
                  aria-label={`Select ${ev.year} flood event`}
                  className="flex flex-col items-center gap-1.5 shrink-0 transition group"
                >
                  {/* Year label */}
                  <span
                    className="text-[9px] font-semibold uppercase tracking-widest transition"
                    style={{ color: isActive ? meta.color : "#4B6280" }}
                  >
                    {ev.peak_month ?? ev.year}
                  </span>

                  {/* Node */}
                  <div
                    className="relative flex items-center justify-center transition"
                    style={{
                      width: isActive ? 34 : 26,
                      height: isActive ? 34 : 26,
                      borderRadius: "50%",
                      background: isActive ? `${meta.color}18` : "rgba(255,255,255,0.04)",
                      border: isActive ? `2px solid ${meta.color}` : "2px solid rgba(255,255,255,0.10)",
                      boxShadow: isActive ? `0 0 14px ${meta.color}50` : "none",
                    }}
                  >
                    <span className="text-sm">{meta.icon}</span>
                    {isActive && (
                      <span
                        className="absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center text-[7px]"
                        style={{ background: meta.color, color: "white", fontWeight: 700 }}
                      >
                        ✓
                      </span>
                    )}
                  </div>

                  {/* Year */}
                  <span
                    className="text-sm font-black transition"
                    style={{ color: isActive ? "#F1F5F9" : "#64748B" }}
                  >
                    {ev.year}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Clear + stats */}
        <div
          className="hidden md:flex flex-col justify-center px-4 shrink-0 gap-1"
          style={{ borderLeft: "1px solid rgba(255,255,255,0.07)" }}
        >
          {activeYear && (
            <button
              onClick={() => onYearSelect(activeYear)}
              className="text-[10px] px-2 py-1 rounded transition"
              aria-label="Clear year filter"
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "#64748B",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#94A3B8")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#64748B")}
            >
              ✕ Clear
            </button>
          )}
          <p className="text-[9px]" style={{ color: "#4B6280" }}>
            Click event to<br />highlight map
          </p>
        </div>
      </div>

      {/* Active event detail strip */}
      {active && (() => {
        const meta = EVENT_META[active.year] ?? { color: "#6B7280", severity: "Event", icon: "⚪" };
        return (
          <div
            className="flex items-center gap-4 px-4 overflow-x-auto"
            style={{
              height: 40,
              background: `${meta.color}09`,
              borderTop: `1px solid ${meta.color}22`,
              flexShrink: 0,
            }}
          >
            <span
              className="text-xs font-bold shrink-0"
              style={{ color: meta.color }}
            >
              {active.year}
            </span>
            <span className="text-xs font-semibold shrink-0" style={{ color: "#F1F5F9" }}>
              {active.title}
            </span>
            <span className="text-[11px] shrink-0" style={{ color: "#94A3B8" }}>
              {humanize(active.estimated_affected)} affected
            </span>
            {active.damage_usd_billion && (
              <span className="text-[11px] font-semibold shrink-0" style={{ color: "#FCA5A5" }}>
                USD {active.damage_usd_billion}B damages
              </span>
            )}
            <span className="text-[10px] shrink-0" style={{ color: "#4B6280" }}>
              {active.affected_provinces.join(" · ")}
            </span>
            <span className="text-[10px] flex-1 min-w-0 truncate" style={{ color: "#4B6280" }}>
              {active.description}
            </span>
          </div>
        );
      })()}
    </div>
  );
}
