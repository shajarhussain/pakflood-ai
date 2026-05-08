"use client";

import { useState } from "react";
import { SAR_REFERENCES, SAR_INTEGRATION_NOTE, type SarReference } from "@/data/sar-evidence";

const CATEGORY_COLORS: Record<SarReference["data_type"], string> = {
  open_dataset:      "#22D3EE",
  published_paper:   "#A78BFA",
  satellite_imagery: "#34D399",
  agency_report:     "#FCD34D",
};

const CATEGORY_LABELS: Record<SarReference["data_type"], string> = {
  open_dataset:      "Dataset",
  published_paper:   "Paper",
  satellite_imagery: "Imagery",
  agency_report:     "Report",
};

const ACCESS_BADGE: Record<SarReference["access"], { color: string; label: string }> = {
  open:         { color: "#22C55E", label: "Open" },
  registration: { color: "#F59E0B", label: "Register" },
  restricted:   { color: "#EF4444", label: "Restricted" },
};

export function SAREvidencePanel() {
  const [filter, setFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const events = Array.from(new Set(SAR_REFERENCES.map((r) => r.flood_event)));
  const filtered = filter === "all" ? SAR_REFERENCES : SAR_REFERENCES.filter((r) => r.flood_event === filter);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span style={{ fontSize: 16 }}>🛰</span>
          <h3 className="text-sm font-bold" style={{ color: "#F8FAFC" }}>
            SAR Evidence References
          </h3>
        </div>
        <p className="text-[10px] leading-relaxed" style={{ color: "#64748B" }}>
          Real published SAR datasets and papers used for flood mapping in Pakistan.
          No fabricated detections — all sources are verifiable.
        </p>
      </div>

      {/* Integration note */}
      <div
        className="mx-3 mb-2 px-3 py-2 rounded-lg shrink-0"
        style={{
          background: "rgba(139,92,246,0.10)",
          border: "1px solid rgba(139,92,246,0.22)",
        }}
      >
        <div className="flex gap-2 items-start">
          <span className="text-xs mt-0.5">🔬</span>
          <p className="text-[10px] leading-relaxed" style={{ color: "#A78BFA" }}>
            {SAR_INTEGRATION_NOTE}
          </p>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="px-3 mb-2 shrink-0 flex gap-1.5 flex-wrap">
        {["all", ...events].map((ev) => (
          <button
            key={ev}
            onClick={() => setFilter(ev)}
            className="text-[9px] font-semibold px-2 py-0.5 rounded-full transition"
            style={{
              background: filter === ev ? "rgba(34,211,238,0.18)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${filter === ev ? "rgba(34,211,238,0.35)" : "rgba(255,255,255,0.08)"}`,
              color: filter === ev ? "#22D3EE" : "#64748B",
            }}
          >
            {ev === "all" ? "All Events" : ev.replace("Pakistan ", "").replace(" Mega-Floods", " Mega")}
          </button>
        ))}
      </div>

      {/* Reference cards */}
      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
        {filtered.map((ref) => {
          const isOpen = expanded === ref.id;
          const typeColor = CATEGORY_COLORS[ref.data_type];
          const access = ACCESS_BADGE[ref.access];

          return (
            <div
              key={ref.id}
              className="rounded-xl overflow-hidden transition"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: `1px solid ${isOpen ? "rgba(34,211,238,0.22)" : "rgba(255,255,255,0.07)"}`,
              }}
            >
              {/* Card header */}
              <button
                className="w-full text-left px-3 py-2.5 flex items-start gap-2"
                onClick={() => setExpanded(isOpen ? null : ref.id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                    <span
                      className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                      style={{ background: `${typeColor}22`, color: typeColor }}
                    >
                      {CATEGORY_LABELS[ref.data_type]}
                    </span>
                    <span
                      className="text-[9px] font-semibold px-1.5 py-0.5 rounded"
                      style={{ background: `${access.color}18`, color: access.color }}
                    >
                      {access.label}
                    </span>
                    {ref.sensor && (
                      <span className="text-[9px]" style={{ color: "#475569" }}>
                        {ref.sensor.split(" ")[0]}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] font-semibold leading-snug" style={{ color: "#E2E8F0" }}>
                    {ref.title}
                  </p>
                  <p className="text-[10px] mt-0.5" style={{ color: "#64748B" }}>
                    {ref.source} · {ref.date}
                  </p>
                </div>
                <span
                  className="text-[10px] mt-1 shrink-0 transition-transform"
                  style={{
                    color: "#4B6280",
                    transform: isOpen ? "rotate(180deg)" : "none",
                  }}
                >
                  ▾
                </span>
              </button>

              {/* Expanded details */}
              {isOpen && (
                <div
                  className="px-3 pb-3"
                  style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
                >
                  <p className="text-[10px] leading-relaxed mt-2" style={{ color: "#94A3B8" }}>
                    {ref.description}
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
                    <div>
                      <span className="text-[9px]" style={{ color: "#475569" }}>Region</span>
                      <p className="text-[10px] font-medium" style={{ color: "#CBD5E1" }}>{ref.region}</p>
                    </div>
                    <div>
                      <span className="text-[9px]" style={{ color: "#475569" }}>Event</span>
                      <p className="text-[10px] font-medium" style={{ color: "#CBD5E1" }}>
                        {ref.flood_event.replace("Pakistan ", "")}
                      </p>
                    </div>
                    {ref.resolution_m && (
                      <div>
                        <span className="text-[9px]" style={{ color: "#475569" }}>Resolution</span>
                        <p className="text-[10px] font-medium" style={{ color: "#CBD5E1" }}>{ref.resolution_m}m</p>
                      </div>
                    )}
                    <div>
                      <span className="text-[9px]" style={{ color: "#475569" }}>Sensor</span>
                      <p className="text-[10px] font-medium" style={{ color: "#CBD5E1" }}>
                        {ref.sensor || "Multi-source"}
                      </p>
                    </div>
                  </div>
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2.5 inline-flex items-center gap-1.5 text-[10px] font-semibold transition"
                    style={{ color: "#22D3EE" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "#67E8F9")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "#22D3EE")}
                  >
                    Open source ↗
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
