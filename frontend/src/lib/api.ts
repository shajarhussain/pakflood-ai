import type { PredictionResponse, ZonesGeoJSON, DistrictSearchResult, FloodEvent, WeatherData } from "@/lib/types";
export type { FloodEvent };

const API_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "https://pakflood-ai.onrender.com/api/v1";

export async function fetchWeather(lat: number, lng: number): Promise<WeatherData> {
  const res = await fetch(`${API_BASE}/weather?lat=${lat}&lng=${lng}`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Weather unavailable (${res.status}): ${text}`);
  }
  return res.json() as Promise<WeatherData>;
}

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

export async function fetchBoundaries(): Promise<object | null> {
  try {
    const res = await fetch(`${API_BASE}/admin-boundaries`, { cache: "force-cache" });
    if (!res.ok) return null;
    return res.json();
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

export interface ChatMessage { role: "user" | "model"; content: string }

export async function sendChatMessage(
  message: string,
  history: ChatMessage[]
): Promise<string> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Chat failed (${res.status}): ${text}`);
  }
  const data = await res.json() as { reply: string };
  return data.reply;
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
