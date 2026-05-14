/**
 * v3 honest-rendering tests.
 *
 * When /api/v1/model/status reports artifact_exists=false, the UI must not
 * surface fake risk numbers, fake confidence, fake factor bars, or fake
 * severity counts as if they were v3 prediction output.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { RiskBrief } from "@/components/copilot/tabs/RiskBrief";
import { RiskIndexBadge } from "@/components/map/RiskIndexBadge";
import { MapLegend } from "@/components/map/MapLegend";
import { SimulationLab } from "@/components/copilot/tabs/SimulationLab";
import { RISK_BY_ID, DISCLAIMER } from "@/data/mock";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";

const lahore: MockRiskEntry = {
  district_id: "PK-PB-LHR",
  name: "Lahore",
  province: "Punjab",
  center: [31.55, 74.4],
  risk_score: 0.38,
  risk_level: "Moderate",
  confidence: 0.5,
  top_factors: ["urban drainage", "moderate rainfall", "river proximity"],
};

const explanation: RiskExplanation = {
  risk_level: "Moderate",
  main_causes: ["urban drainage", "moderate rainfall"],
  historical_evidence: [],
  suggested_actions: ["Monitor PMD advisories"],
  confidence: 0.5,
  data_sources: [],
  disclaimer: DISCLAIMER,
};

function mockModelStatus(artifactExists: boolean) {
  // Reset & install the global fetch mock once per test.
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/model/status")) {
      return new Response(JSON.stringify({
        mode: "real_prediction",
        artifact_exists: artifactExists,
        artifact_path: "ml/artifacts/flood_prediction_calibrated_v3.pkl",
        metadata_exists: artifactExists,
        metadata_path: "ml/artifacts/flood_prediction_metadata_v3.json",
        is_prediction_model: artifactExists,
        model_name: artifactExists ? "flood_prediction_v3" : null,
        model_type: artifactExists ? "BalancedRandomForestClassifier + sigmoid CalibratedClassifierCV" : null,
        prediction_window: artifactExists ? "T+1 to T+3 days" : null,
        calibration_method: artifactExists ? "sigmoid" : null,
        calibration_api: artifactExists ? "FrozenEstimator" : null,
        last_trained_iso: artifactExists ? "2026-05-13T12:00:00Z" : null,
        data_sources: null,
        metric_crs: artifactExists ? "EPSG:6933" : null,
        remediation: artifactExists ? null : "Real prediction model unavailable — run the real-data pipeline first.",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    return new Response("{}", { status: 200 });
  }));
}

async function waitForStatus() {
  // useModelStatus fires fetch in useEffect; flush microtasks twice so React
  // commits the state update before the assertions run.
  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
}


describe("v3 honesty — artifact missing", () => {
  beforeEach(() => mockModelStatus(false));

  it("RiskBrief hides the fake 38% risk score, HIGH/MODERATE pill, and factor bars", async () => {
    render(<RiskBrief district={lahore} explanation={explanation} />);
    await waitForStatus();

    // Unavailable state should be present (text may render in multiple places)
    expect(screen.getByTestId("risk-brief-unavailable")).toBeInTheDocument();
    expect(screen.getAllByText(/Real prediction model unavailable/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Run the real-data pipeline first/i).length).toBeGreaterThan(0);

    // The fake number-of-percent badge must NOT appear
    expect(screen.queryByText("38%")).toBeNull();
    expect(screen.queryByText("50%")).toBeNull();

    // The MODERATE/HIGH risk pill (uppercase) must NOT appear
    expect(screen.queryByText("MODERATE")).toBeNull();
    expect(screen.queryByText("HIGH")).toBeNull();

    // Factor bars must NOT appear
    expect(screen.queryByText(/urban drainage/i)).toBeNull();
    expect(screen.queryByText("91%")).toBeNull();

    // No "Real prediction v3" label may be shown when artifact missing
    expect(screen.queryByText(/Real prediction v3/i)).toBeNull();
  });

  it("RiskIndexBadge hides the mock severity counts", async () => {
    render(<RiskIndexBadge riskData={RISK_BY_ID} />);
    await waitForStatus();

    expect(screen.getByTestId("risk-index-badge-unavailable")).toBeInTheDocument();
    expect(screen.getByText(/Demo risk layer disabled in real_prediction mode/i)).toBeInTheDocument();
    // The legacy "3 SEV" / "2 HIGH" / "SEVERE" indicators must NOT render.
    expect(screen.queryByText(/SEV$/)).toBeNull();
    expect(screen.queryByText("SEVERE")).toBeNull();
  });

  it("MapLegend hides the calibrated colour legend", async () => {
    render(<MapLegend />);
    await waitForStatus();

    expect(screen.getByTestId("map-legend-unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/Severe/)).toBeNull();
    expect(screen.queryByText(/Moderate/)).toBeNull();
  });

  it("SimulationLab is disabled", async () => {
    render(<SimulationLab district={lahore} />);
    await waitForStatus();

    expect(screen.getByTestId("simulation-lab-unavailable")).toBeInTheDocument();
    expect(screen.getByText(/Simulation disabled until real prediction artifact/i)).toBeInTheDocument();
    expect(screen.queryByText(/Reset to baseline/i)).toBeNull();
  });
});


describe("v3 honesty — artifact present (mocked)", () => {
  beforeEach(() => mockModelStatus(true));

  it("RiskBrief shows the Real prediction v3 label", async () => {
    render(<RiskBrief district={lahore} explanation={explanation} />);
    await waitForStatus();

    expect(screen.getByText(/Real prediction v3/i)).toBeInTheDocument();
    expect(screen.queryByTestId("risk-brief-unavailable")).toBeNull();
  });
});
