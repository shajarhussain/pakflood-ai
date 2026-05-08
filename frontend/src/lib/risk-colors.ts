import type { RiskLevel } from "./types";

export const RISK_COLORS: Record<RiskLevel, string> = {
  Low: "#22c55e",       // green-500
  Moderate: "#eab308",  // yellow-500
  High: "#f97316",      // orange-500
  Severe: "#ef4444",    // red-500
};

export const RISK_ICONS: Record<RiskLevel, string> = {
  Low: "●",
  Moderate: "▲",
  High: "■",
  Severe: "⬟",
};

export const RISK_BG: Record<RiskLevel, string> = {
  Low: "bg-green-500/20 border-green-500",
  Moderate: "bg-yellow-500/20 border-yellow-500",
  High: "bg-orange-500/20 border-orange-500",
  Severe: "bg-red-500/20 border-red-500",
};

export function riskColor(level: RiskLevel): string {
  return RISK_COLORS[level] ?? "#6b7280";
}
