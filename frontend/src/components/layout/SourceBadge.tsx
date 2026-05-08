"use client";

export type SourceStatus = "fresh" | "stale" | "error" | "disabled";

interface Props {
  name: string;
  status: SourceStatus;
}

const STATUS_STYLE: Record<SourceStatus, string> = {
  fresh:    "bg-green-500/20 text-green-300 border-green-600",
  stale:    "bg-yellow-500/20 text-yellow-300 border-yellow-600",
  error:    "bg-red-500/20 text-red-300 border-red-600",
  disabled: "bg-slate-500/20 text-slate-400 border-slate-600",
};

const STATUS_LABEL: Record<SourceStatus, string> = {
  fresh:    "Fresh",
  stale:    "Stale",
  error:    "Error",
  disabled: "Disabled",
};

export function SourceBadge({ name, status }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs border rounded px-1.5 py-0.5 ${STATUS_STYLE[status]}`}
    >
      {name}
      <span className="font-medium">· {STATUS_LABEL[status]}</span>
    </span>
  );
}
