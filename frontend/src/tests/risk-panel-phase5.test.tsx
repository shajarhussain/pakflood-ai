/**
 * Phase 5 tests for RiskExplanationPanel.
 * Tests live explanation shape, fallback behaviour, and required display elements.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RiskExplanationPanel } from "@/components/panels/RiskExplanationPanel";
import type { RiskExplanation } from "@/lib/types";
import type { MockRiskEntry } from "@/data/mock";

const mockDistrict: MockRiskEntry = {
  district_id: "PK-SD-SKR",
  name: "Sukkur",
  province: "Sindh",
  center: [27.7, 68.86],
  risk_score: 0.82,
  risk_level: "High",
  confidence: 0.74,
  top_factors: ["7-day rainfall anomaly", "near Indus floodplain"],
};

// Matches the shape returned by GET /explain-risk/by-boundary/{id}
const liveExplanation: RiskExplanation = {
  risk_level: "High",
  main_causes: [
    "Elevated river discharge (GloFAS forecast)",
    "Rainfall anomaly above seasonal average",
  ],
  historical_evidence: [
    "2022: 2022 Catastrophic Floods (August) — 33,000,000 people affected, ~USD 14.9B damage.",
    "2010: 2010 Pakistan Super Floods (August) — 20,000,000 people affected.",
  ],
  suggested_actions: [
    "Avoid low-lying roads and areas near rivers or canals.",
    "Prepare and discuss your evacuation plan with your household.",
    "Follow all official NDMA/PDMA advisories (helpline: 1700).",
  ],
  confidence: 0.74,
  data_sources: [
    "NASA IMERG (GPM) (Stale)",
    "GloFAS River Discharge (Stale)",
    "ReliefWeb Articles (Fresh)",
  ],
  disclaimer:
    "Educational prototype. Not an official warning. Follow PMD, FFD, NDMA, PDMA, and local authorities.",
};

describe("RiskExplanationPanel — Phase 5 live explanation shape", () => {
  it("renders main causes from live explanation", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={liveExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/Elevated river discharge/i)).toBeInTheDocument();
  });

  it("renders historical evidence from live explanation", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={liveExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/2022.*Catastrophic/i)).toBeInTheDocument();
  });

  it("renders data sources section", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={liveExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/Official sources/i)).toBeInTheDocument();
    expect(screen.getByText(/IMERG/i)).toBeInTheDocument();
  });

  it("renders confidence percentage", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={liveExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText("74%")).toBeInTheDocument();
  });

  it("disclaimer does not claim official warning", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={liveExplanation}
        onClose={() => {}}
      />
    );
    const note = screen.getByRole("note", { name: /official warning disclaimer/i });
    expect(note.textContent).not.toMatch(/official warning from/i);
    expect(note.textContent).toMatch(/prototype/i);
  });

  it("shows disclaimer even for Severe risk", () => {
    const severeExplanation: RiskExplanation = {
      ...liveExplanation,
      risk_level: "Severe",
    };
    render(
      <RiskExplanationPanel
        district={{ ...mockDistrict, risk_level: "Severe" }}
        explanation={severeExplanation}
        onClose={() => {}}
      />
    );
    const note = screen.getByRole("note");
    expect(note).toBeInTheDocument();
    expect(note.textContent).toMatch(/prototype/i);
  });
});

describe("RiskExplanationPanel — fallback when backend is unavailable", () => {
  it("renders mock explanation if live is null", () => {
    // The panel receives whatever explanation prop MapDashboard passes.
    // When backend is down, MapDashboard passes buildMockExplanation(district).
    const mockExplanation: RiskExplanation = {
      risk_level: "High",
      main_causes: ["7-day rainfall anomaly", "near Indus floodplain"],
      historical_evidence: ["Severely flooded in 2010 and 2011"],
      suggested_actions: ["Follow official evacuation orders"],
      confidence: 0.74,
      data_sources: ["Mock IMERG (Phase 1 — not connected)"],
      disclaimer:
        "PakFlood AI is an educational decision-support prototype. Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions.",
    };
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/7-day rainfall anomaly/i)).toBeInTheDocument();
    expect(screen.getByRole("note")).toBeInTheDocument();
  });
});
