/**
 * Typed API client for PakFlood AI backend.
 * All functions fall back to mock data when the backend is unreachable,
 * so the UI remains functional during local frontend-only development.
 */
import type { RiskLevel } from "@/lib/types";
import {
  MOCK_RISK,
  MOCK_FLOOD_EVENTS,
  type MockRiskEntry,
  type MockFloodEvent,
} from "@/data/mock";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ---------------------------------------------------------------------------
// Response types (mirror backend Pydantic schemas)
// ---------------------------------------------------------------------------

/**
 * Status of the v3 real-prediction model artifact.
 *
 * The UI must use this to decide whether to show "Real prediction v3"
 * or the honest "Real prediction model unavailable" message. The mock
 * `model_version` returned by the risk endpoints is NOT renamed — only
 * an honest /api/v1/model/status response with both flags true unlocks
 * the v3 chrome.
 */
export interface ModelStatus {
  mode: string;
  artifact_exists: boolean;
  artifact_path: string;
  metadata_exists: boolean;
  metadata_path: string;
  is_prediction_model: boolean;
  model_name: string | null;
  model_type: string | null;
  prediction_window: string | null;
  calibration_method: string | null;
  calibration_api: string | null;
  last_trained_iso: string | null;
  data_sources: Record<string, string> | null;
  metric_crs: string | null;
  remediation: string | null;
}

export const MODEL_UNAVAILABLE_MESSAGE =
  "Real prediction model unavailable — run the real-data pipeline first.";

/** Returns the live model status; null if the backend is unreachable. */
export async function fetchModelStatus(): Promise<ModelStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/model/status`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as ModelStatus;
  } catch {
    return null;
  }
}

/** True only when /api/v1/model/status confirms both flags. */
export function isV3Available(status: ModelStatus | null | undefined): boolean {
  return !!status && status.artifact_exists === true && status.is_prediction_model === true;
}

export interface ApiRiskResponse {
  district_id: string;
  name: string;
  province: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  top_factors: string[];
  forecast_window_hours: number;
  model_version: string;
  source_status: Record<string, string>;
  disclaimer: string;
}

export interface ApiFloodEvent {
  id: string;
  year: number;
  title: string;
  affected_provinces: string[];
  affected_districts: string[];
  peak_month: string;
  estimated_affected: number;
  damage_usd_billion: number | null;
  description: string;
}

export interface ApiDataSource {
  id: string;
  name: string;
  status: string;
  last_updated: string | null;
  latency_hours: number | null;
  latency_ms: number | null;
  description: string;
  features_created: string[];
  circuit_state: string;
  error_message: string | null;
}

export interface ApiLocationResult {
  district_id: string;
  name: string;
  province: string;
  center: [number, number];
  risk_level: RiskLevel;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// GeoJSON boundaries
// ---------------------------------------------------------------------------

export async function fetchBoundaries(): Promise<object | null> {
  return apiFetch<object>("/admin-boundaries?level=district");
}

// ---------------------------------------------------------------------------
// Risk
// ---------------------------------------------------------------------------

function mockToApiRisk(m: MockRiskEntry): ApiRiskResponse {
  return {
    district_id: m.district_id,
    name: m.name,
    province: m.province,
    risk_score: m.risk_score,
    risk_level: m.risk_level,
    confidence: m.confidence,
    top_factors: m.top_factors,
    forecast_window_hours: 72,
    model_version: "mock-v1.0",
    source_status: { imerg: "mock" },
    disclaimer:
      "PakFlood AI is an educational decision-support prototype. Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions.",
  };
}

export async function fetchRiskByDistrict(districtId: string): Promise<ApiRiskResponse> {
  const data = await apiFetch<ApiRiskResponse>(`/risk/by-boundary/${districtId}`);
  if (data) return data;
  const mock = MOCK_RISK.find((r) => r.district_id === districtId);
  if (mock) return mockToApiRisk(mock);
  throw new Error(`No risk data for district ${districtId}`);
}

export async function fetchAllRisk(): Promise<ApiRiskResponse[]> {
  // Phase 3: replace with a real list endpoint once available
  return MOCK_RISK.map(mockToApiRisk);
}

// ---------------------------------------------------------------------------
// Flood events
// ---------------------------------------------------------------------------

function mockToApiEvent(m: MockFloodEvent): ApiFloodEvent {
  return {
    id: m.id,
    year: m.year,
    title: m.title,
    affected_provinces: m.affected_provinces,
    affected_districts: m.affected_districts,
    peak_month: m.peak_month,
    estimated_affected: m.estimated_affected,
    damage_usd_billion: m.damage_usd_billion ?? null,
    description: m.description,
  };
}

export async function fetchFloodEvents(districtName?: string): Promise<ApiFloodEvent[]> {
  const path = districtName
    ? `/flood-events?district_name=${encodeURIComponent(districtName)}`
    : "/flood-events";
  const data = await apiFetch<ApiFloodEvent[]>(path);
  if (data) return data;
  const events = MOCK_FLOOD_EVENTS.map(mockToApiEvent);
  if (districtName) {
    return events.filter((e) => e.affected_districts.includes(districtName));
  }
  return events;
}

// ---------------------------------------------------------------------------
// Data sources
// ---------------------------------------------------------------------------

export async function fetchDataSources(): Promise<ApiDataSource[]> {
  const data = await apiFetch<ApiDataSource[]>("/data-sources");
  if (data) return data;
  return [];
}

// ---------------------------------------------------------------------------
// Risk explanation (Phase 5)
// ---------------------------------------------------------------------------

export async function fetchExplanation(districtId: string): Promise<import("@/lib/types").RiskExplanation | null> {
  return apiFetch<import("@/lib/types").RiskExplanation>(
    `/explain-risk/by-boundary/${encodeURIComponent(districtId)}`
  );
}

// ---------------------------------------------------------------------------
// Location search
// ---------------------------------------------------------------------------

export async function searchLocations(q: string): Promise<ApiLocationResult[]> {
  if (!q || q.length < 2) return [];
  const data = await apiFetch<ApiLocationResult[]>(`/location/search?q=${encodeURIComponent(q)}`);
  if (data) return data;
  return MOCK_RISK.filter((r) => r.name.toLowerCase().includes(q.toLowerCase())).map((r) => ({
    district_id: r.district_id,
    name: r.name,
    province: r.province,
    center: r.center,
    risk_level: r.risk_level,
  }));
}
