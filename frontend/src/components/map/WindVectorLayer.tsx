"use client";

import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { CITY_WEATHER } from "@/data/pakistan-cities-weather";

interface Props {
  visible: boolean;
}

const ARROW_SPACING_DEG = 2.5;

// Interpolate wind vectors across a coarse grid using inverse-distance weighting from city stations
function interpolateWind(lat: number, lng: number): { deg: number; kmh: number } {
  let totalWeight = 0;
  let sumDeg = 0;
  let sumKmh = 0;

  for (const city of CITY_WEATHER) {
    const dlat = lat - city.lat;
    const dlng = lng - city.lng;
    const dist2 = dlat * dlat + dlng * dlng;
    const weight = 1 / (dist2 + 0.01);
    totalWeight += weight;
    sumDeg += city.wind_deg * weight;
    sumKmh += city.wind_kmh * weight;
  }

  return {
    deg: (sumDeg / totalWeight) % 360,
    kmh: sumKmh / totalWeight,
  };
}

function makeArrowSvg(deg: number, kmh: number): string {
  const intensity = Math.min(1, kmh / 40);
  const opacity = 0.35 + intensity * 0.45;
  const color = `rgba(34,211,238,${opacity})`;
  const size = 16 + intensity * 8;

  return `
    <svg width="${size}" height="${size}" viewBox="0 0 24 24" style="transform:rotate(${deg}deg)">
      <path d="M12 2 L18 18 L12 14 L6 18 Z" fill="${color}" />
    </svg>
  `;
}

export function WindVectorLayer({ visible }: Props) {
  const map = useMap();
  const markersRef = useRef<L.Marker[]>([]);

  useEffect(() => {
    const markers: L.Marker[] = [];

    // Pakistan bbox grid
    for (let lat = 24; lat <= 36.5; lat += ARROW_SPACING_DEG) {
      for (let lng = 61.5; lng <= 76.5; lng += ARROW_SPACING_DEG) {
        const { deg, kmh } = interpolateWind(lat, lng);
        const icon = L.divIcon({
          html: makeArrowSvg(deg, kmh),
          className: "",
          iconAnchor: [12, 12],
        });
        const marker = L.marker([lat, lng], { icon, interactive: false, keyboard: false });
        markers.push(marker);
      }
    }

    markersRef.current = markers;

    if (visible) {
      markers.forEach((m) => m.addTo(map));
    }

    return () => {
      markers.forEach((m) => m.remove());
      markersRef.current = [];
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  useEffect(() => {
    if (visible) {
      markersRef.current.forEach((m) => m.addTo(map));
    } else {
      markersRef.current.forEach((m) => m.remove());
    }
  }, [visible, map]);

  return null;
}
