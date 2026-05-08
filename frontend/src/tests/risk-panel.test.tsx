import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RiskExplanationPanel } from "@/components/panels/RiskExplanationPanel";
import type { RiskExplanation } from "@/lib/types";
import type { MockRiskEntry } from "@/data/mock";
import { DISCLAIMER } from "@/data/mock";

const mockDistrict: MockRiskEntry = {
  district_id: "PK-SD-SKR",
  name: "Sukkur",
  province: "Sindh",
  center: [27.7, 68.86],
  risk_score: 0.82,
  risk_level: "High",
  confidence: 0.74,
  top_factors: ["7-day rainfall anomaly", "near Indus floodplain", "historical flood frequency"],
};

const mockExplanation: RiskExplanation = {
  risk_level: "High",
  main_causes: ["7-day rainfall anomaly", "near Indus floodplain"],
  historical_evidence: ["Severely flooded in 2010 and 2011"],
  suggested_actions: ["Follow PMD advisories", "Prepare emergency supplies"],
  confidence: 0.74,
  data_sources: ["Mock IMERG (Phase 1)", "Seed data"],
  disclaimer: DISCLAIMER,
};

describe("RiskExplanationPanel — empty state", () => {
  it("renders empty state when no district selected", () => {
    render(<RiskExplanationPanel district={null} explanation={null} onClose={() => {}} />);
    expect(screen.getByText(/Select a district/i)).toBeInTheDocument();
  });
});

describe("RiskExplanationPanel — filled state", () => {
  it("shows Flood Risk heading", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText("Flood Risk")).toBeInTheDocument();
  });

  it("shows district name and province", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/Sukkur/)).toBeInTheDocument();
    expect(screen.getByText(/Sindh/)).toBeInTheDocument();
  });

  it("shows Confidence value", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText("74%")).toBeInTheDocument();
  });

  it("shows Official sources section", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/Official sources/i)).toBeInTheDocument();
  });

  it("always shows the safety disclaimer", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    const disclaimer = screen.getByRole("note", { name: /official warning disclaimer/i });
    expect(disclaimer).toBeInTheDocument();
    expect(disclaimer.textContent).toMatch(/educational decision-support prototype/i);
    expect(disclaimer.textContent).toMatch(/PMD/);
    expect(disclaimer.textContent).toMatch(/NDMA/);
  });

  it("disclaimer does not claim to be an official warning", () => {
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={() => {}}
      />
    );
    const disclaimerEl = screen.getByRole("note");
    expect(disclaimerEl.textContent).not.toMatch(/official warning from/i);
    expect(disclaimerEl.textContent).toMatch(/prototype/i);
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(
      <RiskExplanationPanel
        district={mockDistrict}
        explanation={mockExplanation}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /close risk panel/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
