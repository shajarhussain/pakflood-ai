import type { PredictionResponse, ZonesGeoJSON, DistrictSearchResult, FloodEvent } from "@/lib/types";
export type { FloodEvent };

const API_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "https://pakflood-ai.onrender.com/api/v1";

export async function predictFloodRisk(lat: number, lng: number): Promise<PredictionResponse> {
  const res = await fetch(`${API_BASE}/predict?lat=${lat}&lng=${lng}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Prediction failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<PredictionResponse>;
}

export interface ModelStatus {
  model_version: string;
  artifact_ready: boolean;
  features: number;
  disclaimer: string;
}

export async function fetchModelStatus(): Promise<ModelStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/model/status`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<ModelStatus>;
  } catch {
    return null;
  }
}

export async function fetchZonesGeoJSON(): Promise<ZonesGeoJSON | null> {
  try {
    const res = await fetch(`${API_BASE}/zones/geojson`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json() as Promise<ZonesGeoJSON>;
  } catch {
    return null;
  }
}

export async function fetchFloodEvents(): Promise<FloodEvent[]> {
  try {
    const res = await fetch(`${API_BASE}/flood-events`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json() as Promise<FloodEvent[]>;
  } catch {
    return [];
  }
}

export async function searchDistricts(q: string): Promise<DistrictSearchResult[]> {
  if (q.trim().length < 2) return [];
  try {
    const res = await fetch(
      `${API_BASE}/districts/search?q=${encodeURIComponent(q.trim())}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    return res.json() as Promise<DistrictSearchResult[]>;
  } catch {
    return [];
  }
}
