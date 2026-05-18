"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { searchDistricts } from "@/lib/api";
import { RISK_COLORS } from "@/lib/risk-colors";
import type { DistrictSearchResult, RiskLevel } from "@/lib/types";

interface Props {
  onSelect: (lat: number, lng: number, name: string) => void;
}

export default function SearchBar({ onSelect }: Props) {
  const [query,     setQuery    ] = useState("");
  const [results,   setResults  ] = useState<DistrictSearchResult[]>([]);
  const [loading,   setLoading  ] = useState(false);
  const [isOpen,    setIsOpen   ] = useState(false);
  const [highlight, setHighlight] = useState(-1);

  const inputRef     = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search — fires 300 ms after the last keystroke
  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setIsOpen(false);
      setLoading(false);
      return;
    }
    setLoading(true);
    const timer = setTimeout(async () => {
      const data = await searchDistricts(query);
      setResults(data);
      setIsOpen(data.length > 0);
      setHighlight(-1);
      setLoading(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = useCallback(
    (r: DistrictSearchResult) => {
      onSelect(r.center.lat, r.center.lng, r.name);
      setQuery(r.name);
      setIsOpen(false);
      setHighlight(-1);
      inputRef.current?.blur();
    },
    [onSelect]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const idx = highlight >= 0 ? highlight : 0;
      if (results[idx]) handleSelect(results[idx]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  return (
    <div ref={containerRef} className="absolute top-[72px] left-1/9 z-[1100] w-72 sm:w-65" style={{ transform: "translateX(-50%)" }}>
      {/* Input field */}
      <div className="relative">
        {/* Search icon */}
        <svg
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search district… (e.g. Lahore)"
          autoComplete="off"
          spellCheck={false}
          className="w-full pl-10 pr-8 py-2.5 rounded-full bg-slate-900/90 border border-white/15 text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:bg-slate-900 transition-all backdrop-blur-md shadow-xl"
        />

        {/* Right icon: spinner or clear */}
        {loading ? (
          <svg
            className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 animate-spin"
            fill="none" viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        ) : query ? (
          <button
            onClick={handleClear}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 flex items-center justify-center text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Clear search"
          >
            <svg fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" className="w-3.5 h-3.5">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        ) : null}
      </div>

      {/* Dropdown results */}
      {isOpen && results.length > 0 && (
        <div className="mt-1.5 rounded-2xl bg-slate-900/98 border border-white/10 shadow-2xl overflow-hidden backdrop-blur-md animate-fade-up">
          {results.map((r, i) => {
            const isHighlighted = highlight === i;
            const summary       = r.summary;
            const avgPct        = summary?.avg_flood_prob != null
              ? Math.round(summary.avg_flood_prob * 100)
              : null;
            const dominantRisk  = summary?.dominant_risk ?? null;
            const riskColor     = dominantRisk
              ? RISK_COLORS[dominantRisk as RiskLevel]
              : undefined;

            return (
              <button
                key={r.district_id}
                // mouseDown fires before blur so we use it instead of onClick
                onMouseDown={(e) => { e.preventDefault(); handleSelect(r); }}
                onMouseEnter={() => setHighlight(i)}
                className={`w-full text-left px-4 py-2.5 flex items-center justify-between gap-3 transition-colors border-b border-white/5 last:border-0 ${
                  isHighlighted ? "bg-slate-700/60" : "hover:bg-slate-800/50"
                }`}
              >
                {/* Name + province */}
                <div className="min-w-0">
                  <div className="text-slate-200 text-sm font-medium leading-tight truncate">
                    {r.name}
                  </div>
                  <div className="text-slate-500 text-xs mt-0.5">{r.province}</div>
                </div>

                {/* Risk badge + avg probability */}
                <div className="flex items-center gap-1.5 shrink-0">
                  {avgPct !== null && (
                    <span className="text-slate-500 text-[10px] tabular-nums">{avgPct}%</span>
                  )}
                  {dominantRisk && riskColor && (
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{
                        color:      riskColor,
                        background: `${riskColor}20`,
                        border:     `1px solid ${riskColor}40`,
                      }}
                    >
                      {dominantRisk}
                    </span>
                  )}
                  {!dominantRisk && (
                    <span className="text-slate-600 text-[10px]">No data</span>
                  )}
                </div>
              </button>
            );
          })}

          <div className="px-4 py-1.5 border-t border-white/5">
            <p className="text-slate-600 text-[10px]">
              {results.length} result{results.length !== 1 ? "s" : ""} · click or ↑↓ Enter
            </p>
          </div>
        </div>
      )}

      {/* No results hint */}
      {isOpen && results.length === 0 && !loading && query.trim().length >= 2 && (
        <div className="mt-1.5 px-4 py-3 rounded-2xl bg-slate-900/98 border border-white/10 shadow-xl backdrop-blur-md">
          <p className="text-slate-500 text-sm">No districts found for &ldquo;{query}&rdquo;</p>
        </div>
      )}
    </div>
  );
}
