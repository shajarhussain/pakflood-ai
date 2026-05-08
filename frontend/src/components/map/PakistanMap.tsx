"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, MutableRefObject } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import type { FeatureCollection, Feature } from "geojson";
import type { PathOptions } from "leaflet";

import { MapLegend } from "./MapLegend";
import { RainCanvas } from "./RainCanvas";
import { GridRiskLayer } from "./GridRiskLayer";
import { WindVectorLayer } from "./WindVectorLayer";
import { CityWeatherLabels } from "./CityWeatherLabels";
import { WeatherLayerLegend } from "./WeatherLayerLegend";
import { riskColor } from "@/lib/risk-colors";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskLevel } from "@/lib/types";
import type { LayerVisibility, MapHandle } from "./MapDashboard";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";
import {
  PAKISTAN_CENTER,
  PAKISTAN_BOUNDS,
  PAKISTAN_MAX_BOUNDS,
  MAP_MIN_ZOOM,
  MAP_MAX_ZOOM,
  MAP_DEFAULT_ZOOM,
} from "@/data/pakistan-bounds";

import districtsData from "@/data/districts.json";

const DISTRICTS_GEOJSON = districtsData as unknown as FeatureCollection;

const TILE_URL  = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

interface Props {
  mapRef: MutableRefObject<MapHandle | null>;
  riskData: Map<string, MockRiskEntry>;
  selectedDistrictId: string | null;
  onDistrictClick: (id: string) => void;
  activeYear: number | null;
  affectedDistrictNames: string[];
  layers: LayerVisibility;
  onGridCellClick?: (cell: GridCell) => void;
  selectedGridCellId?: string | null;
  onCityClick?: (city: CityWeather) => void;
  selectedCityName?: string | null;
}


function featureStyle(
  feature: Feature | undefined,
  riskData: Map<string, MockRiskEntry>,
  selectedId: string | null,
  affectedNames: string[],
  layers: LayerVisibility
): PathOptions {
  const id    = feature?.properties?.district_id as string | undefined;
  const name  = feature?.properties?.name as string | undefined;
  const entry = id ? riskData.get(id) : undefined;
  const level = (entry?.risk_level ?? "Low") as RiskLevel;

  const isSelected = id === selectedId;
  const isDimmed   = affectedNames.length > 0 && !affectedNames.includes(name ?? "");
  const baseColor  = layers.risk ? riskColor(level) : "#334155";

  return {
    fillColor:   baseColor,
    fillOpacity: isDimmed ? 0.05 : isSelected ? 0.85 : layers.risk ? 0.55 : 0.18,
    color:       isSelected ? "#22D3EE" : isDimmed ? "#1E293B" : "rgba(255,255,255,0.14)",
    weight:      isSelected ? 2.5 : isDimmed ? 0.5 : 0.9,
    opacity:     isDimmed ? 0.3 : 1,
  };
}

function MapController({ mapRef }: { mapRef: MutableRefObject<MapHandle | null> }) {
  const map = useMap();
  useEffect(() => {
    mapRef.current = {
      flyTo: (lat, lng, zoom = 9) => map.flyTo([lat, lng], zoom, { duration: 1.2 }),
    };
    return () => { mapRef.current = null; };
  }, [map, mapRef]);
  return null;
}

export default function PakistanMap({
  mapRef, riskData, selectedDistrictId, onDistrictClick,
  affectedDistrictNames, layers, onGridCellClick, selectedGridCellId,
  onCityClick, selectedCityName,
}: Props) {
  const geoJsonKey = [
    selectedDistrictId ?? "none",
    affectedDistrictNames.join(",") || "all",
    layers.risk ? "r" : "nr",
    layers.boundaries ? "b" : "nb",
  ].join("-");

  const showDistrictLayer = layers.boundaries || layers.risk;

  const highestRisk: RiskLevel = (() => {
    const entries = Array.from(riskData.values());
    if (entries.some((e) => e.risk_level === "Severe"))   return "Severe";
    if (entries.some((e) => e.risk_level === "High"))     return "High";
    if (entries.some((e) => e.risk_level === "Moderate")) return "Moderate";
    return "Low";
  })();

  return (
    <div className="relative h-full w-full" style={{ background: "#080E1A" }}>
      <MapContainer
        center={PAKISTAN_CENTER}
        zoom={MAP_DEFAULT_ZOOM}
        minZoom={MAP_MIN_ZOOM}
        maxZoom={MAP_MAX_ZOOM}
        maxBounds={PAKISTAN_MAX_BOUNDS}
        maxBoundsViscosity={0.9}
        bounds={PAKISTAN_BOUNDS}
        style={{ height: "100%", width: "100%", background: "#080E1A" }}
        zoomControl={true}
        attributionControl={true}
        aria-label="Pakistan flood risk map"
      >
        <MapController mapRef={mapRef} />
        <TileLayer url={TILE_URL} attribution={TILE_ATTR} />

        {/* Grid risk zones — below district boundaries */}
        <GridRiskLayer
          visible={layers.grid}
          onCellClick={onGridCellClick}
          selectedCellId={selectedGridCellId ?? null}
        />

        {/* District boundaries */}
        {showDistrictLayer && (
          <GeoJSON
            key={geoJsonKey}
            data={DISTRICTS_GEOJSON}
            style={(feature) =>
              featureStyle(feature, riskData, selectedDistrictId, affectedDistrictNames, layers)
            }
            onEachFeature={(feature, layer) => {
              const id      = feature.properties?.district_id as string;
              const name    = feature.properties?.name as string;
              const province= feature.properties?.province as string;
              const entry   = riskData.get(id);

              if (entry) {
                const lvl  = entry.risk_level.toLowerCase();
                const conf = (entry.confidence * 100).toFixed(0);
                const score= (entry.risk_score * 100).toFixed(0);

                layer.bindTooltip(
                  `<div class="pakflood-tooltip">
                    <div class="pakflood-tooltip-title">${name}</div>
                    <div class="pakflood-tooltip-province">${province}</div>
                    <div class="pakflood-tooltip-row">
                      <span>Risk</span>
                      <span class="pakflood-risk-${lvl}">${entry.risk_level}</span>
                    </div>
                    <div class="pakflood-tooltip-row">
                      <span>Score</span><span>${score}%</span>
                    </div>
                    <div class="pakflood-tooltip-row">
                      <span>Confidence</span><span>${conf}%</span>
                    </div>
                    <div class="pakflood-tooltip-row" style="margin-top:6px;font-size:10px;color:#64748b">
                      <span>${entry.top_factors[0] ?? "—"}</span>
                    </div>
                    <div class="pakflood-tooltip-hint">Click for AI analysis →</div>
                  </div>`,
                  { sticky: true, direction: "top", offset: [0, -6], className: "pakflood-tooltip-container" }
                );
              }

              layer.on("mouseover", (e) => {
                const isSel = id === selectedDistrictId;
                e.target.setStyle({
                  weight: isSel ? 2.5 : 2,
                  color: isSel ? "#22D3EE" : "rgba(255,255,255,0.40)",
                  fillOpacity: 0.80,
                });
              });
              layer.on("mouseout", (e) => {
                e.target.setStyle(featureStyle(feature, riskData, selectedDistrictId, affectedDistrictNames, layers));
              });
              layer.on("click", () => onDistrictClick(id));
            }}
          />
        )}

        {/* Wind vectors */}
        <WindVectorLayer visible={layers.wind} />

        {/* City weather labels */}
        <CityWeatherLabels
          visible={layers.cityLabels}
          onCityClick={onCityClick}
          selectedCityName={selectedCityName ?? null}
        />
      </MapContainer>

      {/* Rainfall canvas overlay — blue tint + particles */}
      <RainCanvas active={layers.rainfall} riskLevel={highestRisk} />

      {/* Layer legends */}
      <WeatherLayerLegend
        showGrid={layers.grid}
        showWind={layers.wind}
        showCityLabels={layers.cityLabels}
      />
      <MapLegend showGrid={layers.grid} />
    </div>
  );
}
