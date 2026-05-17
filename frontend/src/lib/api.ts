import type { PredictionResponse, ZonesGeoJSON } from "@/lib/types";

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
