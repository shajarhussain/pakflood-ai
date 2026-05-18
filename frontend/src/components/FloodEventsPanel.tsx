"use client";
import type { FloodEvent } from "@/lib/types";

interface Props {
  events: FloodEvent[];
  onClose: () => void;
  selectedEventId?: string | null;
  onEventSelect?: (event: FloodEvent | null) => void;
  isSignedIn?: boolean;
  onRequestSignIn?: () => void;
  aiInsight?: string | null;
  aiInsightLoading?: boolean;
  aiInsightEventId?: string | null;
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

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

export default function FloodEventsPanel({
  events, onClose, selectedEventId, onEventSelect,
  isSignedIn = false, onRequestSignIn,
  aiInsight, aiInsightLoading, aiInsightEventId,
}: Props) {
  return (
    <div className="absolute top-[56px] left-0 bottom-0 z-[1000] w-72 flex flex-col bg-slate-950/95 border-r border-white/10 backdrop-blur-sm animate-fade-up">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-slate-300 text-xs font-semibold uppercase tracking-wider">Flood Events</span>
          <span className="text-slate-600 text-[10px]">Pakistan</span>
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

      {/* Scrollable card list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-2.5 p-3">
        {events.length === 0 ? (
          <p className="text-slate-500 text-xs text-center mt-8">No historical flood events found.</p>
        ) : (
          events.map((event) => {
            const c      = eventColor(event.year);
            const active = selectedEventId === event.id;
            const isThisInsight = active && aiInsightEventId === event.id;
            return (
              <div
                key={event.id}
                onClick={() => onEventSelect?.(active ? null : event)}
                className="rounded-xl p-3 flex flex-col gap-2 cursor-pointer transition-all hover:brightness-110 active:scale-[0.98]"
                style={{
                  background: c.bg,
                  border:     active ? `2px solid ${c.text}` : `1px solid ${c.border}`,
                  boxShadow:  active ? `0 0 16px ${c.text}35` : "none",
                }}
              >
                {/* Year + title row */}
                <div className="flex items-start gap-2.5">
                  <div className="text-2xl font-black leading-none shrink-0" style={{ color: c.text }}>
                    {event.year}
                  </div>
                  <div className="flex flex-col gap-1 min-w-0">
                    <div className="text-slate-200 text-[11px] font-semibold leading-snug line-clamp-2">
                      {event.title}
                    </div>
                    {active && (
                      <span className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded w-fit" style={{ background: `${c.text}22`, color: c.text }}>
                        Showing on map
                      </span>
                    )}
                  </div>
                </div>

                {/* Stats row */}
                <div className="flex items-center gap-4">
                  {event.estimated_affected != null && (
                    <div>
                      <div className="text-slate-200 text-xs font-bold leading-none">{formatAffected(event.estimated_affected)}</div>
                      <div className="text-slate-500 text-[10px] mt-0.5">affected</div>
                    </div>
                  )}
                  {event.damage_usd_billion != null && (
                    <div>
                      <div className="text-slate-200 text-xs font-bold leading-none">${event.damage_usd_billion}B</div>
                      <div className="text-slate-500 text-[10px] mt-0.5">damage</div>
                    </div>
                  )}
                  {event.peak_month && (
                    <div>
                      <div className="text-slate-200 text-xs font-bold leading-none">{event.peak_month.slice(0, 3)}</div>
                      <div className="text-slate-500 text-[10px] mt-0.5">peak</div>
                    </div>
                  )}
                </div>

                {/* Province chips */}
                {event.affected_provinces.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {event.affected_provinces.map((p) => (
                      <span
                        key={p}
                        className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ color: c.text, background: `${c.text}18`, border: `1px solid ${c.text}30` }}
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

                {/* ── AI Insight section (active card only) ─────────────────── */}
                {active && (
                  <div
                    className="rounded-lg p-2.5 mt-0.5"
                    style={{ background: "rgba(6,182,212,0.06)", border: "1px solid rgba(6,182,212,0.18)" }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {/* AI label row */}
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <svg className="w-3 h-3 text-cyan-400 shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                        <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z"/>
                      </svg>
                      <span className="text-cyan-400 text-[10px] font-semibold uppercase tracking-wider">AI Analysis</span>
                    </div>

                    {/* Content states */}
                    {!isSignedIn ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); onRequestSignIn?.(); }}
                        className="w-full text-left text-[10px] text-slate-500 hover:text-cyan-400 transition-colors"
                      >
                        🔒 Sign in to get AI event analysis →
                      </button>
                    ) : isThisInsight && aiInsightLoading ? (
                      <ThinkingDots />
                    ) : isThisInsight && aiInsight ? (
                      <p className="text-slate-300 text-[10px] leading-relaxed">{aiInsight}</p>
                    ) : (
                      <p className="text-slate-600 text-[10px]">Generating analysis…</p>
                    )}
                  </div>
                )}

                {/* Click hint when not active */}
                {!active && (
                  <p className="text-slate-700 text-[9px] text-right">Click to show on map →</p>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/5 shrink-0">
        <p className="text-slate-700 text-[10px]">Source: HDX Pakistan flood event data · Educational reference only</p>
      </div>
    </div>
  );
}
