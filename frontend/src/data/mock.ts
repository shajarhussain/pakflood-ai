import type { RiskLevel, RiskExplanation } from "@/lib/types";

export interface MockRiskEntry {
  district_id: string;
  name: string;
  province: string;
  center: [number, number]; // [lat, lng]
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  top_factors: string[];
}

export interface MockFloodEvent {
  id: string;
  year: number;
  title: string;
  affected_provinces: string[];
  affected_districts: string[];
  peak_month: string;
  estimated_affected: number;
  description: string;
  damage_usd_billion?: number;
}

export const MOCK_RISK: MockRiskEntry[] = [
  {
    district_id: "PK-SD-SKR",
    name: "Sukkur",
    province: "Sindh",
    center: [27.7, 68.86],
    risk_score: 0.82,
    risk_level: "High",
    confidence: 0.74,
    top_factors: ["7-day rainfall anomaly", "near Indus floodplain", "historical flood frequency"],
  },
  {
    district_id: "PK-SD-JCB",
    name: "Jacobabad",
    province: "Sindh",
    center: [28.28, 68.43],
    risk_score: 0.91,
    risk_level: "Severe",
    confidence: 0.81,
    top_factors: ["extreme monsoon rainfall", "flat terrain", "2022 flood history"],
  },
  {
    district_id: "PK-SD-LRK",
    name: "Larkana",
    province: "Sindh",
    center: [27.56, 68.21],
    risk_score: 0.76,
    risk_level: "Severe",
    confidence: 0.7,
    top_factors: ["river proximity", "drainage capacity", "antecedent wetness"],
  },
  {
    district_id: "PK-PB-MUL",
    name: "Multan",
    province: "Punjab",
    center: [30.2, 71.44],
    risk_score: 0.55,
    risk_level: "High",
    confidence: 0.65,
    top_factors: ["Chenab river proximity", "historical events", "rainfall 7d"],
  },
  {
    district_id: "PK-PB-RWP",
    name: "Rawalpindi",
    province: "Punjab",
    center: [33.6, 73.04],
    risk_score: 0.28,
    risk_level: "Low",
    confidence: 0.6,
    top_factors: ["low rainfall", "elevated terrain", "drainage infrastructure"],
  },
  {
    district_id: "PK-PB-LHR",
    name: "Lahore",
    province: "Punjab",
    center: [31.55, 74.36],
    risk_score: 0.38,
    risk_level: "Moderate",
    confidence: 0.62,
    top_factors: ["urban drainage", "moderate rainfall", "river proximity"],
  },
  {
    district_id: "PK-KP-PSH",
    name: "Peshawar",
    province: "KPK",
    center: [34.01, 71.58],
    risk_score: 0.42,
    risk_level: "Moderate",
    confidence: 0.58,
    top_factors: ["Kabul river", "monsoon tail", "historical events"],
  },
  {
    district_id: "PK-BL-QTA",
    name: "Quetta",
    province: "Balochistan",
    center: [30.18, 67.0],
    risk_score: 0.35,
    risk_level: "Moderate",
    confidence: 0.55,
    top_factors: ["flash flood risk", "arid terrain runoff", "infrastructure"],
  },
  {
    district_id: "PK-BL-NAS",
    name: "Naseerabad",
    province: "Balochistan",
    center: [28.9, 68.28],
    risk_score: 0.88,
    risk_level: "Severe",
    confidence: 0.78,
    top_factors: ["2022 flood history", "low elevation", "Indus floodplain"],
  },
  {
    district_id: "PK-GB-GIL",
    name: "Gilgit",
    province: "Gilgit-Baltistan",
    center: [35.92, 74.31],
    risk_score: 0.22,
    risk_level: "Low",
    confidence: 0.52,
    top_factors: ["glacial melt risk", "elevated terrain", "seasonal snow"],
  },
];

export const MOCK_FLOOD_EVENTS: MockFloodEvent[] = [
  {
    id: "evt-2010-super-floods",
    year: 2010,
    title: "2010 Pakistan Super Floods",
    affected_provinces: ["KPK", "Punjab", "Sindh", "Balochistan"],
    affected_districts: ["Nowshera", "Charsadda", "Sukkur", "Larkana", "Jacobabad", "Naseerabad"],
    peak_month: "August",
    estimated_affected: 20000000,
    description:
      "One of the worst floods in Pakistan's history. ~One-fifth of Pakistan's land area was underwater at peak. 20M+ people affected.",
  },
  {
    id: "evt-2011-sindh-floods",
    year: 2011,
    title: "2011 Sindh Floods",
    affected_provinces: ["Sindh", "Balochistan"],
    affected_districts: ["Larkana", "Jacobabad", "Naseerabad", "Sukkur"],
    peak_month: "September",
    estimated_affected: 9000000,
    description:
      "Heavy monsoon rains caused severe flooding in southern Pakistan. 9M+ displaced, large areas of agricultural land damaged.",
  },
  {
    id: "evt-2014-punjab-floods",
    year: 2014,
    title: "2014 Pakistan Floods",
    affected_provinces: ["Punjab"],
    affected_districts: ["Multan", "Lahore"],
    peak_month: "September",
    estimated_affected: 2500000,
    description: "Heavy monsoon rains caused flooding in central Punjab, with the Chenab and Ravi rivers overflowing.",
  },
  {
    id: "evt-2022-record-floods",
    year: 2022,
    title: "2022 Catastrophic Floods",
    affected_provinces: ["Sindh", "Balochistan", "KPK", "Punjab"],
    affected_districts: ["Jacobabad", "Sukkur", "Larkana", "Naseerabad", "Multan", "Peshawar"],
    peak_month: "August",
    estimated_affected: 33000000,
    damage_usd_billion: 14.9,
    description:
      "Unprecedented floods affecting 1/3 of Pakistan. 33M+ affected. USD 14.9B in damages (World Bank PDNA). Linked to climate change.",
  },
];

export const DISCLAIMER =
  "PakFlood AI is an educational decision-support prototype. Always consult official PMD, FFD, NDMA, and PDMA sources for real emergency decisions.";

const RISK_ACTIONS: Record<RiskLevel, string[]> = {
  Low: [
    "Monitor official weather forecasts",
    "Check local authority advisories",
    "Review household emergency plan",
  ],
  Moderate: [
    "Follow PMD and NDMA advisories closely",
    "Prepare emergency supplies (water, documents, medicine)",
    "Identify nearest evacuation routes",
    "Stay alert to river level announcements",
  ],
  High: [
    "Follow all official evacuation orders immediately",
    "Move to higher ground if near rivers or low-lying areas",
    "Contact PDMA/local authority for shelter information",
    "Avoid crossing flooded roads or streams",
    "Keep emergency contacts ready (NDMA helpline: 1700)",
  ],
  Severe: [
    "EVACUATE immediately if instructed by authorities",
    "Call NDMA emergency helpline: 1700",
    "Do not return home until official all-clear",
    "Avoid all floodwater — even 15 cm can sweep a person",
    "Follow ONLY official PMD, FFD, NDMA, PDMA warnings",
  ],
};

const HISTORICAL_BY_DISTRICT: Record<string, string[]> = {
  Sukkur: ["Severely flooded in 2010 and 2011", "Affected in 2022 catastrophic floods"],
  Jacobabad: ["Among hardest-hit in 2010, 2011, 2022", "Historically prone to extreme riverine flooding"],
  Larkana: ["Flooded in 2010, 2011, 2022", "Located in Indus floodplain with high exposure"],
  Multan: ["Affected by Chenab river floods in 2014", "Central Punjab flood corridor"],
  Naseerabad: ["Among worst-hit in 2022 Balochistan floods", "Low-lying Kachhi plain, very high exposure"],
  Peshawar: ["Kabul river flooding in 2010", "KPK flash flood events"],
  Lahore: ["Urban flooding events during intense monsoon", "Ravi river proximity"],
  Rawalpindi: ["Generally lower flood exposure", "Urban drainage challenges during intense rain"],
  Quetta: ["Flash flood risk from arid terrain runoff", "Periodic urban flooding"],
  Gilgit: ["Glacial lake outburst flood (GLOF) risk", "Seasonal snow-melt induced river rises"],
};

export function buildMockExplanation(entry: MockRiskEntry): RiskExplanation {
  const historical = HISTORICAL_BY_DISTRICT[entry.name] ?? ["Historical flood data unavailable for this district"];
  return {
    risk_level: entry.risk_level,
    main_causes: entry.top_factors,
    historical_evidence: historical,
    suggested_actions: RISK_ACTIONS[entry.risk_level],
    confidence: entry.confidence,
    data_sources: [
      "IMERG-style rainfall (educational demo · live source planned)",
      "Seed flood event data (2010–2022, HDX Pakistan)",
      "PMD/FFD bulletin status (demo mode · official integration planned)",
    ],
    disclaimer: DISCLAIMER,
  };
}

export const RISK_BY_ID = new Map<string, MockRiskEntry>(MOCK_RISK.map((d) => [d.district_id, d]));
export const RISK_BY_NAME = new Map<string, MockRiskEntry>(MOCK_RISK.map((d) => [d.name, d]));
