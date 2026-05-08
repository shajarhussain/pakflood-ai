import { describe, it, expect } from "vitest";
import { riskColor, RISK_COLORS } from "@/lib/risk-colors";

describe("risk-colors", () => {
  it("returns correct color for each risk level", () => {
    expect(riskColor("Low")).toBe(RISK_COLORS.Low);
    expect(riskColor("Moderate")).toBe(RISK_COLORS.Moderate);
    expect(riskColor("High")).toBe(RISK_COLORS.High);
    expect(riskColor("Severe")).toBe(RISK_COLORS.Severe);
  });

  it("all levels have defined colors", () => {
    const levels = ["Low", "Moderate", "High", "Severe"] as const;
    levels.forEach((level) => {
      expect(RISK_COLORS[level]).toMatch(/^#[0-9a-f]{6}$/i);
    });
  });
});
