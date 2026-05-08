"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import {
  generateGridCells,
  getGridCellColor,
  getGridCellOpacity,
  type GridCell,
} from "@/lib/grid-risk";

interface Props {
  visible: boolean;
  onCellClick?: (cell: GridCell) => void;
  selectedCellId?: string | null;
}

export function GridRiskLayer({ visible, onCellClick, selectedCellId }: Props) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);
  const cellsRef = useRef<GridCell[]>([]);

  useEffect(() => {
    const cells = generateGridCells();
    cellsRef.current = cells;

    const layer = L.geoJSON(
      cells.map((c) => c.feature),
      {
        style: (feature) => {
          if (!feature) return {};
          const idx  = cells.findIndex((c) => c.feature === feature);
          const cell = cells[idx];
          if (!cell) return {};
          const color    = getGridCellColor(cell.risk_level);
          const isSelected = cell.id === selectedCellId;
          return {
            fillColor:   color,
            fillOpacity: isSelected ? 0.75 : getGridCellOpacity(cell.risk_level),
            color:       isSelected ? "#FFFFFF" : color,
            weight:      isSelected ? 2.0 : 0.4,
            opacity:     isSelected ? 0.9 : 0.3,
          };
        },
        onEachFeature: (feature, leafletLayer) => {
          const idx  = cells.findIndex((c) => c.feature === feature);
          const cell = cells[idx];
          if (!cell) return;

          const color  = getGridCellColor(cell.risk_level);
          const pct    = Math.round(cell.score * 100);
          const factors= cell.main_factors
            .map((f) => `<li style="color:#CBD5E1;font-size:10px;margin-top:2px">• ${f}</li>`)
            .join("");

          leafletLayer.bindTooltip(
            `<div style="min-width:164px;padding:7px 9px;background:#111E35;border:1px solid rgba(255,255,255,0.14);border-radius:8px;color:#F8FAFC">
              <div style="font-weight:700;font-size:12px;color:${color}">${cell.risk_level} Risk · ${pct}%</div>
              <div style="font-size:10px;color:#94A3B8;margin-top:2px">${cell.zone_label}</div>
              <ul style="margin:4px 0 0;padding:0;list-style:none">${factors}</ul>
              <div style="font-size:9px;color:#64748B;margin-top:5px">🌧 ${cell.rainfall_mm} mm/24h</div>
              <div style="font-size:9px;color:#22D3EE;margin-top:3px">Click for AI zone analysis →</div>
            </div>`,
            { sticky: true, opacity: 1, className: "pakflood-tooltip" }
          );

          if (onCellClick) {
            leafletLayer.on("click", (e) => {
              L.DomEvent.stopPropagation(e);
              onCellClick(cell);
            });
          }

          leafletLayer.on("mouseover", () => {
            const isSelected = cell.id === selectedCellId;
            (leafletLayer as L.Path).setStyle({
              weight: isSelected ? 2.5 : 1.5,
              opacity: 0.7,
              fillOpacity: Math.min(getGridCellOpacity(cell.risk_level) + 0.20, 0.80),
            });
          });
          leafletLayer.on("mouseout", () => {
            layer.resetStyle(leafletLayer);
          });
        },
      }
    );

    layerRef.current = layer;

    if (visible) layer.addTo(map);

    return () => {
      layer.remove();
      layerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, onCellClick]);

  // Toggle visibility
  useEffect(() => {
    if (!layerRef.current) return;
    if (visible) layerRef.current.addTo(map);
    else layerRef.current.remove();
  }, [visible, map]);

  // Re-style when selection changes
  useEffect(() => {
    if (!layerRef.current) return;
    const cells = cellsRef.current;
    layerRef.current.eachLayer((leafletLayer) => {
      const path = leafletLayer as L.Path & { feature?: { properties?: { _idx?: number } } };
      // Find matching cell by iterating
      const featureLayer = leafletLayer as L.GeoJSON;
      const geoJsonLayer = featureLayer as unknown as { feature: GeoJSON.Feature };
      const feat = geoJsonLayer.feature;
      const cell = cells.find((c) => c.feature === feat);
      if (!cell) return;
      const color      = getGridCellColor(cell.risk_level);
      const isSelected = cell.id === selectedCellId;
      path.setStyle({
        fillColor:   color,
        fillOpacity: isSelected ? 0.75 : getGridCellOpacity(cell.risk_level),
        color:       isSelected ? "#FFFFFF" : color,
        weight:      isSelected ? 2.0 : 0.4,
        opacity:     isSelected ? 0.9 : 0.3,
      });
    });
  }, [selectedCellId]);

  return null;
}
