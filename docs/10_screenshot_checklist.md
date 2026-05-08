# Screenshot Checklist — PakFlood AI Demo

Use this checklist before any presentation or submission to verify the UI is demo-ready.

---

## 1. Map loads correctly

- [ ] Dark navy/charcoal background visible
- [ ] Pakistan outline rendered with at least 10 district polygons
- [ ] All 10 districts colored (no grey/blank districts)
- [ ] Risk colors follow Low (green) → Moderate (yellow) → High (orange) → Severe (red) gradient
- [ ] No console errors in browser DevTools

---

## 2. Safety disclaimer visible

- [ ] SafetyDisclaimer banner visible on initial load (above or below map)
- [ ] Disclaimer text includes "PMD", "NDMA", and "educational"
- [ ] Banner is not dismissible (always visible)

---

## 3. Map legend visible

- [ ] MapLegend shows all four risk levels: Low, Moderate, High, Severe
- [ ] Each level has both a color swatch AND a text label (color-blind-safe)
- [ ] Legend is always visible — not hidden behind panels

---

## 4. District hover card

- [ ] Hovering over a district shows a hover card
- [ ] Card shows: district name, province, risk score, risk level
- [ ] Card disappears when mouse leaves the district

---

## 5. District click → explanation panel

- [ ] Clicking a district opens the RiskExplanationPanel on the right
- [ ] Panel shows: Risk Level badge, Confidence score, Top Factors list
- [ ] Panel shows: Data Sources section with freshness badges
- [ ] Panel shows: Limitations / Disclaimer section
- [ ] Panel does NOT claim to be an "official warning"

---

## 6. Layer control panel

- [ ] LayerControlPanel visible on the left
- [ ] Toggling risk layer hides/shows district risk colors
- [ ] Boundary layer toggle works
- [ ] Panel labels are readable (dark background)

---

## 7. Flood timeline

- [ ] FloodTimeline bar visible at the bottom of the map
- [ ] At least 4 events shown: 2010, 2011, 2014, 2022
- [ ] Clicking an event highlights affected districts or shows event details

---

## 8. Source badges (data freshness)

- [ ] SourceBadge components visible on the data-sources page or panel
- [ ] Each badge shows: source name, status (stale/fresh/error), circuit state
- [ ] Stale status styled differently from fresh (color or icon)

---

## 9. Admin run-risk-model

- [ ] POST `/api/v1/admin/run-risk-model` returns 200
- [ ] Response includes `assessments` array with 10 items
- [ ] Response includes `persisted_count`, `persistence_status`
- [ ] Response includes `feature_snapshot` with `rainfall_1d_mm`, `river_discharge_m3s`

---

## 10. Mobile viewport (optional)

- [ ] UI usable at 375×667px (iPhone SE)
- [ ] Map fills viewport, legend and disclaimer still visible
- [ ] Panels stack vertically without overflow

---

## Screenshot filenames

Save screenshots with these names for the submission package:

```
screenshots/
  01_map_overview.png
  02_disclaimer_banner.png
  03_legend.png
  04_hover_card.png
  05_explanation_panel.png
  06_layer_controls.png
  07_flood_timeline.png
  08_source_badges.png
  09_admin_api_response.png
  10_mobile_viewport.png
```
