"use client";

export function SafetyDisclaimer() {
  return (
    <div
      role="alert"
      aria-label="Safety disclaimer"
      className="w-full flex items-center justify-center gap-2 px-4 text-center shrink-0"
      style={{
        height: 26,
        background: "rgba(245,158,11,0.07)",
        borderTop: "1px solid rgba(245,158,11,0.18)",
        color: "#B45309",
        fontSize: 10,
        fontWeight: 500,
      }}
    >
      <span style={{ color: "#F59E0B" }}>⚠</span>
      <span>
        Educational prototype — not an authoritative emergency alert. Always follow{" "}
        <strong style={{ color: "#FCD34D", fontWeight: 700 }}>PMD · FFD · NDMA · PDMA</strong>{" "}
        for real emergency decisions.
      </span>
    </div>
  );
}
