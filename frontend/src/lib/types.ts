export type RiskLevel = "Low" | "Moderate" | "High" | "Severe";

export interface District {
  id: string;
  name: string;
  province: string;
  geometry: GeoJSON.Geometry;
}

export interface RiskSnapshot {
  district_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  top_factors: string[];
  source_status: Record<string, "fresh" | "stale" | "error">;
  model_version: string;
  updated_at: string;
}

export interface RiskExplanation {
  risk_level: RiskLevel;
  main_causes: string[];
  historical_evidence: string[];
  suggested_actions: string[];
  confidence: number;
  data_sources: string[];
  disclaimer: string;
}

export interface FloodEvent {
  id: string;
  year: number;
  title: string;
  affected_districts: string[];
  description: string;
}

export interface DataSource {
  source_id: string;
  name: string;
  status: "fresh" | "stale" | "error";
  last_updated: string | null;
  adapter_class: string;
}
