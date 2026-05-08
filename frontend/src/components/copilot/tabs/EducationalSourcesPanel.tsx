"use client";

import { useState } from "react";
import {
  EDUCATIONAL_SOURCES,
  CATEGORY_LABELS,
  type EducationalSource,
} from "@/data/educational-sources";

const CATEGORY_ICONS: Record<EducationalSource["category"], string> = {
  satellite:   "🛰",
  hydrology:   "🌊",
  meteorology: "⛈",
  relief:      "🤝",
  government:  "🏛",
  research:    "🔬",
};

const ACCESS_STYLE: Record<EducationalSource["access"], { color: string; label: string }> = {
  open:         { color: "#22C55E", label: "Open" },
  registration: { color: "#F59E0B", label: "Register" },
  api_key:      { color: "#22D3EE", label: "API Key" },
  restricted:   { color: "#EF4444", label: "Restricted" },
};

const ALL_CATEGORIES = Object.keys(CATEGORY_LABELS) as EducationalSource["category"][];

export function EducationalSourcesPanel() {
  const [activeCategory, setActiveCategory] = useState<EducationalSource["category"] | "all">("all");
  const [showUsedOnly, setShowUsedOnly] = useState(false);

  const filtered = EDUCATIONAL_SOURCES.filter((s) => {
    if (showUsedOnly && !s.used_in_system) return false;
    if (activeCategory !== "all" && s.category !== activeCategory) return false;
    return true;
  });

  const usedCount = EDUCATIONAL_SOURCES.filter((s) => s.used_in_system).length;
  const plannedCount = EDUCATIONAL_SOURCES.filter((s) => s.planned).length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span style={{ fontSize: 16 }}>📡</span>
          <h3 className="text-sm font-bold" style={{ color: "#F8FAFC" }}>
            Data Sources & Evidence
          </h3>
        </div>
        <div className="flex gap-3 mt-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "#22C55E" }} />
            <span className="text-[10px]" style={{ color: "#94A3B8" }}>{usedCount} integrated</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "#8B5CF6" }} />
            <span className="text-[10px]" style={{ color: "#94A3B8" }}>{plannedCount} planned v2</span>
          </div>
        </div>
      </div>

      {/* Category filter row */}
      <div className="px-3 mb-2 shrink-0 flex gap-1 flex-wrap">
        <button
          onClick={() => setActiveCategory("all")}
          className="text-[9px] font-semibold px-2 py-0.5 rounded-full transition"
          style={{
            background: activeCategory === "all" ? "rgba(34,211,238,0.18)" : "rgba(255,255,255,0.05)",
            border: `1px solid ${activeCategory === "all" ? "rgba(34,211,238,0.35)" : "rgba(255,255,255,0.08)"}`,
            color: activeCategory === "all" ? "#22D3EE" : "#64748B",
          }}
        >
          All
        </button>
        {ALL_CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className="text-[9px] font-semibold px-2 py-0.5 rounded-full transition"
            style={{
              background: activeCategory === cat ? "rgba(34,211,238,0.18)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${activeCategory === cat ? "rgba(34,211,238,0.35)" : "rgba(255,255,255,0.08)"}`,
              color: activeCategory === cat ? "#22D3EE" : "#64748B",
            }}
          >
            {CATEGORY_ICONS[cat]} {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {/* Toggle: used only */}
      <div className="px-3 mb-2 shrink-0">
        <button
          onClick={() => setShowUsedOnly((v) => !v)}
          className="flex items-center gap-2 text-[10px] transition"
          style={{ color: showUsedOnly ? "#22D3EE" : "#4B6280" }}
        >
          <span
            className="w-8 h-4 rounded-full flex items-center transition"
            style={{
              background: showUsedOnly ? "rgba(34,211,238,0.25)" : "rgba(255,255,255,0.08)",
              border: `1px solid ${showUsedOnly ? "rgba(34,211,238,0.4)" : "rgba(255,255,255,0.1)"}`,
              padding: "1px",
            }}
          >
            <span
              className="w-3 h-3 rounded-full transition-all"
              style={{
                background: showUsedOnly ? "#22D3EE" : "#334155",
                marginLeft: showUsedOnly ? "auto" : 0,
              }}
            />
          </span>
          Show integrated only
        </button>
      </div>

      {/* Source cards */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
        {filtered.map((src) => {
          const access = ACCESS_STYLE[src.access];
          const icon = CATEGORY_ICONS[src.category];

          return (
            <div
              key={src.id}
              className="rounded-xl p-3"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: src.used_in_system
                  ? "1px solid rgba(34,211,238,0.18)"
                  : src.planned
                  ? "1px solid rgba(139,92,246,0.18)"
                  : "1px solid rgba(255,255,255,0.07)",
              }}
            >
              <div className="flex items-start gap-2.5">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-sm"
                  style={{ background: "rgba(255,255,255,0.06)" }}
                >
                  {icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                    <span className="text-[11px] font-bold truncate" style={{ color: "#E2E8F0" }}>
                      {src.short_name}
                    </span>
                    {src.used_in_system && (
                      <span
                        className="text-[8px] font-bold px-1 py-0.5 rounded"
                        style={{ background: "rgba(34,211,238,0.15)", color: "#22D3EE" }}
                      >
                        INTEGRATED
                      </span>
                    )}
                    {src.planned && !src.used_in_system && (
                      <span
                        className="text-[8px] font-bold px-1 py-0.5 rounded"
                        style={{ background: "rgba(139,92,246,0.15)", color: "#A78BFA" }}
                      >
                        v2
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] leading-relaxed" style={{ color: "#94A3B8" }}>
                    {src.description}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                    <span
                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded"
                      style={{ background: `${access.color}18`, color: access.color }}
                    >
                      {access.label}
                    </span>
                    <span className="text-[9px]" style={{ color: "#475569" }}>
                      {src.update_frequency}
                    </span>
                    <span className="text-[9px]" style={{ color: "#475569" }}>
                      {src.data_type}
                    </span>
                  </div>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1.5 inline-block text-[9px] font-semibold transition"
                    style={{ color: "#38BDF8" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#7DD3FC")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "#38BDF8")}
                  >
                    {src.url.replace(/^https?:\/\//, "").split("/")[0]} ↗
                  </a>
                </div>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-8" style={{ color: "#475569" }}>
            <p className="text-sm">No sources match this filter.</p>
          </div>
        )}
      </div>

      {/* Footer disclaimer */}
      <div
        className="px-3 py-2 shrink-0 text-[9px] leading-relaxed"
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          color: "#475569",
        }}
      >
        Always verify data directly from official sources. PMD, FFD, NDMA, and PDMA are the
        authoritative bodies for flood warnings in Pakistan.
      </div>
    </div>
  );
}
