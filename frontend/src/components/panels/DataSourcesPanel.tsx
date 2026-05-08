"use client";

import { useEffect, useState } from "react";
import { fetchDataSources, type ApiDataSource } from "@/lib/api";
import type { SourceStatus } from "@/components/layout/SourceBadge";

const STATUS_DOT: Record<string, string> = {
  fresh:    "bg-green-400",
  stale:    "bg-yellow-400",
  error:    "bg-red-400",
  disabled: "bg-slate-500",
};

function isValidStatus(s: string): s is SourceStatus {
  return ["fresh", "stale", "error", "disabled"].includes(s);
}

export function DataSourcesPanel() {
  const [sources, setSources] = useState<ApiDataSource[]>([]);

  useEffect(() => {
    fetchDataSources().then((data) => {
      if (data.length > 0) setSources(data);
    });
  }, []);

  if (sources.length === 0) return null;

  return (
    <div className="border-t border-slate-800 pt-2 mt-1">
      <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 px-1">
        Data Sources
      </p>
      <ul className="flex flex-col gap-1">
        {sources.map((src) => {
          const status = isValidStatus(src.status) ? src.status : "error";
          return (
            <li
              key={src.id}
              className="flex items-center gap-1.5 px-1"
              title={src.error_message ?? src.description}
            >
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${STATUS_DOT[status]}`} />
              <span className="text-[10px] text-slate-300 truncate flex-1">{src.name}</span>
              <span
                className={`text-[9px] font-semibold uppercase ${
                  status === "fresh" ? "text-green-400"
                  : status === "stale" ? "text-yellow-400"
                  : status === "error" ? "text-red-400"
                  : "text-slate-500"
                }`}
              >
                {status}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
