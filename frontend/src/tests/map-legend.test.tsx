import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MapLegend } from "@/components/map/MapLegend";

function mockV3(artifactExists: boolean) {
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
        remediation: artifactExists ? null : "Real prediction model unavailable — run the real-data pipeline first.",
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    }
    return new Response("{}", { status: 200 });
  }));
}

async function flushStatus() {
  await new Promise((r) => setTimeout(r, 0));
  await new Promise((r) => setTimeout(r, 0));
}

describe("MapLegend — v3 artifact present (full calibrated legend)", () => {
  beforeEach(() => mockV3(true));

  it("renders all four risk levels", async () => {
    render(<MapLegend />);
    await flushStatus();
    expect(screen.getByText(/Severe/i)).toBeInTheDocument();
    expect(screen.getByText(/High/i)).toBeInTheDocument();
    expect(screen.getByText(/Moderate/i)).toBeInTheDocument();
    expect(screen.getByText(/Low/i)).toBeInTheDocument();
  });

  it("has accessible aria-label", async () => {
    render(<MapLegend />);
    await flushStatus();
    expect(
      screen.getByRole("generic", { name: /flood risk level legend/i })
    ).toBeInTheDocument();
  });

  it("shows a color swatch for each level", async () => {
    const { container } = render(<MapLegend />);
    await flushStatus();
    const swatches = container.querySelectorAll("span[style*='background-color']");
    expect(swatches).toHaveLength(4);
  });

  it("shows risk icons", async () => {
    const { container } = render(<MapLegend />);
    await flushStatus();
    const iconSpans = container.querySelectorAll("span[aria-hidden='true']");
    expect(iconSpans.length).toBeGreaterThanOrEqual(4);
  });
});

describe("MapLegend — v3 artifact missing (calibrated legend hidden)", () => {
  beforeEach(() => mockV3(false));

  it("hides risk-level rows and shows v3-unavailable message", async () => {
    render(<MapLegend />);
    await flushStatus();
    expect(screen.getByTestId("map-legend-unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/Severe/i)).toBeNull();
    expect(screen.queryByText(/Moderate/i)).toBeNull();
  });
});
