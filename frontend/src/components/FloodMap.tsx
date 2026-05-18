"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, Marker, LayerGroup } from "leaflet";
import type { FeatureCollection, Polygon, MultiPolygon } from "geojson";
import {
  PAKISTAN_CENTER,
  PAKISTAN_BOUNDS,
  PAKISTAN_MAX_BOUNDS,
  MAP_DEFAULT_ZOOM,
  MAP_MIN_ZOOM,
  MAP_MAX_ZOOM,
} from "@/data/pakistan-bounds";
import type { ZonesGeoJSON, FloodEvent } from "@/lib/types";
import { fetchBoundaries } from "@/lib/api";

// ── Point-in-Pakistan check (ray-casting) ────────────────────────────────────
// Returns true if (lat, lng) falls inside any district polygon in the boundaries
// FeatureCollection. Falls back to true when boundaries haven't loaded yet so
// that the bounding-box pre-filter is the only guard during initial load.

function _pointInRing(lat: number, lng: number, ring: number[][] | undefined): boolean {
  if (!ring || ring.length === 0) return false;
  let inside = false;
  const n = ring.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = ring[i][0], yi = ring[i][1]; // GeoJSON order: [lng, lat]
    const xj = ring[j][0], yj = ring[j][1];
    if ((yi > lat) !== (yj > lat)) {
      if (lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
        inside = !inside;
      }
    }
  }
  return inside;
}

function isInsidePakistan(
  lat: number,
  lng: number,
  boundaries: FeatureCollection | null
): boolean {
  if (!boundaries) return true; // not loaded yet — allow, bbox already restricts roughly
  for (const feature of boundaries.features) {
    if (!feature.geometry) continue;
    const geom = feature.geometry as Polygon | MultiPolygon;
    if (geom.type === "Polygon") {
      const ring = (geom.coordinates?.[0] as unknown) as number[][] | undefined;
      if (_pointInRing(lat, lng, ring)) return true;
    } else if (geom.type === "MultiPolygon") {
      for (const poly of (geom.coordinates as unknown) as number[][][][] | undefined ?? []) {
        if (_pointInRing(lat, lng, poly?.[0])) return true;
      }
    }
  }
  return false;
}

// ── Event year colours ───────────────────────────────────────────────────────

const EVENT_YEAR_COLORS: Record<number, string> = {
  2022: "#ef4444",
  2010: "#f97316",
  2011: "#eab308",
  2014: "#22c55e",
};

// ── Zone colours ─────────────────────────────────────────────────────────────

const ZONE_COLORS: Record<string, string> = {
  Severe:   "#ef4444",
  High:     "#f97316",
  Moderate: "#eab308",
  Low:      "#22c55e",
  Unknown:  "#475569",
};

// ── District risk aggregation ────────────────────────────────────────────────
// Spatially joins zone points to district polygons (ray-casting) and returns
// the dominant (highest-priority) risk per district.

const _RISK_PRIORITY: Record<string, number> = { Severe: 4, High: 3, Moderate: 2, Low: 1 };

interface DistrictRiskData { risk: string; maxProb: number; count: number }

function computeDistrictRisk(
  zones: ZonesGeoJSON,
  boundaries: FeatureCollection
): Map<string, DistrictRiskData> {
  const result = new Map<string, DistrictRiskData>();

  for (const f of zones.features) {
    const [lng, lat] = f.geometry.coordinates;
    const { risk_level, flood_prob } = f.properties;
    const prob = flood_prob ?? 0;

    for (const boundary of boundaries.features) {
      if (!boundary.geometry) continue;
      const name = boundary.properties?.name as string | undefined;
      if (!name) continue;
      const geom = boundary.geometry as Polygon | MultiPolygon;

      let inside = false;
      if (geom.type === "Polygon") {
        inside = _pointInRing(lat, lng, (geom.coordinates[0] as unknown) as number[][] | undefined);
      } else if (geom.type === "MultiPolygon") {
        for (const poly of (geom.coordinates as unknown) as number[][][][] | undefined ?? []) {
          if (_pointInRing(lat, lng, poly?.[0])) { inside = true; break; }
        }
      }

      if (inside) {
        const cur = result.get(name);
        if (!cur) {
          result.set(name, { risk: risk_level, maxProb: prob, count: 1 });
        } else {
          if ((_RISK_PRIORITY[risk_level] ?? 0) > (_RISK_PRIORITY[cur.risk] ?? 0)) cur.risk = risk_level;
          if (prob > cur.maxProb) cur.maxProb = prob;
          cur.count++;
        }
        break; // a point belongs to exactly one district
      }
    }
  }

  return result;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  selectedLocation: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
  zones?: ZonesGeoJSON | null;
  showZones?: boolean;
  showZonePolygons?: boolean;
  riskFilter?: string | null;
  selectedEvent?: FloodEvent | null;
}

export default function FloodMap({ selectedLocation, onLocationSelect, zones, showZones, showZonePolygons, riskFilter, selectedEvent }: Props) {
  const containerRef        = useRef<HTMLDivElement>(null);
  const mapRef              = useRef<LeafletMap | null>(null);
  const markerRef           = useRef<Marker | null>(null);
  const zonesGroupRef       = useRef<LayerGroup | null>(null);
  const zonePolygonsGroupRef = useRef<LayerGroup | null>(null);
  const eventLayerRef       = useRef<LayerGroup | null>(null);
  const boundariesRef       = useRef<FeatureCollection | null>(null);
  const [mapReady,        setMapReady       ] = useState(false);
  const [boundariesReady, setBoundariesReady] = useState(false);

  // ── Initialize map + fetch real boundaries ─────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let destroyed = false;

    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      if (destroyed || !containerRef.current) return;

      const map = L.map(containerRef.current, {
        center:             PAKISTAN_CENTER,
        zoom:               MAP_DEFAULT_ZOOM,
        minZoom:            MAP_MIN_ZOOM,
        maxZoom:            MAP_MAX_ZOOM,
        maxBounds:          PAKISTAN_MAX_BOUNDS,
        maxBoundsViscosity: 0.8,
        zoomControl:        true,
      });

      if (destroyed) { map.remove(); return; }

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap contributors',
        subdomains: "abcd",
        maxZoom: 19,
      }).addTo(map);

      // Bounding-box pre-filter for clicks (fast; exact filter uses isInsidePakistan)
      const bbox = PAKISTAN_BOUNDS;
      map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        if (lat < bbox[0][0] || lat > bbox[1][0] || lng < bbox[0][1] || lng > bbox[1][1]) return;
        if (!isInsidePakistan(lat, lng, boundariesRef.current)) return;
        onLocationSelect(lat, lng);
      });

      mapRef.current = map;
      setMapReady(true);

      // Fetch district boundaries — non-blocking, renders after map is usable
      const geojson = await fetchBoundaries() as FeatureCollection | null;
      if (destroyed || !geojson) return;

      boundariesRef.current = geojson;

      L.geoJSON(geojson, {
        style: () => ({
          color:       "rgba(34,211,238,0.30)",
          weight:      0.7,
          fillColor:   "rgba(34,211,238,0.03)",
          fillOpacity: 1,
          interactive: false,
        }),
        interactive: false,
      }).addTo(map);

      setBoundariesReady(true); // triggers zone re-render with Pakistan filter applied
    })();

    return () => {
      destroyed = true;
      mapRef.current?.remove();
      mapRef.current = null;
      zonesGroupRef.current = null;
      zonePolygonsGroupRef.current = null;
      eventLayerRef.current = null;
      boundariesRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Zone heatmap — filtered to Pakistan ───────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;

      if (zonesGroupRef.current) zonesGroupRef.current.clearLayers();
      if (!showZones || !zones?.features?.length) return;

      if (!zonesGroupRef.current) {
        zonesGroupRef.current = L.layerGroup().addTo(mapRef.current!);
      }

      const boundaries = boundariesRef.current; // may be null if still loading

      for (const feature of zones.features) {
        const [lng, lat] = feature.geometry.coordinates;

        // Skip grid points outside Pakistan's actual polygon boundary
        if (!isInsidePakistan(lat, lng, boundaries)) continue;

        const { flood_prob, risk_level, confidence, top_factors } = feature.properties;
        const color      = ZONE_COLORS[risk_level] ?? "#475569";
        const dimmed     = !!riskFilter && risk_level !== riskFilter;
        const opacity    = dimmed ? 0.05 : Math.max(0.25, (flood_prob ?? 0) * 0.92);
        const radius     = dimmed ? 9 : (riskFilter ? 17 : 14);
        const pct        = Math.round((flood_prob  ?? 0) * 100);
        const confPct    = Math.round((confidence  ?? 0) * 100);
        const topName    = top_factors?.[0]?.name ?? "—";

        L.circleMarker([lat, lng], {
          radius,
          color:       !dimmed && riskFilter ? color : "transparent",
          weight:      !dimmed && riskFilter ? 1.5   : 0,
          fillColor:   color,
          fillOpacity: opacity,
          interactive: !dimmed,
        })
          .on("click", (e) => { (e.originalEvent as Event).stopPropagation(); })
          .bindPopup(
            `<div style="font-family:system-ui,sans-serif;font-size:12px;min-width:150px">
              <div style="font-weight:700;color:${color};margin-bottom:5px;font-size:13px">${risk_level} Risk</div>
              <div style="color:#94a3b8;margin-bottom:2px">Flood prob: <b style="color:#e2e8f0">${pct}%</b></div>
              <div style="color:#94a3b8;margin-bottom:2px">Confidence: <b style="color:#e2e8f0">${confPct}%</b></div>
              <div style="color:#94a3b8">Top driver: <b style="color:#e2e8f0">${topName}</b></div>
              <div style="margin-top:6px;color:#475569;font-size:10px">${lat.toFixed(2)}°N ${lng.toFixed(2)}°E</div>
            </div>`
          )
          .addTo(zonesGroupRef.current!);
      }
    })();
    // boundariesReady is a dep so zones re-render once boundaries finish loading
  }, [zones, showZones, riskFilter, mapReady, boundariesReady]);

  // ── Zone choropleth — district polygons coloured by dominant risk ─────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;

      if (zonePolygonsGroupRef.current) zonePolygonsGroupRef.current.clearLayers();
      if (!showZonePolygons || !zones?.features?.length || !boundariesRef.current) return;

      if (!zonePolygonsGroupRef.current) {
        zonePolygonsGroupRef.current = L.layerGroup().addTo(mapRef.current!);
      }

      const districtRisk = computeDistrictRisk(zones, boundariesRef.current);

      for (const boundary of boundariesRef.current.features) {
        if (!boundary.geometry) continue;
        const name     = boundary.properties?.name     as string | undefined;
        const province = boundary.properties?.province as string | undefined;
        if (!name) continue;

        const data   = districtRisk.get(name);
        const risk   = data?.risk   ?? "Unknown";
        const color  = ZONE_COLORS[risk] ?? ZONE_COLORS["Unknown"];
        const dimmed = !!riskFilter && risk !== riskFilter;
        const pct    = data ? Math.round(data.maxProb * 100) : null;

        L.geoJSON(boundary as never, {
          style: () => ({
            color:       dimmed ? "#334155" : color,
            weight:      dimmed ? 0.5 : 2,
            fillColor:   color,
            fillOpacity: dimmed ? 0.04 : (data ? 0.35 : 0.07),
            opacity:     dimmed ? 0.3  : 0.9,
          }),
          interactive: !!data && !dimmed,
        })
          .bindPopup(
            data
              ? `<div style="font-family:system-ui,sans-serif;font-size:12px;min-width:170px">
                  <div style="font-weight:700;font-size:14px;color:#e2e8f0;margin-bottom:1px">${name}</div>
                  <div style="color:#64748b;font-size:11px;margin-bottom:8px">${province ?? ""}</div>
                  <div style="font-weight:700;color:${color};font-size:13px;margin-bottom:5px">${risk} Risk</div>
                  <div style="color:#94a3b8;margin-bottom:2px">Max flood prob: <b style="color:#e2e8f0">${pct}%</b></div>
                  <div style="color:#94a3b8">Zone points: <b style="color:#e2e8f0">${data.count}</b></div>
                </div>`
              : `<div style="font-family:system-ui,sans-serif;font-size:12px">
                  <b style="color:#e2e8f0">${name}</b>
                  <div style="color:#475569;font-size:11px;margin-top:3px">No zone data</div>
                </div>`
          )
          .addTo(zonePolygonsGroupRef.current!);
      }
    })();
  }, [zones, showZonePolygons, riskFilter, mapReady, boundariesReady]);

  // ── Historical event district highlight ──────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;

      if (eventLayerRef.current) {
        eventLayerRef.current.clearLayers();
      } else {
        eventLayerRef.current = L.layerGroup().addTo(mapRef.current!);
      }

      if (!selectedEvent || !boundariesRef.current) return;

      const color   = EVENT_YEAR_COLORS[selectedEvent.year] ?? "#94a3b8";
      const nameSet = new Set(selectedEvent.affected_districts.map((d) => d.toLowerCase()));

      const matched: object[] = [];

      for (const feature of boundariesRef.current.features) {
        const name = (feature.properties?.name as string | undefined)?.toLowerCase();
        if (!name || !nameSet.has(name)) continue;

        matched.push(feature);
        L.geoJSON(feature as never, {
          style: () => ({
            color,
            weight:      2,
            fillColor:   color,
            fillOpacity: 0.28,
            opacity:     0.9,
          }),
          interactive: false,
        }).addTo(eventLayerRef.current!);
      }

      if (matched.length > 0) {
        const bounds = L.geoJSON({ type: "FeatureCollection", features: matched } as never).getBounds();
        if (bounds.isValid()) {
          mapRef.current?.fitBounds(bounds, { padding: [60, 60], animate: true, maxZoom: 8 });
        }
      }
    })();
  }, [selectedEvent, mapReady, boundariesReady]);

  // ── Selected location marker ───────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;

      markerRef.current?.remove();
      markerRef.current = null;
      if (!selectedLocation || !mapRef.current) return;

      const { lat, lng } = selectedLocation;
      const icon = L.divIcon({
        className: "",
        html: `<div style="
          width:18px;height:18px;border-radius:50%;
          background:#ef4444;border:3px solid #fff;
          box-shadow:0 0 12px rgba(239,68,68,0.9);
          position:relative;z-index:9999;
        "></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });

      markerRef.current = L.marker([lat, lng], { icon, zIndexOffset: 1000 })
        .addTo(mapRef.current)
        .bindPopup(`<span style="color:#94a3b8;font-size:11px">${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E</span>`)
        .openPopup();

      mapRef.current.setView([lat, lng], Math.max(mapRef.current.getZoom(), 8), { animate: true });
    })();
  }, [selectedLocation]);

  return <div ref={containerRef} className="w-full h-full" />;
}
