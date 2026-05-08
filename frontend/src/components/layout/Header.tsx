"use client";

import { useState, useRef, useEffect } from "react";
import { searchLocations, type ApiLocationResult } from "@/lib/api";
import { RISK_COLORS, RISK_ICONS } from "@/lib/risk-colors";
import type { RiskLevel } from "@/lib/types";

interface Props {
  onDistrictSelect: (result: ApiLocationResult) => void;
}

export function Header({ onDistrictSelect }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ApiLocationResult[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search — setState always inside the timer callback to satisfy lint rule
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (query.length < 2) {
        setResults([]);
        setOpen(false);
        return;
      }
      const data = await searchLocations(query);
      setResults(data);
      setOpen(true);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function select(result: ApiLocationResult) {
    onDistrictSelect(result);
    setQuery("");
    setOpen(false);
    setResults([]);
  }

  return (
    <header className="flex items-center gap-4 px-4 py-2 bg-slate-900 border-b border-slate-700 z-10 shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-lg font-bold text-cyan-400 tracking-wide">PakFlood AI</span>
        <span className="hidden sm:block text-slate-500 text-xs">| Flood Intelligence Dashboard</span>
      </div>

      {/* Search */}
      <div ref={containerRef} className="relative ml-auto w-64 sm:w-72">
        <input
          type="text"
          placeholder="Search district…"
          aria-label="Search district"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.length < 2) setOpen(false);
          }}
          onFocus={() => results.length > 0 && setOpen(true)}
          className="w-full bg-slate-800 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
        />

        {open && results.length > 0 && (
          <ul
            role="listbox"
            className="absolute top-full mt-1 w-full bg-slate-800 border border-slate-600 rounded-md shadow-xl z-50 overflow-hidden"
          >
            {results.map((r) => (
              <li
                key={r.district_id}
                role="option"
                aria-selected={false}
                onClick={() => select(r)}
                className="flex items-center justify-between px-3 py-2 hover:bg-slate-700 cursor-pointer"
              >
                <div>
                  <span className="text-white text-sm font-medium">{r.name}</span>
                  <span className="text-slate-400 text-xs ml-2">{r.province}</span>
                </div>
                <span
                  className="text-xs font-semibold flex items-center gap-1"
                  style={{ color: RISK_COLORS[r.risk_level as RiskLevel] }}
                >
                  <span>{RISK_ICONS[r.risk_level as RiskLevel]}</span>
                  {r.risk_level}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Data freshness badge */}
      <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-500 shrink-0">
        <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
        API · Phase 2
      </div>
    </header>
  );
}
