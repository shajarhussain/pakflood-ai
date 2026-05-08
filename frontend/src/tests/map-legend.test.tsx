import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MapLegend } from "@/components/map/MapLegend";

describe("MapLegend", () => {
  it("renders all four risk levels", () => {
    render(<MapLegend />);
    expect(screen.getByText(/Severe/i)).toBeInTheDocument();
    expect(screen.getByText(/High/i)).toBeInTheDocument();
    expect(screen.getByText(/Moderate/i)).toBeInTheDocument();
    expect(screen.getByText(/Low/i)).toBeInTheDocument();
  });

  it("has accessible aria-label", () => {
    render(<MapLegend />);
    expect(
      screen.getByRole("generic", { name: /flood risk level legend/i })
    ).toBeInTheDocument();
  });

  it("shows a color swatch for each level", () => {
    const { container } = render(<MapLegend />);
    // 4 colored squares (each is a span with background-color style)
    const swatches = container.querySelectorAll("span[style*='background-color']");
    expect(swatches).toHaveLength(4);
  });

  it("shows risk icons", () => {
    render(<MapLegend />);
    // Each level has an icon character rendered
    const { container } = render(<MapLegend />);
    const iconSpans = container.querySelectorAll("span[aria-hidden='true']");
    expect(iconSpans.length).toBeGreaterThanOrEqual(4);
  });
});
