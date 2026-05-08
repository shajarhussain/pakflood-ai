"use client";

import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { MissionHeader } from "@/components/layout/MissionHeader";
import { SafetyDisclaimer } from "@/components/layout/SafetyDisclaimer";
import { CleanLayerSwitcher, type LayerMode } from "@/components/map/CleanLayerSwitcher";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { FloodTimeline } from "@/components/timeline/FloodTimeline";
import { MOCK_FLOOD_EVENTS, RISK_BY_ID, buildMockExplanation } from "@/data/mock";
import type { MockRiskEntry, MockFloodEvent } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import { fetchExplanation, fetchFloodEvents, type ApiLocationResult } from "@/lib/api";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";
import type { MapHandle } from "@/components/map/MapDashboard";

const WindyPakistanMap = dynamic(
  () => import("./WindyPakistanMap"),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#080E1A",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 20,
              fontWeight: 900,
              color: "#fff",
              background: "linear-gradient(135deg, #22D3EE, #3B82F6)",
              boxShadow: "0 0 20px rgba(34,211,238,0.4)",
            }}
          >
            ⬡
          </div>
          <p style={{ color: "#22D3EE", fontSize: 13, animation: "pulse 1.5s infinite" }}>
            Loading Command Map…
          </p>
        </div>
      </div>
    ),
  }
);

const MODE_BADGE: Record<LayerMode, { text: string; color: string }> = {
  risk:     { text: "Grid Risk ON",  color: "#EF4444" },
  rainfall: { text: "Rainfall ON",   color: "#22D3EE" },
  wind:     { text: "Wind ON",       color: "#7DD3FC" },
  weather:  { text: "Weather ON",    color: "#FCD34D" },
  sar:      { text: "SAR ON",        color: "#A78BFA" },
  history:  { text: "History ON",    color: "#F59E0B" },
};

export default function CleanCommandCenter() {
  const [mode, setMode] = useState<LayerMode>("risk");
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null);
  const [selectedGridCell,   setSelectedGridCell]   = useState<GridCell | null>(null);
  const [selectedCity,       setSelectedCity]       = useState<CityWeather | null>(null);
  const [activeYear,  setActiveYear]  = useState<number | null>(null);
  const [floodEvents, setFloodEvents] = useState<MockFloodEvent[]>(MOCK_FLOOD_EVENTS);
  const [panelClosed, setPanelClosed] = useState(false);
  const mapRef = useRef<MapHandle | null>(null);

  useEffect(() => {
    fetchFloodEvents().then((apiEvents) => {
      if (apiEvents.length > 0) {
        setFloodEvents(
          apiEvents.map((e) => ({ ...e, damage_usd_billion: e.damage_usd_billion ?? undefined }))
        );
      }
    });
  }, []);

  const affectedDistrictNames = useMemo<string[]>(() => {
    if (!activeYear) return [];
    return floodEvents.find((e) => e.year === activeYear)?.affected_districts ?? [];
  }, [activeYear, floodEvents]);

  const selectedDistrict: MockRiskEntry | null = selectedDistrictId
    ? (RISK_BY_ID.get(selectedDistrictId) ?? null)
    : null;

  const [liveExplanation,   setLiveExplanation]   = useState<RiskExplanation | null>(null);
  const [liveExplanationId, setLiveExplanationId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedDistrictId) return;
    fetchExplanation(selectedDistrictId).then((live) => {
      if (live) { setLiveExplanation(live); setLiveExplanationId(selectedDistrictId); }
    });
  }, [selectedDistrictId]);

  const selectedExplanation: RiskExplanation | null = (() => {
    if (!selectedDistrict) return null;
    if (liveExplanation && liveExplanationId === selectedDistrictId) return liveExplanation;
    return buildMockExplanation(selectedDistrict);
  })();

  const handleDistrictClick = useCallback((id: string) => {
    setSelectedDistrictId((prev) => (prev === id ? null : id));
    setSelectedGridCell(null);
    setSelectedCity(null);
  }, []);

  const handleGridCellClick = useCallback((cell: GridCell) => {
    setSelectedGridCell((prev) => (prev?.id === cell.id ? null : cell));
    setSelectedDistrictId(null);
    setSelectedCity(null);
  }, []);

  const handleCityClick = useCallback((city: CityWeather) => {
    setSelectedCity((prev) => (prev?.name === city.name ? null : city));
    setSelectedGridCell(null);
    setMode("weather");
  }, []);

  const handleDistrictSearch = useCallback((result: ApiLocationResult) => {
    setSelectedDistrictId(result.district_id);
    setSelectedGridCell(null);
    setSelectedCity(null);
    mapRef.current?.flyTo(result.center[0], result.center[1], 9);
  }, []);

  const handleClose = useCallback(() => {
    setSelectedDistrictId(null);
    setSelectedGridCell(null);
    setSelectedCity(null);
    setPanelClosed(true);
  }, []);

  const hasSelection = !!(selectedDistrictId || selectedGridCell || selectedCity);
  const showPanel = !panelClosed || hasSelection;
  const badge = MODE_BADGE[mode];

  return (
    <div
      style={{
        position: "relative",
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        background: "#080E1A",
      }}
    >
      {/* Full-viewport map */}
      <div style={{ position: "absolute", inset: 0, zIndex: 1 }}>
        <WindyPakistanMap
          mapRef={mapRef}
          mode={mode}
          riskData={RISK_BY_ID}
          selectedDistrictId={selectedDistrictId}
          onDistrictClick={handleDistrictClick}
          affectedDistrictNames={affectedDistrictNames}
          onGridCellClick={handleGridCellClick}
          selectedGridCellId={selectedGridCell?.id ?? null}
          onCityClick={handleCityClick}
          selectedCityName={selectedCity?.name ?? null}
        />
      </div>

      {/* Floating header */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, zIndex: 600 }}>
        <MissionHeader
          riskData={RISK_BY_ID}
          onDistrictSelect={handleDistrictSearch}
          onCitySearch={handleCityClick}
        />
      </div>

      {/* Left: mode switcher — self-positions via position:absolute inside */}
      <CleanLayerSwitcher mode={mode} onChange={setMode} />

      {/* Active mode status badge — used by Playwright for layer-state assertions */}
      <div
        aria-label="Active layers status"
        style={{
          position: "absolute",
          left: 65,
          bottom: 130,
          zIndex: 600,
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          background: "rgba(13,19,35,0.82)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
          border: "1px solid rgba(255,255,255,0.09)",
          borderRadius: 20,
          padding: "4px 10px 4px 8px",
          fontSize: 11,
          fontWeight: 600,
          color: badge.color,
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: badge.color,
            display: "inline-block",
            flexShrink: 0,
            boxShadow: `0 0 4px ${badge.color}`,
          }}
        />
        {badge.text}
      </div>

      {/* Right: Copilot drawer — slides in when something is selected */}
      <div
        style={{
          position: "absolute",
          top: 52,
          right: 0,
          bottom: 104,
          width: 370,
          zIndex: 700,
          display: "flex",
          flexDirection: "column",
          transform: showPanel ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
        }}
      >
        <CopilotPanel
          district={selectedDistrict}
          explanation={selectedExplanation}
          selectedGridCell={selectedGridCell}
          selectedCity={selectedCity}
          onClose={handleClose}
        />
      </div>

      {/* Bottom: flood event timeline + safety disclaimer */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 500,
          background: "#080E1A",
        }}
      >
        <FloodTimeline
          events={floodEvents}
          activeYear={activeYear}
          onYearSelect={(yr) => setActiveYear((prev) => (prev === yr ? null : yr))}
        />
        <SafetyDisclaimer />
      </div>
    </div>
  );
}
