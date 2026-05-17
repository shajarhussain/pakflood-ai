export type RiskLevel = "Low" | "Moderate" | "High" | "Severe";

export interface TopFactor {
  name: string;
  value: number;
  importance: number;
}

export interface PredictionResponse {
  latitude: number;
  longitude: number;
  flood_probability: number;
  risk_level: RiskLevel | "Unknown";
  confidence: number;
  top_factors: TopFactor[];
  weather_features: Record<string, number>;
  model_version: string;
  saved_to_db: boolean;
  disclaimer: string;
}

// ── Zone heatmap ─────────────────────────────────────────────────────────────

export interface ZoneFeatureProperties {
  flood_prob: number;
  risk_level: RiskLevel | "Unknown";
  risk_score: number;
  confidence: number;
  top_factors: TopFactor[];
  computed_at: string;
  precipitation?: number;
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  soil_moisture?: number;
  is_monsoon?: number;
}

export interface ZoneFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lng, lat] — GeoJSON order
  };
  properties: ZoneFeatureProperties;
}

export interface ZonesGeoJSON {
  type: "FeatureCollection";
  features: ZoneFeature[];
  metadata: {
    computed_at: string | null;
    is_fresh: boolean;
    total_points: number;
    grid_step_degrees: number;
    message?: string;
  };
}
