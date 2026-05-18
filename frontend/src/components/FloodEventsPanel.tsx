"use client";
import type { FloodEvent } from "@/lib/types";

interface Props {
  events: FloodEvent[];
  onClose: () => void;
}

function formatAffected(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(0)}M+`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K+`;
  return String(n);
}

const YEAR_COLOR: Record<number, { text: string; bg: string; border: string }> = {
  2022: { text: "#ef4444", bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.25)"   },
  2010: { text: "#f97316", bg: "rgba(249,115,22,0.08)",  border: "rgba(249,115,22,0.25)"  },
  2011: { text: "#eab308", bg: "rgba(234,179,8,0.08)",   border: "rgba(234,179,8,0.25)"   },
  2014: { text: "#22c55e", bg: "rgba(34,197,94,0.08)",   border: "rgba(34,197,94,0.25)"   },
};

function eventColor(year: number) {
  return YEAR_COLOR[year] ?? { text: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.2)" };
}

export default function FloodEventsPanel({ events, onClose }: Props) {
  if (events.length === 0) {
    return (
      <div className="absolute bottom-0 left-0 right-0 z-[1000] bg-slate-950/95 border-t border-white/10 backdrop-blur-sm px-4 py-4">
        <p className="text-slate-500 text-sm text-center">No historical flood events found.</p>
      </div>
    );
  }

  return (
    <div className="absolute bottom-0 left-0 right-0 z-[1000] bg-slate-950/95 border-t border-white/10 backdrop-blur-sm animate-fade-up">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/5">
        <div className="flex items-center gap-2">
          <span className="text-slate-300 text-xs font-semibold uppercase tracking-wider">Historical Flood Events</span>
          <span className="text-slate-600 text-xs">Pakistan</span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors p-1 rounded"
          aria-label="Close events panel"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Horizontal scroll of event cards */}
      <div className="flex gap-3 px-4 py-3 overflow-x-auto scrollbar-thin">
        {events.map((event) => {
          const c = eventColor(event.year);
          return (
            <div
              key={event.id}
              className="shrink-0 w-64 rounded-xl p-3.5 flex flex-col gap-2"
              style={{ background: c.bg, border: `1px solid ${c.border}` }}
            >
              {/* Year + title */}
              <div>
                <div className="text-2xl font-black leading-none mb-1" style={{ color: c.text }}>
                  {event.year}
                </div>
                <div className="text-slate-200 text-xs font-semibold leading-snug line-clamp-2">
                  {event.title}
                </div>
              </div>

              {/* Stats row */}
              <div className="flex items-center gap-3">
                {event.estimated_affected != null && (
                  <div>
                    <div className="text-slate-200 text-sm font-bold leading-none">
                      {formatAffected(event.estimated_affected)}
                    </div>
                    <div className="text-slate-500 text-[10px] mt-0.5">affected</div>
                  </div>
                )}
                {event.damage_usd_billion != null && (
                  <div>
                    <div className="text-slate-200 text-sm font-bold leading-none">
                      ${event.damage_usd_billion}B
                    </div>
                    <div className="text-slate-500 text-[10px] mt-0.5">damage</div>
                  </div>
                )}
                {event.peak_month && (
                  <div>
                    <div className="text-slate-200 text-sm font-bold leading-none">
                      {event.peak_month.slice(0, 3)}
                    </div>
                    <div className="text-slate-500 text-[10px] mt-0.5">peak</div>
                  </div>
                )}
              </div>

              {/* Provinces */}
              {event.affected_provinces.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {event.affected_provinces.map((p) => (
                    <span
                      key={p}
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{
                        color: c.text,
                        background: `${c.text}18`,
                        border: `1px solid ${c.text}30`,
                      }}
                    >
                      {p}
                    </span>
                  ))}
                </div>
              )}

              {/* Description */}
              <p className="text-slate-500 text-[10px] leading-relaxed line-clamp-3">
                {event.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <div className="px-4 pb-2">
        <p className="text-slate-700 text-[10px]">
          Source: HDX Pakistan flood event data · Educational reference only
        </p>
      </div>
    </div>
  );
}
