"use client";

import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { CITY_WEATHER } from "@/data/pakistan-cities-weather";

interface Props {
  visible: boolean;
}

function colorForRain(mm: number): string {
  if (mm >= 50) return "#FF0040";
  if (mm >= 25) return "#FF7700";
  if (mm >= 10) return "#00D4FF";
  return "#3B82F6";
}

export function RainfallStationLayer({ visible }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!visible) return;

    const markers = CITY_WEATHER.map((city) => {
      const mm = city.rainfall_mm_24h;
      const color = colorForRain(mm);
      const radius = Math.min(10 + mm * 0.45, 32);
      const heavy = mm >= 25;
      const ringSize = radius * 2 + 16;

      const html = `
        <div style="
          position: relative;
          width: ${ringSize}px; height: ${ringSize}px;
          transform: translate(-50%, -50%);
          pointer-events: none;
        ">
          <div style="
            position: absolute; left: 50%; top: 50%;
            width: ${ringSize}px; height: ${ringSize}px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background: radial-gradient(circle, ${color}55 0%, ${color}00 70%);
            ${heavy ? "animation: rainfall-station-pulse 1.6s ease-in-out infinite;" : ""}
          "></div>
          <div style="
            position: absolute; left: 50%; top: 50%;
            width: ${radius * 2}px; height: ${radius * 2}px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background: ${color};
            border: 2px solid rgba(255,255,255,0.85);
            box-shadow: 0 0 ${radius}px ${color}, 0 2px 8px rgba(0,0,0,0.4);
            display: flex; align-items: center; justify-content: center;
            font: 800 ${Math.max(10, Math.min(14, radius * 0.75))}px var(--font-geist-mono, monospace);
            color: white;
            text-shadow: 0 1px 3px rgba(0,0,0,0.7);
            letter-spacing: -0.02em;
          ">${mm}</div>
          <div style="
            position: absolute; left: 50%;
            top: calc(50% + ${radius + 8}px);
            transform: translateX(-50%);
            white-space: nowrap;
            font: 700 9px/1.2 var(--font-geist-mono, monospace);
            color: #F1F5F9;
            text-shadow: 0 1px 6px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.8);
            letter-spacing: 0.10em;
            text-transform: uppercase;
            text-align: center;
          ">
            ${city.name}<br/>
            <span style="color:${color}; letter-spacing: 0.06em; font-size: 8px;">${mm} MM/24H</span>
          </div>
        </div>
      `;

      return L.marker([city.lat, city.lng], {
        icon: L.divIcon({
          html,
          className: "rainfall-station-icon",
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        }),
        interactive: false,
        zIndexOffset: 800,
      });
    });

    markers.forEach((m) => m.addTo(map));
    return () => {
      markers.forEach((m) => m.remove());
    };
  }, [map, visible]);

  return null;
}
