// Demo weather data for major Pakistani cities
// Label: "Demo weather labels — live weather integration planned"
// Values are representative for monsoon season (July–August)

export interface CityWeather {
  name: string;
  lat: number;
  lng: number;
  temp_c: number;
  wind_kmh: number;
  wind_dir: string;   // compass label
  wind_deg: number;   // degrees 0–360
  condition: string;  // brief description
  icon: string;       // emoji icon
  rainfall_mm_24h: number;
  humidity_pct: number;
  is_mvp_district: boolean;
}

export const CITY_WEATHER: CityWeather[] = [
  {
    name: "Karachi",
    lat: 24.86, lng: 67.01,
    temp_c: 33, wind_kmh: 22, wind_dir: "SW", wind_deg: 225,
    condition: "Partly cloudy", icon: "⛅",
    rainfall_mm_24h: 2, humidity_pct: 72,
    is_mvp_district: false,
  },
  {
    name: "Lahore",
    lat: 31.55, lng: 74.35,
    temp_c: 38, wind_kmh: 14, wind_dir: "NW", wind_deg: 315,
    condition: "Hot & humid", icon: "🌤",
    rainfall_mm_24h: 8, humidity_pct: 68,
    is_mvp_district: true,
  },
  {
    name: "Islamabad",
    lat: 33.72, lng: 73.06,
    temp_c: 33, wind_kmh: 18, wind_dir: "SW", wind_deg: 220,
    condition: "Monsoon showers", icon: "🌧",
    rainfall_mm_24h: 22, humidity_pct: 78,
    is_mvp_district: false,
  },
  {
    name: "Peshawar",
    lat: 34.01, lng: 71.58,
    temp_c: 36, wind_kmh: 20, wind_dir: "SW", wind_deg: 205,
    condition: "Hazy & warm", icon: "🌤",
    rainfall_mm_24h: 6, humidity_pct: 55,
    is_mvp_district: true,
  },
  {
    name: "Quetta",
    lat: 30.18, lng: 67.00,
    temp_c: 30, wind_kmh: 26, wind_dir: "NW", wind_deg: 320,
    condition: "Dry & windy", icon: "💨",
    rainfall_mm_24h: 1, humidity_pct: 35,
    is_mvp_district: true,
  },
  {
    name: "Multan",
    lat: 30.20, lng: 71.44,
    temp_c: 41, wind_kmh: 12, wind_dir: "NE", wind_deg: 45,
    condition: "Extreme heat", icon: "🔥",
    rainfall_mm_24h: 4, humidity_pct: 45,
    is_mvp_district: true,
  },
  {
    name: "Sukkur",
    lat: 27.70, lng: 68.86,
    temp_c: 42, wind_kmh: 10, wind_dir: "SW", wind_deg: 210,
    condition: "Hot & monsoon", icon: "🌩",
    rainfall_mm_24h: 48, humidity_pct: 62,
    is_mvp_district: true,
  },
  {
    name: "Gilgit",
    lat: 35.92, lng: 74.31,
    temp_c: 27, wind_kmh: 8, wind_dir: "NW", wind_deg: 310,
    condition: "Clear mountain", icon: "⛰",
    rainfall_mm_24h: 3, humidity_pct: 40,
    is_mvp_district: true,
  },
  {
    name: "Hyderabad",
    lat: 25.40, lng: 68.37,
    temp_c: 38, wind_kmh: 16, wind_dir: "SW", wind_deg: 215,
    condition: "Monsoon rain", icon: "🌧",
    rainfall_mm_24h: 32, humidity_pct: 70,
    is_mvp_district: false,
  },
  {
    name: "Rawalpindi",
    lat: 33.60, lng: 73.04,
    temp_c: 34, wind_kmh: 15, wind_dir: "SW", wind_deg: 225,
    condition: "Monsoon cloud", icon: "🌦",
    rainfall_mm_24h: 18, humidity_pct: 75,
    is_mvp_district: true,
  },
  {
    name: "Jacobabad",
    lat: 28.28, lng: 68.43,
    temp_c: 45, wind_kmh: 8, wind_dir: "SW", wind_deg: 200,
    condition: "Extreme heat + rain", icon: "⚠",
    rainfall_mm_24h: 62, humidity_pct: 58,
    is_mvp_district: true,
  },
  {
    name: "Larkana",
    lat: 27.56, lng: 68.21,
    temp_c: 41, wind_kmh: 9, wind_dir: "SW", wind_deg: 205,
    condition: "Heavy monsoon", icon: "🌩",
    rainfall_mm_24h: 55, humidity_pct: 65,
    is_mvp_district: true,
  },
];

/** Demo disclaimer shown with all city weather labels */
export const WEATHER_DEMO_LABEL =
  "Demo weather labels — representative monsoon season values — live weather integration planned";
