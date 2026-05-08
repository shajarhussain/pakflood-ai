// Educational data sources used in this prototype
// All links are real, publicly accessible resources for flood intelligence in Pakistan

export interface EducationalSource {
  id: string;
  name: string;
  short_name: string;
  category: "satellite" | "hydrology" | "meteorology" | "relief" | "government" | "research";
  description: string;
  url: string;
  data_type: string;
  update_frequency: string;
  access: "open" | "registration" | "api_key" | "restricted";
  used_in_system: boolean;
  planned: boolean;
}

export const EDUCATIONAL_SOURCES: EducationalSource[] = [
  {
    id: "imerg",
    name: "NASA GPM IMERG — Integrated Multi-satellitE Retrievals for GPM",
    short_name: "NASA IMERG",
    category: "satellite",
    description:
      "Near-real-time global precipitation estimates at 0.1° resolution, updated every 30 minutes. Primary rainfall data source for flood risk estimation.",
    url: "https://gpm.nasa.gov/data/imerg",
    data_type: "Rainfall raster (NetCDF / HDF5)",
    update_frequency: "30 minutes (Early run), 3.5 hours (Late run), 3.5 months (Final run)",
    access: "registration",
    used_in_system: true,
    planned: false,
  },
  {
    id: "chirps",
    name: "CHIRPS — Climate Hazards Group InfraRed Precipitation with Station Data",
    short_name: "CHIRPS",
    category: "satellite",
    description:
      "35+ year quasi-global rainfall dataset. Used for historical baseline and seasonal anomaly detection.",
    url: "https://www.chc.ucsb.edu/data/chirps",
    data_type: "Daily/monthly rainfall raster (GeoTIFF)",
    update_frequency: "Monthly (near-real-time pentadal updates)",
    access: "open",
    used_in_system: true,
    planned: false,
  },
  {
    id: "glofas",
    name: "GloFAS — Global Flood Awareness System",
    short_name: "GloFAS",
    category: "hydrology",
    description:
      "River discharge forecasts from ECMWF + Copernicus. Provides 30-day ensemble flood probability forecasts along major river networks including the Indus.",
    url: "https://global-flood.emergency.copernicus.eu/",
    data_type: "River discharge forecast (NetCDF)",
    update_frequency: "Daily",
    access: "open",
    used_in_system: true,
    planned: false,
  },
  {
    id: "pmd",
    name: "Pakistan Meteorological Department",
    short_name: "PMD",
    category: "government",
    description:
      "Official weather forecasts, monsoon bulletins, and extreme weather warnings for Pakistan. The authoritative source for official emergency decisions.",
    url: "https://www.pmd.gov.pk/",
    data_type: "Weather bulletins, forecast maps",
    update_frequency: "Daily / event-driven",
    access: "open",
    used_in_system: false,
    planned: true,
  },
  {
    id: "ffd",
    name: "Federal Flood Division — Pakistan",
    short_name: "FFD",
    category: "government",
    description:
      "River level gauging, flood forecasting, and advisory bulletins for Pakistan's major river systems under the Ministry of Water Resources.",
    url: "http://www.ffd.gov.pk/",
    data_type: "River level bulletins, flood advisories",
    update_frequency: "Daily during flood season",
    access: "open",
    used_in_system: false,
    planned: true,
  },
  {
    id: "ndma",
    name: "National Disaster Management Authority — Pakistan",
    short_name: "NDMA",
    category: "government",
    description:
      "Official disaster risk information, situation reports, and SUPARCO satellite assessments. Primary emergency management authority for Pakistan.",
    url: "https://ndma.gov.pk/",
    data_type: "Situation reports, SAR assessments",
    update_frequency: "Event-driven",
    access: "open",
    used_in_system: false,
    planned: true,
  },
  {
    id: "reliefweb",
    name: "ReliefWeb — UN OCHA",
    short_name: "ReliefWeb",
    category: "relief",
    description:
      "Curated humanitarian information including flood reports, maps, and situation updates for Pakistan. Used for contextual evidence in risk explanations.",
    url: "https://reliefweb.int/country/pak",
    data_type: "Reports, maps, infographics",
    update_frequency: "Continuous",
    access: "api_key",
    used_in_system: true,
    planned: false,
  },
  {
    id: "sentinel1",
    name: "Copernicus Sentinel-1 SAR",
    short_name: "Sentinel-1",
    category: "satellite",
    description:
      "C-band SAR satellite providing 10m resolution flood extent imagery regardless of cloud cover. Available through ESA Copernicus Open Access Hub.",
    url: "https://scihub.copernicus.eu/",
    data_type: "SAR imagery (GeoTIFF / SAFE format)",
    update_frequency: "Every 6–12 days (per orbit)",
    access: "registration",
    used_in_system: false,
    planned: true,
  },
  {
    id: "copernicus-ems",
    name: "Copernicus Emergency Management Service",
    short_name: "Copernicus EMS",
    category: "satellite",
    description:
      "Rapid mapping products for natural disasters including Pakistan floods. Provides delineation and grading maps using Sentinel-1 SAR.",
    url: "https://emergency.copernicus.eu/",
    data_type: "Flood extent polygons, damage grading maps",
    update_frequency: "On-demand (disaster activation)",
    access: "open",
    used_in_system: false,
    planned: true,
  },
  {
    id: "unosat",
    name: "UNOSAT — UNITAR Operational Satellite Applications Programme",
    short_name: "UNOSAT",
    category: "relief",
    description:
      "Satellite-derived flood maps for humanitarian response. UNOSAT produced extensive Sentinel-1 flood mapping for Pakistan 2022.",
    url: "https://unosat.org/",
    data_type: "Flood extent shapefiles, population estimates",
    update_frequency: "On-demand (disaster activation)",
    access: "open",
    used_in_system: false,
    planned: true,
  },
  {
    id: "suparco",
    name: "SUPARCO — Space & Upper Atmosphere Research Commission",
    short_name: "SUPARCO",
    category: "government",
    description:
      "Pakistan's national space agency. Provides satellite-based flood monitoring and damage assessments for NDMA and provincial governments.",
    url: "https://www.suparco.gov.pk/",
    data_type: "Satellite imagery, flood assessments",
    update_frequency: "Event-driven",
    access: "restricted",
    used_in_system: false,
    planned: true,
  },
  {
    id: "hdx-pak",
    name: "Humanitarian Data Exchange — Pakistan Datasets",
    short_name: "HDX Pakistan",
    category: "research",
    description:
      "Open humanitarian data including Pakistan administrative boundaries (used for district GeoJSON in this prototype), population data, and historical flood impact datasets.",
    url: "https://data.humdata.org/dataset?q=pakistan+flood",
    data_type: "GeoJSON, CSV, Shapefile",
    update_frequency: "Varies by dataset",
    access: "open",
    used_in_system: true,
    planned: false,
  },
  {
    id: "gee",
    name: "Google Earth Engine",
    short_name: "GEE",
    category: "research",
    description:
      "Cloud geospatial analysis platform used for processing IMERG and CHIRPS data at scale. Enables flood extent computation from SAR without local compute.",
    url: "https://earthengine.google.com/",
    data_type: "Raster analysis API",
    update_frequency: "Near-real-time",
    access: "registration",
    used_in_system: false,
    planned: true,
  },
];

export const CATEGORY_LABELS: Record<EducationalSource["category"], string> = {
  satellite: "Satellite & Remote Sensing",
  hydrology: "Hydrology & River Forecasting",
  meteorology: "Meteorology",
  relief: "Humanitarian & Relief",
  government: "Government & Official",
  research: "Research & Data Platforms",
};
