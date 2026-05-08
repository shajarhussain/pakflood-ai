# HCI / GUI Design System

## Design Philosophy

**Map-first, explanation-second, action-third.**

Users should understand risk before reading any text. A user must be able to:
1. Find their district
2. Understand why risk is high
3. See confidence and sources
4. Identify next actions

…in under 60 seconds.

## Visual Style Guide

| Element | Specification |
|---|---|
| Background | Dark navy / charcoal (`#0f172a` / `#1e293b`) |
| Water / flood layers | Blue / cyan (`#06b6d4`, `#0891b2`) |
| Risk: Low | Green `#22c55e` |
| Risk: Moderate | Yellow `#eab308` |
| Risk: High | Orange `#f97316` |
| Risk: Severe | Red `#ef4444` |
| Cards | Glassmorphism with high contrast (`bg-slate-900/90 border border-slate-700`) |
| Risk display | Color + label + icon (never color alone — color-blind accessibility) |
| Warning hierarchy | Information → Watch → Warning → Severe |
| Language | English first; Urdu/local-language emergency summaries later |
| Tone | Calm, actionable — avoid fear-based wording |

## Layout

```
┌─────────────────────────────────────────────────────────┐
│ Safety Disclaimer Banner (always visible)               │
├────────────────────────────────────────────────────────-┤
│ Header: PakFlood AI                                     │
├───────────┬───────────────────────────┬─────────────────┤
│ Layer     │                           │ Risk Explanation │
│ Control   │    Pakistan Map           │ Panel            │
│ Panel     │    (Leaflet / Mapbox)     │ (opens on click) │
│           │                           │                  │
├───────────┴───────────────────────────┴─────────────────┤
│ Flood Timeline Slider (2010 / 2011 / 2014 / 2022)       │
└─────────────────────────────────────────────────────────┘
```

## Components

- `PakistanMap` — Leaflet map wrapper, district GeoJSON overlay
- `RiskLayer` — applies risk color to each district polygon
- `DistrictHoverCard` — tooltip on mouseover: risk score, level, rainfall, river proximity
- `MapLegend` — always visible, color + label + icon
- `RiskExplanationPanel` — 7-field schema: risk, causes, evidence, actions, confidence, sources, disclaimer
- `LayerControlPanel` — toggleable layers (risk, boundaries, rainfall, satellite)
- `FloodTimeline` — horizontal slider for historical events
- `SafetyDisclaimer` — always visible banner at top of page
- `SourceBadge` — fresh/stale/error status per data source

## Accessibility Requirements

- Keyboard navigation for all interactive elements
- Color contrast ≥ 4.5:1 for all text
- Risk shown as color + label + icon (not color alone)
- Map has `aria-label`
- Legend has text labels readable by screen reader
- `SafetyDisclaimer` uses `role="alert"`

## Reference Dashboards

- Google Flood Hub / Crisis Response — simple public-facing flood map with disclaimer
- GDACS — multi-hazard alert list with severity
- Copernicus EMS / GloFAS — professional geospatial hazard layers
- Ushahidi — crowdsourced crisis reporting on maps
