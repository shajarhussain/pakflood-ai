"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { CITY_WEATHER, type CityWeather } from "@/data/pakistan-cities-weather";

interface Props {
  visible: boolean;
  onCityClick?: (city: CityWeather) => void;
  selectedCityName?: string | null;
}

function windArrow(deg: number): string {
  const arrows = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"];
  return arrows[Math.round(((deg % 360) / 360) * 8) % 8];
}

function chipHtml(city: CityWeather, isSelected: boolean): string {
  const arrow = windArrow(city.wind_deg);
  const rainColor =
    city.rainfall_mm_24h >= 40 ? "#EF4444"
    : city.rainfall_mm_24h >= 15 ? "#F97316"
    : city.rainfall_mm_24h >= 5  ? "#22D3EE"
    : "#475569";
  const border = isSelected ? "1.5px solid #22D3EE" : "1px solid rgba(255,255,255,0.16)";
  const bg     = isSelected ? "rgba(34,211,238,0.14)" : "rgba(13,19,35,0.86)";
  const glow   = isSelected
    ? "0 0 10px rgba(34,211,238,0.45), 0 1px 6px rgba(0,0,0,0.65)"
    : "0 1px 6px rgba(0,0,0,0.55)";

  return `<div style="
    background:${bg};
    border:${border};
    border-radius:20px;
    padding:3px 8px 3px 7px;
    display:inline-flex;
    align-items:center;
    gap:4px;
    backdrop-filter:blur(10px);
    -webkit-backdrop-filter:blur(10px);
    box-shadow:${glow};
    cursor:pointer;
    white-space:nowrap;
    user-select:none;
  ">
    <span style="font-size:10px;font-weight:700;color:#F1F5F9;line-height:1">${city.name}</span>
    <span style="font-size:11px;font-weight:800;color:#FCD34D;line-height:1">${city.temp_c}°</span>
    <span style="font-size:10px;color:${rainColor};line-height:1">${arrow}</span>
  </div>`;
}

export function CompactCityChips({ visible, onCityClick, selectedCityName }: Props) {
  const map = useMap();
  const markersRef = useRef<L.Marker[]>([]);

  useEffect(() => {
    const markers: L.Marker[] = CITY_WEATHER.map((city) => {
      const isSelected = city.name === selectedCityName;
      const icon = L.divIcon({
        html: chipHtml(city, isSelected),
        className: "",
        iconAnchor: [40, 12],
      });

      const marker = L.marker([city.lat, city.lng], {
        icon,
        interactive: true,
        keyboard: false,
        zIndexOffset: isSelected ? 1000 : 0,
      });

      // No hover tooltips — info appears on click via CopilotPanel.
      if (onCityClick) {
        marker.on("click", (e) => {
          L.DomEvent.stopPropagation(e);
          onCityClick(city);
        });
      }

      return marker;
    });

    markersRef.current = markers;
    if (visible) markers.forEach((m) => m.addTo(map));

    return () => {
      markers.forEach((m) => m.remove());
      markersRef.current = [];
    };
  }, [map, onCityClick]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (visible) markersRef.current.forEach((m) => m.addTo(map));
    else markersRef.current.forEach((m) => m.remove());
  }, [visible, map]);

  useEffect(() => {
    markersRef.current.forEach((marker, i) => {
      const city = CITY_WEATHER[i];
      const isSelected = city.name === selectedCityName;
      marker.setIcon(
        L.divIcon({ html: chipHtml(city, isSelected), className: "", iconAnchor: [40, 12] })
      );
      marker.setZIndexOffset(isSelected ? 1000 : 0);
    });
  }, [selectedCityName]);

  return null;
}
