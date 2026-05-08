import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FloodTimeline } from "@/components/timeline/FloodTimeline";
import { MOCK_FLOOD_EVENTS } from "@/data/mock";

describe("FloodTimeline", () => {
  it("renders all four historical event years", () => {
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={null} onYearSelect={() => {}} />
    );
    expect(screen.getByLabelText(/Select 2010 flood event/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Select 2011 flood event/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Select 2014 flood event/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Select 2022 flood event/i)).toBeInTheDocument();
  });

  it("calls onYearSelect when a year button is clicked", () => {
    const onYearSelect = vi.fn();
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={null} onYearSelect={onYearSelect} />
    );
    fireEvent.click(screen.getByLabelText(/Select 2022 flood event/i));
    expect(onYearSelect).toHaveBeenCalledWith(2022);
  });

  it("shows active event detail strip when a year is selected", () => {
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={2022} onYearSelect={() => {}} />
    );
    // Event title is unique
    expect(screen.getByText(/2022 Catastrophic Floods/i)).toBeInTheDocument();
    // The detail strip also shows the clear button (proves the strip rendered)
    expect(screen.getByLabelText(/Clear year filter/i)).toBeInTheDocument();
    // Damage figure appears at least once
    expect(screen.getAllByText(/14\.9/i).length).toBeGreaterThanOrEqual(1);
  });

  it("shows clear button when a year is active", () => {
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={2010} onYearSelect={() => {}} />
    );
    expect(screen.getByLabelText(/Clear year filter/i)).toBeInTheDocument();
  });

  it("does not show detail strip when no year selected", () => {
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={null} onYearSelect={() => {}} />
    );
    expect(screen.queryByText(/Catastrophic Floods/i)).not.toBeInTheDocument();
  });

  it("marks selected year button as pressed", () => {
    render(
      <FloodTimeline events={MOCK_FLOOD_EVENTS} activeYear={2010} onYearSelect={() => {}} />
    );
    const btn = screen.getByLabelText(/Select 2010 flood event/i);
    expect(btn).toHaveAttribute("aria-pressed", "true");
  });
});
