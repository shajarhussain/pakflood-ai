import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LayerControlPanel } from "@/components/panels/LayerControlPanel";
import type { LayerVisibility } from "@/components/map/MapDashboard";

const defaultLayers: LayerVisibility = {
  risk: true,
  boundaries: true,
  rainfall: false,
  grid: false,
  wind: false,
  cityLabels: false,
  sarReference: false,
};

describe("LayerControlPanel", () => {
  it("renders layer labels", () => {
    render(<LayerControlPanel layers={defaultLayers} onToggle={() => {}} />);
    expect(screen.getByText("Risk Layer")).toBeInTheDocument();
    expect(screen.getByText("Boundaries")).toBeInTheDocument();
    expect(screen.getByText("Rainfall")).toBeInTheDocument();
    expect(screen.getByText("Satellite SAR")).toBeInTheDocument();
  });

  it("calls onToggle when an available layer is clicked", () => {
    const onToggle = vi.fn();
    render(<LayerControlPanel layers={defaultLayers} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText(/Toggle Risk Layer/i));
    expect(onToggle).toHaveBeenCalledWith("risk");
  });

  it("does not call onToggle for unavailable layers", () => {
    const onToggle = vi.fn();
    render(<LayerControlPanel layers={defaultLayers} onToggle={onToggle} />);
    fireEvent.click(screen.getByLabelText(/Toggle Rainfall layer/i));
    expect(onToggle).not.toHaveBeenCalled();
  });

  it("marks active layers as pressed", () => {
    render(<LayerControlPanel layers={defaultLayers} onToggle={() => {}} />);
    const riskBtn = screen.getByLabelText(/Toggle Risk Layer/i);
    expect(riskBtn).toHaveAttribute("aria-pressed", "true");
  });
});
