"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, MutableRefObject } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import type { FeatureCollection, Feature } from "geojson";
import type { PathOptions } from "leaflet";

import { CompactCityChips } from "./CompactCityChips";
import { WindVectorLayer } from "./WindVectorLayer";
import { RainCanvas } from "./RainCanvas";
import { RainfallStationLayer } from "./RainfallStationLayer";
import { MapLegend } from "./MapLegend";
import type { MockRiskEntry } from "@/data/mock";
import type { RiskLevel } from "@/lib/types";
import type { GridCell } from "@/lib/grid-risk";
import type { CityWeather } from "@/data/pakistan-cities-weather";
import type { LayerMode } from "./CleanLayerSwitcher";
import type { MapHandle } from "./MapDashboard";
import {
  PAKISTAN_CENTER, PAKISTAN_BOUNDS, PAKISTAN_MAX_BOUNDS,
  MAP_MIN_ZOOM, MAP_MAX_ZOOM, MAP_DEFAULT_ZOOM,
  PROVINCE_LABELS,
} from "@/data/pakistan-bounds";

import districtsData from "@/data/districts.json";
import provincesData from "@/data/provinces.json";

const DISTRICTS_GEOJSON = districtsData as unknown as FeatureCollection;
const PROVINCES_GEOJSON = provincesData as unknown as FeatureCollection;

// Voyager shows terrain, rivers, cities — much more geographic context than pure dark
const TILE_URL  = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

// Risk color lookup — used by markers (replaces solid polygon fills)
const RISK_FILL: Record<string, { fill: string; opacity: number; border: string; weight: number }> = {
  Severe:   { fill: "#FF0040", opacity: 0.78, border: "#FF0040", weight: 2.0 },
  High:     { fill: "#FF7700", opacity: 0.62, border: "#FF7700", weight: 1.4 },
  Moderate: { fill: "#FFE500", opacity: 0.46, border: "#FFE500", weight: 1.0 },
  Low:      { fill: "#00FF88", opacity: 0.28, border: "#00FF88", weight: 0.7 },
};

// Per-district highlight marker spec — replaces polygon fills
const HIGHLIGHT_SPEC: Record<RiskLevel, { core: number; halo: number; color: string; pulse: boolean }> = {
  Severe:   { core: 22, halo: 56, color: "#FF0040", pulse: true  },
  High:     { core: 18, halo: 42, color: "#FF7700", pulse: true  },
  Moderate: { core: 14, halo: 30, color: "#FFE500", pulse: false },
  Low:      { core: 11, halo: 22, color: "#00FF88", pulse: false },
};

// Province base layer — visible fills so all of Pakistan has a risk color
const PROVINCE_FILL: Record<string, { fill: string; fillOpacity: number; border: string }> = {
  Severe:   { fill: "#FF0040", fillOpacity: 0.38, border: "#FF0040" },
  High:     { fill: "#FF7700", fillOpacity: 0.30, border: "#FF7700" },
  Moderate: { fill: "#FFE500", fillOpacity: 0.24, border: "#FFE500" },
  Low:      { fill: "#00FF88", fillOpacity: 0.18, border: "#00FF88" },
};

interface Props {
  mapRef: MutableRefObject<MapHandle | null>;
  mode: LayerMode;
  riskData: Map<string, MockRiskEntry>;
  selectedDistrictId: string | null;
  onDistrictClick: (id: string) => void;
  affectedDistrictNames: string[];
  onGridCellClick?: (cell: GridCell) => void;
  selectedGridCellId?: string | null;
  onCityClick?: (city: CityWeather) => void;
  selectedCityName?: string | null;
  panelOpen?: boolean;
}

function featureStyle(
  feature: Feature | undefined,
  riskData: Map<string, MockRiskEntry>,
  selectedId: string | null,
  affectedNames: string[],
  _mode: LayerMode
): PathOptions {
  const id    = feature?.properties?.district_id as string | undefined;
  const name  = feature?.properties?.name as string | undefined;
  const entry = id ? riskData.get(id) : undefined;
  const level = (entry?.risk_level ?? "Low") as RiskLevel;

  const isSelected = id === selectedId;
  const isDimmed   = affectedNames.length > 0 && !affectedNames.includes(name ?? "");

  // Selected district: bright teal outline so user sees the area shape
  if (isSelected) {
    const rf = RISK_FILL[level] ?? RISK_FILL.Low;
    return {
      fillColor:   rf.fill,
      fillOpacity: 0.22,
      color:       "#00FFD1",
      weight:      2.6,
      opacity:     1,
      className:   "",
    };
  }

  // Dimmed (history mode, district not in active year): nearly hidden
  if (isDimmed) {
    return {
      fillColor: "#000000", fillOpacity: 0.001,
      color: "transparent", weight: 0, opacity: 0,
      className: "",
    };
  }

  // Default: invisible-but-clickable polygon — markers carry the visual weight
  return {
    fillColor:   "#000000",
    fillOpacity: 0.001,
    color:       "transparent",
    weight:      0,
    opacity:     0,
    className:   "",
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

function ProvinceBaseLayer() {
  return (
    <GeoJSON
      data={PROVINCES_GEOJSON}
      style={(feature) => {
        const level = (feature?.properties?.risk_level ?? "Low") as string;
        const pf = PROVINCE_FILL[level] ?? PROVINCE_FILL.Low;
        return {
          fillColor: pf.fill, fillOpacity: pf.fillOpacity,
          color: pf.border, weight: 1.5, opacity: 0.55,
          interactive: false,
        };
      }}
    />
  );
}

function polygonCentroid(coords: number[][]): [number, number] {
  let sumLng = 0, sumLat = 0;
  for (const [lng, lat] of coords) { sumLng += lng; sumLat += lat; }
  return [sumLat / coords.length, sumLng / coords.length];
}

interface DistrictHighlightLayerProps {
  riskData: Map<string, MockRiskEntry>;
  selectedId: string | null;
  onClick: (id: string) => void;
  affectedNames: string[];
}

function DistrictHighlightLayer({ riskData, selectedId, onClick, affectedNames }: DistrictHighlightLayerProps) {
  const map = useMap();

  useEffect(() => {
    const markers: L.Marker[] = [];

    DISTRICTS_GEOJSON.features.forEach((feature) => {
      const id = feature.properties?.district_id as string;
      const name = feature.properties?.name as string;
      const entry = riskData.get(id);
      if (!entry) return;
      if (affectedNames.length > 0 && !affectedNames.includes(name)) return;

      const geom = feature.geometry as { type: string; coordinates: number[][][] };
      if (geom.type !== "Polygon") return;
      const ring = geom.coordinates[0];
      const [cLat, cLng] = polygonCentroid(ring);

      const level = entry.risk_level as RiskLevel;
      const spec = HIGHLIGHT_SPEC[level] ?? HIGHLIGHT_SPEC.Low;
      const isSel = id === selectedId;
      const outline = isSel ? "#00FFD1" : "rgba(255,255,255,0.9)";
      const outlineW = isSel ? 2.5 : 1.8;

      const html = `
        <div style="
          position:relative;
          width:${spec.halo}px; height:${spec.halo}px;
          transform:translate(-50%,-50%);
          cursor:pointer;
        ">
          <div style="
            position:absolute; left:50%; top:50%;
            width:${spec.halo}px; height:${spec.halo}px;
            transform:translate(-50%,-50%);
            border-radius:50%;
            background:radial-gradient(circle, ${spec.color}55 0%, ${spec.color}00 70%);
            ${spec.pulse ? "animation: district-marker-pulse 1.8s ease-in-out infinite;" : ""}
            pointer-events:none;
          "></div>
          <div style="
            position:absolute; left:50%; top:50%;
            width:${spec.core}px; height:${spec.core}px;
            transform:translate(-50%,-50%) ${isSel ? "scale(1.18)" : "scale(1)"};
            border-radius:50%;
            background:${spec.color};
            border:${outlineW}px solid ${outline};
            box-shadow: 0 0 ${spec.core * 0.9}px ${spec.color}, 0 2px 6px rgba(0,0,0,0.55);
            transition: transform 0.2s ease;
          "></div>
        </div>
      `;

      const marker = L.marker([cLat, cLng], {
        icon: L.divIcon({
          html,
          className: "district-highlight-marker",
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
        interactive: true,
        keyboard: true,
        title: `${name} — ${entry.risk_level} risk`,
        zIndexOffset: 1000,
      });
      marker.on("click", () => onClick(id));
      marker.addTo(map);
      markers.push(marker);
    });

    return () => { markers.forEach((m) => m.remove()); };
  }, [map, riskData, selectedId, onClick, affectedNames]);

  return null;
}

function ProvinceLabels() {
  const map = useMap();
  useEffect(() => {
    const markers = PROVINCE_LABELS.map(({ name, lat, lng }) =>
      L.marker([lat, lng], {
        icon: L.divIcon({
          html: `<span style="
            color:rgba(0,255,209,0.70);
            font:700 10px/1 var(--font-geist-mono,monospace);
            text-transform:uppercase;
            letter-spacing:0.18em;
            text-shadow:0 1px 6px rgba(0,0,0,0.9), 0 0 12px rgba(0,255,209,0.4);
            white-space:nowrap;
            pointer-events:none;
            display:block;
          ">${name}</span>`,
          className: "",
          iconAnchor: [0, 6],
        }),
        interactive: false,
        zIndexOffset: -1000,
      })
    );
    markers.forEach((m) => m.addTo(map));
    return () => { markers.forEach((m) => m.remove()); };
  }, [map]);
  return null;
}

export default function WindyPakistanMap({
  mapRef, mode, riskData, selectedDistrictId, onDistrictClick,
  affectedDistrictNames, onGridCellClick: _onGridCellClick,
  selectedGridCellId: _selectedGridCellId,
  onCityClick, selectedCityName, panelOpen = false,
}: Props) {
  const highestRisk: RiskLevel = (() => {
    const entries = Array.from(riskData.values());
    if (entries.some((e) => e.risk_level === "Severe"))   return "Severe";
    if (entries.some((e) => e.risk_level === "High"))     return "High";
    if (entries.some((e) => e.risk_level === "Moderate")) return "Moderate";
    return "Low";
  })();

  const geoJsonKey = [
    selectedDistrictId ?? "none",
    affectedDistrictNames.join(",") || "all",
    mode,
  ].join("-");

  // Voyager is a light/medium tile — darken it so risk colors still pop on top
  const tileOpacity = mode === "rainfall" ? 0.40 : 0.62;

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", background: "#1A2035" }}>
      <MapContainer
        center={PAKISTAN_CENTER}
        zoom={MAP_DEFAULT_ZOOM}
        minZoom={MAP_MIN_ZOOM}
        maxZoom={MAP_MAX_ZOOM}
        maxBounds={PAKISTAN_MAX_BOUNDS}
        maxBoundsViscosity={0.90}
        bounds={PAKISTAN_BOUNDS}
        style={{ height: "100%", width: "100%", background: "#1A2035" }}
        zoomControl={true}
        attributionControl={true}
        aria-label="Pakistan flood risk map"
      >
        <MapController mapRef={mapRef} />
        <TileLayer url={TILE_URL} attribution={TILE_ATTR} opacity={tileOpacity} />

        {/* Province base fills — covers all of Pakistan so no black void */}
        <ProvinceBaseLayer />

        {/* Province ambient labels */}
        <ProvinceLabels />

        {/* District boundaries — choropleth only, no grid squares */}
        <GeoJSON
          key={geoJsonKey}
          data={DISTRICTS_GEOJSON}
          style={(feature) =>
            featureStyle(feature, riskData, selectedDistrictId, affectedDistrictNames, mode)
          }
          onEachFeature={(feature, layer) => {
            const id = feature.properties?.district_id as string;
            // Click-only: no tooltips, no hover info popups.
            layer.on("click", () => onDistrictClick(id));
          }}
        />

        {/* District highlight markers — clean radar-style pings instead of polygon fills */}
        <DistrictHighlightLayer
          riskData={riskData}
          selectedId={selectedDistrictId}
          onClick={onDistrictClick}
          affectedNames={affectedDistrictNames}
        />

        {/* Real station rainfall markers — visible only in rainfall mode */}
        <RainfallStationLayer visible={mode === "rainfall"} />

        {/* Wind vectors — only in wind mode */}
        <WindVectorLayer visible={mode === "wind"} />

        {/* City chips — weather + rainfall modes */}
        <CompactCityChips
          visible={mode === "weather" || mode === "rainfall"}
          onCityClick={onCityClick}
          selectedCityName={selectedCityName}
        />
      </MapContainer>

      {/* Vignette — dims surrounding countries, Pakistan pops */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          zIndex: 400,
          background:
            "radial-gradient(ellipse 62% 68% at 52% 46%, transparent 0%, rgba(10,15,30,0.72) 100%)",
        }}
      />

      {/* Vivid rainfall overlay — blue-teal tones */}
      {mode === "rainfall" && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            zIndex: 450,
            background:
              "linear-gradient(160deg, rgba(0,212,255,0.20) 0%, rgba(0,100,200,0.16) 55%, rgba(100,50,255,0.10) 100%)",
          }}
        />
      )}

      {/* SAR overlay — purple tint */}
      {mode === "sar" && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            zIndex: 450,
            background: "rgba(155,89,255,0.10)",
          }}
        />
      )}

      {/* Rain canvas + card */}
      <RainCanvas active={mode === "rainfall"} riskLevel={highestRisk} panelOpen={panelOpen} />

      {/* Risk legend — only in risk mode */}
      {mode === "risk" && <MapLegend showGrid={false} panelOpen={panelOpen} />}
    </div>
  );
}
