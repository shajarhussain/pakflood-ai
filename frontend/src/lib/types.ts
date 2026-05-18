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

// ── Flood events ─────────────────────────────────────────────────────────────

export interface FloodEvent {
  id: string;
  year: number;
  title: string;
  affected_provinces: string[];
  affected_districts: string[];
  peak_month: string;
  estimated_affected: number | null;
  damage_usd_billion: number | null;
  description: string;
}

// ── Weather ───────────────────────────────────────────────────────────────────

export interface WeatherData {
  location: string;
  country: string;
  temp: number;
  feels_like: number;
  temp_min: number;
  temp_max: number;
  humidity: number;
  pressure: number;
  wind_speed: number;
  wind_deg: number;
  wind_dir: string;
  weather: string;
  description: string;
  icon: string;
  clouds: number;
  visibility: number;
}

// ── District search ───────────────────────────────────────────────────────────

export interface DistrictSummary {
  total_points: number;
  avg_flood_prob: number | null;
  max_flood_prob: number | null;
  dominant_risk: RiskLevel | null;
  risk_breakdown: Record<string, number>;
  computed_at: string | null;
}

export interface DistrictSearchResult {
  district_id: string;
  name: string;
  province: string;
  center: { lat: number; lng: number };
  summary: DistrictSummary | null;
}
