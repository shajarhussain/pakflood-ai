// SAR (Synthetic Aperture Radar) evidence references — educational/real sources only
// No fabricated detections. All entries reference real published datasets or papers.

export interface SarReference {
  id: string;
  title: string;
  source: string;
  url: string;
  date: string;              // publication or data date
  region: string;
  flood_event: string;
  data_type: "satellite_imagery" | "published_paper" | "open_dataset" | "agency_report";
  sensor: string;
  resolution_m: number | null;
  description: string;
  access: "open" | "registration" | "restricted";
}

export const SAR_REFERENCES: SarReference[] = [
  {
    id: "copernicus-2022-ems",
    title: "Copernicus EMS — Pakistan Floods 2022 Rapid Mapping Products",
    source: "European Union Copernicus Emergency Management Service",
    url: "https://emergency.copernicus.eu/mapping/list-of-components/EMSR624",
    date: "2022-08-30",
    region: "Sindh, Balochistan, KP",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "open_dataset",
    sensor: "Sentinel-1 SAR (C-band)",
    resolution_m: 10,
    description:
      "Delineation maps from Sentinel-1 SAR showing flood extent across provinces. Activation EMSR624 covers southern Pakistan.",
    access: "open",
  },
  {
    id: "unosat-2022-flood",
    title: "UNOSAT Flood Extent Maps — Pakistan 2022",
    source: "UNITAR-UNOSAT",
    url: "https://unosat.org/products/3596",
    date: "2022-09-06",
    region: "Sindh",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "open_dataset",
    sensor: "Sentinel-1 SAR + optical",
    resolution_m: 10,
    description:
      "SAR-derived flood maps produced by UNOSAT showing approximately one-third of Sindh inundated at peak flooding.",
    access: "open",
  },
  {
    id: "nasa-dfo-2022",
    title: "NASA Disaster Flood Observatory — Pakistan 2022 Flood",
    source: "NASA / Dartmouth Flood Observatory",
    url: "https://floodmap.modaps.eosdis.nasa.gov/",
    date: "2022-08-28",
    region: "Indus River Basin",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "open_dataset",
    sensor: "MODIS (optical) + SAR composite",
    resolution_m: 250,
    description:
      "Near-real-time flood extent mapping using MODIS satellite imagery composited with SAR data for cloud penetration.",
    access: "open",
  },
  {
    id: "sentinel-hub-2022",
    title: "Sentinel Hub — Pakistan Flood Monitoring August 2022",
    source: "Sentinel Hub (ESA / Sinergise)",
    url: "https://www.sentinel-hub.com/",
    date: "2022-08-01",
    region: "Pakistan (national)",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "satellite_imagery",
    sensor: "Sentinel-1 SAR C-band (IW mode)",
    resolution_m: 10,
    description:
      "Freely accessible Sentinel-1 SAR imagery available via Sentinel Hub EO Browser for educational and research use.",
    access: "open",
  },
  {
    id: "ndma-2022-report",
    title: "NDMA Pakistan Flood 2022 — Situation Reports",
    source: "National Disaster Management Authority Pakistan",
    url: "https://ndma.gov.pk/",
    date: "2022-10-01",
    region: "Pakistan (national)",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "agency_report",
    sensor: "Multi-source (SUPARCO SAR + optical)",
    resolution_m: null,
    description:
      "NDMA situation reports including SUPARCO satellite assessments. SUPARCO provides SAR-based flood mapping for national emergency response.",
    access: "open",
  },
  {
    id: "science-2010-flood",
    title: "The Exceptional Summer 2010 Flooding in Pakistan (Houze et al.)",
    source: "Science Magazine / AAAS",
    url: "https://doi.org/10.1126/science.1207773",
    date: "2011-02-11",
    region: "Pakistan (KP, Punjab, Sindh)",
    flood_event: "Pakistan Floods 2010",
    data_type: "published_paper",
    sensor: "TRMM TMI + SAR analysis",
    resolution_m: null,
    description:
      "Peer-reviewed analysis of the 2010 Pakistan flood using satellite precipitation and SAR-derived extent data. Documents ~20 million displaced.",
    access: "restricted",
  },
  {
    id: "reliefweb-2022-sar-analysis",
    title: "Flood Analysis using SAR Data — Pakistan 2022 (REACH)",
    source: "REACH Initiative / ReliefWeb",
    url: "https://reliefweb.int/report/pakistan/flood-extent-analysis-satellite-imagery-pakistan-august-2022",
    date: "2022-09-15",
    region: "Sindh, Balochistan",
    flood_event: "Pakistan Mega-Floods 2022",
    data_type: "agency_report",
    sensor: "Sentinel-1 SAR",
    resolution_m: 10,
    description:
      "REACH Initiative analysis of Sentinel-1 SAR-derived flood extent. Estimated 7.6 million acres inundated in Sindh alone.",
    access: "open",
  },
];

/** SAR availability note shown in UI */
export const SAR_INTEGRATION_NOTE =
  "Live SAR imagery integration requires direct Copernicus/SUPARCO API access — planned for v2. " +
  "Current references link to publicly available SAR datasets from Sentinel-1, UNOSAT, and NASA DFO.";
