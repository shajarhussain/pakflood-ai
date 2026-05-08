"use client";

import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import { MissionHeader } from "@/components/layout/MissionHeader";
import { StatusBar } from "@/components/layout/StatusBar";
import { SafetyDisclaimer } from "@/components/layout/SafetyDisclaimer";
import { LayerRail } from "@/components/map/LayerRail";
import { KPICards } from "@/components/map/KPICards";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { FloodTimeline } from "@/components/timeline/FloodTimeline";
import { MOCK_FLOOD_EVENTS, RISK_BY_ID, buildMockExplanation } from "@/data/mock";
import type { MockRiskEntry, MockFloodEvent } from "@/data/mock";
import type { RiskExplanation } from "@/lib/types";
import { fetchExplanation, fetchFloodEvents, type ApiLocationResult } from "@/lib/api";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";

const PakistanMap = dynamic(() => import("./PakistanMap"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center" style={{ background: "#080E1A" }}>
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-xl font-black text-white"
          style={{ background: "linear-gradient(135deg, #22D3EE, #3B82F6)", boxShadow: "0 0 20px rgba(34,211,238,0.4)" }}
        >
          ⬡
        </div>
        <p className="text-sm animate-pulse" style={{ color: "#22D3EE" }}>Loading Command Map…</p>
      </div>
    </div>
  ),
});

export interface LayerVisibility {
  risk:         boolean;
  boundaries:   boolean;
  rainfall:     boolean;
  grid:         boolean;
  wind:         boolean;
  cityLabels:   boolean;
  sarReference: boolean;
}

export interface MapHandle {
  flyTo: (lat: number, lng: number, zoom?: number) => void;
}

export default function MapDashboard() {
  const [selectedDistrictId, setSelectedDistrictId] = useState<string | null>(null);
  const [selectedGridCell,   setSelectedGridCell]   = useState<GridCell | null>(null);
  const [selectedCity,       setSelectedCity]       = useState<CityWeather | null>(null);
  const [activeYear,  setActiveYear]  = useState<number | null>(null);
  const [layers, setLayers] = useState<LayerVisibility>({
    risk: true, boundaries: true, rainfall: false,
    grid: true, wind: false, cityLabels: true, sarReference: false,
  });
  const [floodEvents, setFloodEvents] = useState<MockFloodEvent[]>(MOCK_FLOOD_EVENTS);
  const mapRef = useRef<MapHandle | null>(null);

  useEffect(() => {
    fetchFloodEvents().then((apiEvents) => {
      if (apiEvents.length > 0) {
        setFloodEvents(apiEvents.map((e) => ({ ...e, damage_usd_billion: e.damage_usd_billion ?? undefined })));
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
  }, []);

  const handleDistrictSearch = useCallback((result: ApiLocationResult) => {
    setSelectedDistrictId(result.district_id);
    setSelectedGridCell(null);
    setSelectedCity(null);
    mapRef.current?.flyTo(result.center[0], result.center[1], 9);
  }, []);

  const toggleLayer = useCallback((key: keyof LayerVisibility) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleClose = useCallback(() => {
    setSelectedDistrictId(null);
    setSelectedGridCell(null);
    setSelectedCity(null);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: "#080E1A" }}>
      <MissionHeader riskData={RISK_BY_ID} onDistrictSelect={handleDistrictSearch} onCitySearch={handleCityClick} />
      <StatusBar activeLayers={layers} />

      <div className="flex flex-1 overflow-hidden">
        <LayerRail layers={layers} onToggle={toggleLayer} />

        <div className="relative flex-1 min-w-0">
          <PakistanMap
            mapRef={mapRef}
            riskData={RISK_BY_ID}
            selectedDistrictId={selectedDistrictId}
            onDistrictClick={handleDistrictClick}
            activeYear={activeYear}
            affectedDistrictNames={affectedDistrictNames}
            layers={layers}
            onGridCellClick={handleGridCellClick}
            selectedGridCellId={selectedGridCell?.id ?? null}
            onCityClick={handleCityClick}
            selectedCityName={selectedCity?.name ?? null}
          />
          <KPICards riskData={RISK_BY_ID} selectedDistrict={selectedDistrict} />
        </div>

        <CopilotPanel
          district={selectedDistrict}
          explanation={selectedExplanation}
          selectedGridCell={selectedGridCell}
          selectedCity={selectedCity}
          onClose={handleClose}
        />
      </div>

      <FloodTimeline
        events={floodEvents}
        activeYear={activeYear}
        onYearSelect={(yr) => setActiveYear((prev) => (prev === yr ? null : yr))}
      />
      <SafetyDisclaimer />
    </div>
  );
}
