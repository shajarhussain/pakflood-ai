"use client";
import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, Marker, LayerGroup } from "leaflet";
import {
  PAKISTAN_CENTER,
  PAKISTAN_BOUNDS,
  PAKISTAN_MAX_BOUNDS,
  MAP_DEFAULT_ZOOM,
  MAP_MIN_ZOOM,
  MAP_MAX_ZOOM,
} from "@/data/pakistan-bounds";
import type { ZonesGeoJSON } from "@/lib/types";

const ZONE_COLORS: Record<string, string> = {
  Severe:   "#ef4444",
  High:     "#f97316",
  Moderate: "#eab308",
  Low:      "#22c55e",
  Unknown:  "#475569",
};

interface Props {
  selectedLocation: { lat: number; lng: number } | null;
  onLocationSelect: (lat: number, lng: number) => void;
  zones?: ZonesGeoJSON | null;
  showZones?: boolean;
}

export default function FloodMap({ selectedLocation, onLocationSelect, zones, showZones }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<LeafletMap | null>(null);
  const markerRef    = useRef<Marker | null>(null);
  const zonesGroupRef = useRef<LayerGroup | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // ── Initialize map ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // Guard against React StrictMode double-invocation
    let destroyed = false;

    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      if (destroyed || !containerRef.current) return;

      const map = L.map(containerRef.current, {
        center: PAKISTAN_CENTER,
        zoom: MAP_DEFAULT_ZOOM,
        minZoom: MAP_MIN_ZOOM,
        maxZoom: MAP_MAX_ZOOM,
        maxBounds: PAKISTAN_MAX_BOUNDS,
        maxBoundsViscosity: 0.8,
        zoomControl: true,
      });

      if (destroyed) { map.remove(); return; }

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap contributors',
        subdomains: "abcd",
        maxZoom: 19,
      }).addTo(map);

      const bounds = PAKISTAN_BOUNDS;
      L.rectangle(bounds, {
        color: "rgba(34,211,238,0.3)",
        weight: 1,
        fill: false,
        dashArray: "4 4",
      }).addTo(map);

      map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        if (
          lat < bounds[0][0] || lat > bounds[1][0] ||
          lng < bounds[0][1] || lng > bounds[1][1]
        ) return;
        onLocationSelect(lat, lng);
      });

      mapRef.current = map;
      setMapReady(true);
    })();

    return () => {
      destroyed = true;
      mapRef.current?.remove();
      mapRef.current = null;
      zonesGroupRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Zone heatmap layer ────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;

      // Always clear first
      if (zonesGroupRef.current) {
        zonesGroupRef.current.clearLayers();
      }

      if (!showZones || !zones?.features?.length) return;

      // Create the layer group once and keep it in the map
      if (!zonesGroupRef.current) {
        zonesGroupRef.current = L.layerGroup().addTo(mapRef.current!);
      }

      for (const feature of zones.features) {
        const [lng, lat] = feature.geometry.coordinates;
        const { flood_prob, risk_level, confidence, top_factors } = feature.properties;
        const color    = ZONE_COLORS[risk_level] ?? "#475569";
        const opacity  = Math.max(0.18, (flood_prob ?? 0) * 0.88);
        const pct      = Math.round((flood_prob   ?? 0) * 100);
        const confPct  = Math.round((confidence   ?? 0) * 100);
        const topName  = top_factors?.[0]?.name ?? "—";

        L.circleMarker([lat, lng], {
          radius:      14,
          color:       "transparent",
          fillColor:   color,
          fillOpacity: opacity,
          weight:      0,
          interactive: true,
        })
          .on("click", (e) => {
            // Prevent map click handler from firing a new prediction
            (e.originalEvent as Event).stopPropagation();
          })
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
  }, [zones, showZones, mapReady]);

  // ── Selected location marker ──────────────────────────────────────────────
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
        .bindPopup(
          `<span style="color:#94a3b8;font-size:11px">${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E</span>`
        )
        .openPopup();

      mapRef.current.setView([lat, lng], Math.max(mapRef.current.getZoom(), 8), {
        animate: true,
      });
    })();
  }, [selectedLocation]);

  return <div ref={containerRef} className="w-full h-full" />;
}
