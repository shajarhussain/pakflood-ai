"use client";

interface Props {
  showGrid: boolean;
  showWind: boolean;
  showCityLabels: boolean;
}

export function WeatherLayerLegend({ showGrid, showWind, showCityLabels }: Props) {
  if (!showGrid && !showWind && !showCityLabels) return null;

  return (
    <div
      className="absolute bottom-24 left-14 z-[500] pointer-events-none"
      style={{
        background: "rgba(13,21,38,0.88)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 10,
        padding: "8px 10px",
        backdropFilter: "blur(10px)",
        minWidth: 148,
      }}
    >
      <div className="text-[9px] font-bold uppercase tracking-widest mb-2" style={{ color: "#64748B" }}>
        Active Layers
      </div>

      {showGrid && (
        <div className="mb-2">
          <div className="text-[10px] font-semibold mb-1" style={{ color: "#94A3B8" }}>
            Grid Risk Zones
          </div>
          {[
            { level: "Severe",   color: "#EF4444" },
            { level: "High",     color: "#F97316" },
            { level: "Moderate", color: "#F59E0B" },
            { level: "Low",      color: "#22C55E" },
            { level: "Minimal",  color: "#475569" },
          ].map(({ level, color }) => (
            <div key={level} className="flex items-center gap-1.5 mb-0.5">
              <div style={{ width: 10, height: 10, background: color, opacity: 0.6, borderRadius: 2 }} />
              <span style={{ fontSize: 9, color: "#CBD5E1" }}>{level}</span>
            </div>
          ))}
        </div>
      )}

      {showWind && (
        <div className="mb-2">
          <div className="text-[10px] font-semibold mb-1" style={{ color: "#94A3B8" }}>
            Wind Vectors
          </div>
          <div className="flex items-center gap-1.5">
            <span style={{ color: "#22D3EE", fontSize: 11 }}>▲</span>
            <span style={{ fontSize: 9, color: "#CBD5E1" }}>IDW-interpolated demo</span>
          </div>
        </div>
      )}

      {showCityLabels && (
        <div>
          <div className="text-[10px] font-semibold mb-1" style={{ color: "#94A3B8" }}>
            City Weather
          </div>
          <div className="flex items-center gap-1.5">
            <span style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: "#22D3EE" }} />
            <span style={{ fontSize: 9, color: "#CBD5E1" }}>MVP district</span>
          </div>
          <div style={{ fontSize: 8, color: "#475569", marginTop: 3 }}>Demo monsoon values</div>
        </div>
      )}
    </div>
  );
}
