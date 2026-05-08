import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceBadge } from "@/components/layout/SourceBadge";

describe("SourceBadge", () => {
  it("renders source name", () => {
    render(<SourceBadge name="IMERG" status="fresh" />);
    expect(screen.getByText(/IMERG/)).toBeInTheDocument();
  });

  it("shows Fresh label for fresh status", () => {
    render(<SourceBadge name="IMERG" status="fresh" />);
    expect(screen.getByText(/Fresh/)).toBeInTheDocument();
  });

  it("shows Stale label for stale status", () => {
    render(<SourceBadge name="GloFAS" status="stale" />);
    expect(screen.getByText(/Stale/)).toBeInTheDocument();
  });

  it("shows Error label for error status", () => {
    render(<SourceBadge name="FFD" status="error" />);
    expect(screen.getByText(/Error/)).toBeInTheDocument();
  });

  it("shows Disabled label for disabled status", () => {
    render(<SourceBadge name="SAR" status="disabled" />);
    expect(screen.getByText(/Disabled/)).toBeInTheDocument();
  });
});
