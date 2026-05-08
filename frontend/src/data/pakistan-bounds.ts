// Pakistan geographic constants — used for map bounds locking and grid generation

/** Tight bounding box: [west, south, east, north] in decimal degrees */
export const PAKISTAN_BBOX = [60.8, 23.5, 77.2, 37.2] as [number, number, number, number];

/** Leaflet-style bounds [[south, west], [north, east]] */
export const PAKISTAN_BOUNDS = [
  [23.5, 60.8],
  [37.2, 77.2],
] as [[number, number], [number, number]];

/** Slightly padded max-bounds for Leaflet — prevents panning far outside */
export const PAKISTAN_MAX_BOUNDS = [
  [19.5, 55.0],
  [40.5, 81.0],
] as [[number, number], [number, number]];

/** Default map center [lat, lng] */
export const PAKISTAN_CENTER: [number, number] = [30.3753, 69.3451];

/** Zoom levels */
export const MAP_MIN_ZOOM = 4;
export const MAP_MAX_ZOOM = 14;
export const MAP_DEFAULT_ZOOM = 6;

/** Approximate Indus River waypoints [lat, lng] for proximity calculations */
export const INDUS_WAYPOINTS: [number, number][] = [
  [36.5, 74.5], // Gilgit region
  [34.5, 72.8], // KP north
  [33.2, 72.0], // Attock area
  [31.5, 71.2], // Jhang / Punjab
  [30.2, 71.0], // Multan area
  [28.5, 70.3], // Guddu Barrage
  [27.7, 68.8], // Sukkur Barrage
  [26.5, 68.0], // Sehwan
  [25.5, 67.8], // Kotri Barrage
  [24.5, 67.5], // Hyderabad
  [23.9, 67.4], // near Thatta / sea
];

/** Province rough bounding polygons (used for labelling only) */
export const PROVINCE_LABELS = [
  { name: "Sindh",              lat: 26.0, lng: 68.5 },
  { name: "Punjab",             lat: 30.5, lng: 72.5 },
  { name: "Balochistan",        lat: 28.5, lng: 65.0 },
  { name: "KP",                 lat: 34.0, lng: 71.5 },
  { name: "Gilgit-Baltistan",   lat: 36.0, lng: 74.5 },
  { name: "AJK",                lat: 33.8, lng: 73.8 },
];
