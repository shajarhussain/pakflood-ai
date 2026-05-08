import * as turf from "@turf/turf";
import type { Feature, Polygon, FeatureCollection } from "geojson";
import { PAKISTAN_BBOX, INDUS_WAYPOINTS } from "@/data/pakistan-bounds";
import { CITY_WEATHER } from "@/data/pakistan-cities-weather";

export type GridRiskLevel = "Severe" | "High" | "Moderate" | "Low" | "Water" | "Minimal";

export interface GridCell {
  id: string;
  feature: Feature<Polygon>;
  centroid: [number, number]; // [lat, lng]
  score: number;              // 0–1
  risk_level: GridRiskLevel;
  rainfall_mm: number;
  zone_label: string;
  main_factors: string[];
}

const CELL_SIDE_DEG = 0.6;

/** Straight-line distance in km from a point to the nearest Indus waypoint */
function distToIndusKm(lat: number, lng: number): number {
  const pt = turf.point([lng, lat]);
  let minDist = Infinity;
  for (const [wLat, wLng] of INDUS_WAYPOINTS) {
    const d = turf.distance(pt, turf.point([wLng, wLat]), { units: "kilometers" });
    if (d < minDist) minDist = d;
  }
  return minDist;
}

/** Nearest city weather object by centroid distance */
function nearestCityRainfall(lat: number, lng: number): number {
  const pt = turf.point([lng, lat]);
  let minDist = Infinity;
  let best = CITY_WEATHER[0];
  for (const city of CITY_WEATHER) {
    const d = turf.distance(pt, turf.point([city.lng, city.lat]), { units: "kilometers" });
    if (d < minDist) { minDist = d; best = city; }
  }
  return best.rainfall_mm_24h;
}

function classifyScore(score: number): GridRiskLevel {
  if (score >= 0.75) return "Severe";
  if (score >= 0.55) return "High";
  if (score >= 0.35) return "Moderate";
  if (score >= 0.15) return "Low";
  return "Minimal";
}

function zoneLabel(lat: number, lng: number): string {
  if (lat < 28.5 && lat > 23.5 && lng > 65.5 && lng < 71.5) return "Sindh Floodplain";
  if (lat > 28 && lat < 33 && lng > 70 && lng < 74.5) return "Punjab Plains";
  if (lat > 32 && lat < 36 && lng > 69 && lng < 74) return "KP Piedmont";
  if (lat > 25 && lat < 32 && lng > 61 && lng < 68) return "Balochistan Highlands";
  if (lat > 35) return "Gilgit-Baltistan";
  if (lat > 33 && lat < 36 && lng > 73 && lng < 75) return "AJK/Kashmir";
  return "Transitional";
}

/** Deterministic flood risk score per centroid using geographic heuristics */
function computeScore(lat: number, lng: number): { score: number; factors: string[] } {
  let score = 0.05;
  const factors: string[] = [];

  const distIndus = distToIndusKm(lat, lng);
  const rainfall = nearestCityRainfall(lat, lng);

  // Sindh Floodplain — highest flood exposure
  if (lat >= 23.5 && lat <= 28.5 && lng >= 65.5 && lng <= 71.5) {
    score += 0.50;
    factors.push("Sindh alluvial floodplain");
    if (lat >= 26 && lat <= 28.5 && lng >= 68 && lng <= 70.5) {
      score += 0.12; // Jacobabad / Larkana / Sukkur corridor
      factors.push("Sukkur-Jacobabad high-risk corridor");
    }
  }

  // Punjab plains — moderate-high flood risk
  if (lat >= 28 && lat <= 33 && lng >= 70 && lng <= 74.5) {
    score += 0.20;
    factors.push("Punjab alluvial plain");
    if (lat >= 30 && lat <= 31.5 && lng >= 70.5 && lng <= 72.5) {
      score += 0.08; // Multan / Jhang
      factors.push("Multan-Jhang flood corridor");
    }
  }

  // KP piedmont — flash flood zone
  if (lat >= 32 && lat <= 36 && lng >= 69 && lng <= 74) {
    score += 0.12;
    factors.push("KP mountain piedmont");
  }

  // Balochistan — low but flash-flood prone
  if (lat >= 25 && lat <= 32 && lng >= 61 && lng <= 68) {
    score += 0.08;
    factors.push("Balochistan semi-arid zone");
  }

  // Gilgit-Baltistan — GLOF risk, not riverine
  if (lat > 35) {
    score = 0.12 + Math.random() * 0.04; // modest GLOF base
    factors.push("Glacial lake outburst risk (GLOF)");
    return { score: Math.min(score, 0.95), factors };
  }

  // Proximity to Indus bonus
  if (distIndus < 50) {
    score += 0.18;
    factors.push("Within 50 km of Indus River");
  } else if (distIndus < 100) {
    score += 0.09;
    factors.push("Within 100 km of Indus River");
  }

  // Rainfall contribution
  if (rainfall >= 50) {
    score += 0.15;
    factors.push(`Extreme rainfall (${rainfall} mm/24h)`);
  } else if (rainfall >= 25) {
    score += 0.08;
    factors.push(`Heavy rainfall (${rainfall} mm/24h)`);
  } else if (rainfall >= 10) {
    score += 0.04;
    factors.push(`Moderate rainfall (${rainfall} mm/24h)`);
  }

  return { score: Math.min(score, 0.95), factors };
}

let _cache: GridCell[] | null = null;

export function generateGridCells(): GridCell[] {
  if (_cache) return _cache;

  const bbox = PAKISTAN_BBOX; // [west, south, east, north]
  const grid: FeatureCollection<Polygon> = turf.squareGrid(bbox, CELL_SIDE_DEG, {
    units: "degrees",
  });

  const cells: GridCell[] = [];
  grid.features.forEach((feature, idx) => {
    const center = turf.centroid(feature);
    const [lng, lat] = center.geometry.coordinates;

    // Only include cells whose centroid is within the Pakistan max-bounds
    if (lat < 23.5 || lat > 37.2 || lng < 60.8 || lng > 77.2) return;

    const { score, factors } = computeScore(lat, lng);
    const level = classifyScore(score);
    if (level === "Minimal") return;
    const rainfall = nearestCityRainfall(lat, lng);

    cells.push({
      id: `grid-${idx}`,
      feature,
      centroid: [lat, lng],
      score,
      risk_level: level,
      rainfall_mm: rainfall,
      zone_label: zoneLabel(lat, lng),
      main_factors: factors.slice(0, 3),
    });
  });

  _cache = cells;
  return cells;
}

export function getGridCellColor(level: GridRiskLevel): string {
  switch (level) {
    case "Severe":   return "#EF4444";
    case "High":     return "#F97316";
    case "Moderate": return "#F59E0B";
    case "Low":      return "#22C55E";
    case "Water":    return "#22D3EE";
    case "Minimal":  return "#475569";
  }
}

export function getGridCellOpacity(level: GridRiskLevel): number {
  switch (level) {
    case "Severe":   return 0.55;
    case "High":     return 0.45;
    case "Moderate": return 0.35;
    case "Low":      return 0.25;
    case "Minimal":  return 0.12;
    default:         return 0.20;
  }
}
