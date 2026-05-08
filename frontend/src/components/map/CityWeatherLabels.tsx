"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { CITY_WEATHER, WEATHER_DEMO_LABEL, type CityWeather } from "@/data/pakistan-cities-weather";

interface Props {
  visible: boolean;
  onCityClick?: (city: CityWeather) => void;
  selectedCityName?: string | null;
}

export function CityWeatherLabels({ visible, onCityClick, selectedCityName }: Props) {
  const map = useMap();
  const markersRef = useRef<L.Marker[]>([]);

  function makeIconHtml(city: CityWeather, isSelected: boolean): string {
    const windArrow = getWindArrow(city.wind_deg);
    const rainBar   = getRainBar(city.rainfall_mm_24h);
    const mvpDot    = city.is_mvp_district
      ? `<span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#22D3EE;vertical-align:middle;margin-right:3px"></span>`
      : "";

    const borderColor = isSelected ? "#22D3EE" : "rgba(255,255,255,0.14)";
    const glowShadow  = isSelected ? "0 0 12px rgba(34,211,238,0.55), 0 2px 12px rgba(0,0,0,0.5)" : "0 2px 12px rgba(0,0,0,0.5)";

    return `
      <div style="
        background:rgba(13,21,38,0.92);
        border:1.5px solid ${borderColor};
        border-radius:9px;
        padding:5px 8px;
        min-width:82px;
        backdrop-filter:blur(10px);
        box-shadow:${glowShadow};
        cursor:pointer;
      ">
        <div style="font-size:11px;font-weight:700;color:#F8FAFC;display:flex;align-items:center;gap:2px">
          ${mvpDot}${city.name}
        </div>
        <div style="font-size:14px;font-weight:800;color:#FCD34D;margin-top:1px;line-height:1.1">${city.temp_c}°C</div>
        <div style="font-size:9px;color:#94A3B8;margin-top:1px">${city.icon} ${city.condition}</div>
        <div style="font-size:9px;color:#7DD3FC;margin-top:2px">${windArrow} ${city.wind_kmh} km/h ${city.wind_dir}</div>
        <div style="margin-top:3px;display:flex;align-items:center;gap:3px">
          <div style="font-size:8px;color:#64748B">🌧</div>
          ${rainBar}
          <div style="font-size:8px;color:#22D3EE">${city.rainfall_mm_24h}mm</div>
        </div>
        ${isSelected ? '<div style="font-size:8px;color:#22D3EE;margin-top:3px">● Selected</div>' : ''}
      </div>
    `;
  }

  useEffect(() => {
    const markers: L.Marker[] = CITY_WEATHER.map((city) => {
      const isSelected = city.name === selectedCityName;
      const icon = L.divIcon({
        html: makeIconHtml(city, isSelected),
        className: "",
        iconAnchor: [41, 0],
      });

      const marker = L.marker([city.lat, city.lng], {
        icon,
        interactive: true,
        keyboard: false,
        zIndexOffset: isSelected ? 1000 : 0,
      });

      marker.bindTooltip(
        `<div style="font-size:10px;padding:5px 7px;background:#0D1526;color:#CBD5E1;border:1px solid rgba(255,255,255,0.12);border-radius:7px;min-width:140px">
          <b style="color:#F8FAFC;font-size:11px">${city.name}</b><br/>
          Humidity: <b>${city.humidity_pct}%</b><br/>
          Wind: <b>${city.wind_kmh} km/h</b> from ${city.wind_dir}<br/>
          Rainfall 24h: <b>${city.rainfall_mm_24h} mm</b><br/>
          <span style="color:#F59E0B;font-size:8px;margin-top:2px;display:block">${WEATHER_DEMO_LABEL.slice(0, 52)}…</span>
          ${onCityClick ? '<span style="color:#22D3EE;font-size:8px">Click for full weather analysis →</span>' : ""}
        </div>`,
        { sticky: false, className: "pakflood-tooltip", direction: "top", offset: [0, -4] }
      );

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, onCityClick]);

  // Toggle visibility
  useEffect(() => {
    if (visible) markersRef.current.forEach((m) => m.addTo(map));
    else markersRef.current.forEach((m) => m.remove());
  }, [visible, map]);

  // Rebuild icons when selection changes (to update glow)
  useEffect(() => {
    markersRef.current.forEach((marker, i) => {
      const city       = CITY_WEATHER[i];
      const isSelected = city.name === selectedCityName;
      const icon = L.divIcon({
        html: makeIconHtml(city, isSelected),
        className: "",
        iconAnchor: [41, 0],
      });
      marker.setIcon(icon);
      if (isSelected) {
        marker.setZIndexOffset(1000);
      } else {
        marker.setZIndexOffset(0);
      }
    });
  }, [selectedCityName]);

  return null;
}

function getWindArrow(deg: number): string {
  const arrows = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"];
  const idx = Math.round(((deg % 360) / 360) * 8) % 8;
  return arrows[idx];
}

function getRainBar(mm: number): string {
  const maxMm = 70;
  const pct   = Math.min(100, (mm / maxMm) * 100);
  const color = mm >= 50 ? "#EF4444" : mm >= 25 ? "#F97316" : mm >= 10 ? "#22D3EE" : "#334155";
  return `<div style="width:34px;height:4px;background:#1E293B;border-radius:2px;overflow:hidden">
    <div style="width:${pct}%;height:100%;background:${color};border-radius:2px"></div>
  </div>`;
}
