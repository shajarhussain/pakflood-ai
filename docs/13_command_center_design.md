# PakFlood AI Command Center — Product Design & Implementation Blueprint

**Flood Intelligence, Forecast Simulation & Response Planning for Pakistan**

---

## 0. Mission Statement

PakFlood AI Command Center is a professional-grade, AI-powered disaster intelligence interface for Pakistan. It synthesizes satellite rainfall data, river discharge forecasts, historical flood evidence, and ML-based risk assessment into a single dark, map-first command environment — built for situational awareness, not casual browsing.

**Safety line (always shown):**
> "Educational prototype. Not an official warning system. Always follow PMD, FFD, NDMA, PDMA, and local authorities for real emergency decisions."

---

## 1. Design Tokens

### 1.1 Color System

```typescript
// design-tokens.ts
export const colors = {
  // Backgrounds
  bg: {
    base:      "#080E1A",   // deepest navy — outer shell
    surface:   "#0D1526",   // primary surface — map panels, rails
    elevated:  "#111E35",   // card backgrounds
    overlay:   "#162040",   // glassmorphism panel base
    input:     "#1A2845",   // form inputs, selects
    hover:     "#1F2F55",   // hover states
  },

  // Brand / Hydrology
  cyan: {
    50:  "#E0F7FF",
    100: "#B8EFFF",
    400: "#22D3EE",   // primary accent — rainfall, water
    500: "#06B6D4",   // interactive elements
    600: "#0891B2",   // active/selected
    glow: "rgba(34,211,238,0.25)",
  },
  blue: {
    400: "#60A5FA",
    500: "#3B82F6",   // electric blue — AI copilot, forecast
    600: "#2563EB",
    glow: "rgba(59,130,246,0.20)",
  },

  // Risk Level Palette
  risk: {
    low:      { fill: "#22C55E", glow: "rgba(34,197,94,0.30)",  text: "#86EFAC" },
    moderate: { fill: "#F59E0B", glow: "rgba(245,158,11,0.30)", text: "#FCD34D" },
    high:     { fill: "#F97316", glow: "rgba(249,115,22,0.35)", text: "#FDBA74" },
    severe:   { fill: "#EF4444", glow: "rgba(239,68,68,0.40)",  text: "#FCA5A5" },
  },

  // Status / Semantic
  status: {
    fresh:   "#22C55E",   // source fresh
    stale:   "#F59E0B",   // source stale > 6h
    error:   "#EF4444",   // source error / circuit open
    disabled:"#6B7280",   // source not enabled in demo
    live:    "#06B6D4",   // live data active
    demo:    "#8B5CF6",   // demo/simulated mode
  },

  // Borders
  border: {
    subtle:  "rgba(255,255,255,0.06)",
    default: "rgba(255,255,255,0.10)",
    accent:  "rgba(34,211,238,0.25)",
    glow:    "rgba(34,211,238,0.50)",
  },

  // Text
  text: {
    primary:   "#F1F5F9",
    secondary: "#94A3B8",
    muted:     "#64748B",
    disabled:  "#475569",
    inverse:   "#0D1526",
  },
};
```

### 1.2 Typography

```typescript
export const typography = {
  fontFamily: {
    display: "'Inter', 'SF Pro Display', system-ui, sans-serif",
    mono:    "'JetBrains Mono', 'Fira Code', monospace",
  },
  scale: {
    "display-lg": { size: "2rem",   weight: 700, tracking: "-0.025em", line: 1.1 },
    "display-sm": { size: "1.5rem", weight: 700, tracking: "-0.02em",  line: 1.2 },
    "heading-xl": { size: "1.25rem",weight: 600, tracking: "-0.01em",  line: 1.3 },
    "heading-lg": { size: "1.125rem",weight:600, tracking: "0",        line: 1.4 },
    "heading-md": { size: "1rem",   weight: 600, tracking: "0",        line: 1.4 },
    "body-lg":    { size: "0.9375rem",weight:400,tracking: "0",        line: 1.6 },
    "body-md":    { size: "0.875rem",weight:400, tracking: "0",        line: 1.6 },
    "body-sm":    { size: "0.8125rem",weight:400,tracking: "0",        line: 1.5 },
    "label-lg":   { size: "0.75rem", weight: 600, tracking: "0.05em", line: 1.4 },
    "label-md":   { size: "0.6875rem",weight:600, tracking:"0.06em",  line: 1.4 },
    "mono-md":    { size: "0.875rem", weight: 500, tracking: "0",     line: 1.5 },
    "mono-sm":    { size: "0.75rem",  weight: 500, tracking: "0",     line: 1.5 },
  },
};
```

### 1.3 Spacing & Layout

```typescript
export const spacing = {
  // Base unit: 4px
  1:  "4px",   2:  "8px",   3:  "12px",  4:  "16px",
  5:  "20px",  6:  "24px",  7:  "28px",  8:  "32px",
  10: "40px",  12: "48px",  16: "64px",  20: "80px",
};

export const layout = {
  topBar:        "48px",    // mission header height
  statusBar:     "32px",    // source/model status bar
  leftRail:      "56px",    // icon-only layer rail (collapsed)
  leftRailOpen:  "240px",   // expanded layer control panel
  rightPanel:    "380px",   // AI Copilot panel
  rightPanelWide:"480px",   // expanded panels (Simulation Lab)
  bottomTimeline:"160px",   // historical flood timeline
  mapArea:       "calc(100vh - 80px)", // topBar + statusBar
};
```

### 1.4 Cards, Radius & Shadows

```typescript
export const cards = {
  radius: {
    sm:  "6px",
    md:  "10px",
    lg:  "14px",
    xl:  "18px",
    full:"9999px",
  },
  shadow: {
    card:    "0 4px 16px rgba(0,0,0,0.4), 0 1px 4px rgba(0,0,0,0.3)",
    panel:   "0 8px 32px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.4)",
    modal:   "0 20px 60px rgba(0,0,0,0.7)",
    glow: {
      cyan:   "0 0 20px rgba(34,211,238,0.25), 0 0 40px rgba(34,211,238,0.10)",
      blue:   "0 0 20px rgba(59,130,246,0.25), 0 0 40px rgba(59,130,246,0.10)",
      red:    "0 0 24px rgba(239,68,68,0.35), 0 0 48px rgba(239,68,68,0.15)",
      amber:  "0 0 20px rgba(245,158,11,0.30), 0 0 40px rgba(245,158,11,0.10)",
    },
  },
  glass: {
    background: "rgba(13,21,38,0.75)",
    border:     "rgba(255,255,255,0.08)",
    blur:       "backdrop-filter: blur(12px) saturate(160%)",
  },
};
```

### 1.5 Glow Effects

```css
/* Severe risk pulse — applied to district polygon fill */
@keyframes severe-pulse {
  0%, 100% { filter: drop-shadow(0 0 6px rgba(239,68,68,0.6)); opacity: 1; }
  50%       { filter: drop-shadow(0 0 20px rgba(239,68,68,0.9)); opacity: 0.85; }
}

/* High risk subtle glow */
@keyframes high-glow {
  0%, 100% { filter: drop-shadow(0 0 4px rgba(249,115,22,0.5)); }
  50%       { filter: drop-shadow(0 0 14px rgba(249,115,22,0.8)); }
}

/* Selected district focus ring */
@keyframes focus-ring {
  0%, 100% { stroke-width: 2; stroke-opacity: 1; }
  50%       { stroke-width: 3; stroke-opacity: 0.7; }
}

/* AI Copilot typing indicator */
@keyframes copilot-pulse {
  0%, 100% { opacity: 0.4; } 50% { opacity: 1; }
}

/* Source health live indicator */
@keyframes live-blink {
  0%, 100% { opacity: 1; } 50% { opacity: 0.3; }
}

/* Radar sweep */
@keyframes radar-sweep {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
```

---

## 2. Application Shell — Full Layout Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MISSION HEADER (48px)                                               [alerts] │
│  PakFlood AI Command Center  |  Pakistan  |  Source Status  |  Model Status  │
├──────────────────────────────────────────────────────────────────────────────┤
│  SOURCE/MODEL STATUS BAR (32px) — condensed live source feed                 │
├────┬─────────────────────────────────────────────────┬───────────────────────┤
│    │                                                 │                       │
│  L │              FULL-BLEED MAP                    │   AI FLOOD COPILOT    │
│  A │           (map-first, fills all)               │   RIGHT PANEL         │
│  Y │                                                 │   (380px)             │
│  E │    [floating KPI cards over map]                │                       │
│  R │    [risk layer / rainfall / river / sat]        │   [tab-based]         │
│    │    [district tooltips, focus ring]              │   Brief               │
│  R │    [animated overlays]                          │   Copilot Chat        │
│  A │                                                 │   Simulation          │
│  I │                                                 │   Response Plan       │
│  L │                                                 │   Evidence            │
│    │                                                 │                       │
│(56)│                                                 │                       │
├────┴─────────────────────────────────────────────────┴───────────────────────┤
│  BOTTOM: HISTORICAL FLOOD TIMELINE (160px) — collapsible                     │
│  [2010] ── [2011] ── [2014] ── [2022] with event footprint toggle            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Left Layer Rail (collapsed 56px / expanded 240px)

| Icon | Label (expanded) | Description |
|---|---|---|
| 🗺 | Risk Zones | District flood risk color fill |
| 🌧 | Rainfall Intensity | IMERG-style heat overlay + rain animation |
| 🌊 | River Discharge | Animated river-flow lines |
| 📜 | Historical Events | Flood footprint overlays |
| 👥 | Exposure / Impact | Population + infrastructure |
| 🛰 | Satellite Preview | SAR/Sentinel scan overlay |
| ❤️ | Source Health | Data source status markers |

Each layer toggle has:
- active/inactive pill indicator
- source badge (IMERG, GloFAS, etc.)
- data freshness dot (green / amber / red)
- "demo mode" label where applicable

---

## 3. Mission Header Component

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⬡ PakFlood AI         Pakistan Flood Intelligence    [🔴 SEVERE] [🟡 HIGH]  │
│   COMMAND CENTER      Forecast · Simulation · Response  2 districts active   │
│                                              [Docs] [Admin] [?] [◐ Demo Mode]│
└──────────────────────────────────────────────────────────────────────────────┘
```

Elements:
- **Brand mark** — cyan hexagon glyph + "PakFlood AI" in 700 weight + "COMMAND CENTER" in label-md cyan uppercase tracking
- **System subtitle** — "Pakistan Flood Intelligence · Forecast · Simulation · Response"
- **Active alert pills** — floating `[🔴 SEVERE: 2]` `[🟡 HIGH: 3]` badges with glow
- **Navigation links** — Docs, Admin, Help as minimal ghost buttons
- **Demo Mode indicator** — amber pill `◐ Demo Mode — educational prototype` (always visible in demo)

---

## 4. Source / Model Status Bar

```
SOURCES: ●IMERG stale 4h  ●CHIRPS fresh  ●GloFAS fresh  ●ReliefWeb live  ●FFD demo  ●SAR planned
MODEL: RandomForest baseline-v1.0  |  AUC 0.71  |  Districts: 10  |  Last run: 3 min ago
```

Design:
- Fixed 32px bar, `bg-base`, subtle bottom border
- Sources as inline chips: colored dot + source name + freshness label
- Circuit breaker state shown via icon (✓ closed / ⚠ half / ✕ open)
- Model version and last inference timestamp
- All monospaced text, label-sm

---

## 5. Full-Bleed Command Map

### 5.1 Map Tile Style
- Base tiles: **CartoDB DarkMatter** (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`) — gives dark navy water, graphite land
- Pakistan border: bright cyan `#22D3EE`, stroke 2.5px
- Province borders: `rgba(255,255,255,0.12)`, stroke 1px dashed
- District borders: `rgba(255,255,255,0.07)`, stroke 0.5px — more visible on hover/select

### 5.2 Floating KPI Cards (over map, bottom-left cluster)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  DISTRICTS   │  │  SEVERE RISK │  │ RAINFALL     │  │  SOURCE      │
│  MONITORED   │  │  ZONES       │  │  ANOMALY     │  │  HEALTH      │
│     10       │  │   2 active   │  │  +340% avg   │  │  4/6 fresh   │
│  MVP dataset │  │  ● pulsing   │  │  sim. 7-day  │  │  ●●●●○○     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

Each KPI card:
- `bg-overlay / glass` style with `backdrop-blur`
- colored top border (cyan for informational, amber for warning, red for severe)
- heading-md value + label-md subtitle
- no close button — they stay pinned

### 5.3 District Interaction States

| State | Fill | Border | Label | Effect |
|---|---|---|---|---|
| **Default** | Risk-level color @ 60% opacity | 0.5px white/7% | Hidden | None |
| **Hover** | Risk-level color @ 85% opacity | 1.5px white/20% | Name label appears | Cursor: pointer, shadow under card |
| **Selected** | Risk-level color @ 100% | 2.5px cyan, animated | Bold name | Focus ring pulse animation, right panel opens |
| **Severe** | `#EF4444` fill + glow | 2px red + outer glow | Name always visible | `severe-pulse` animation |
| **High** | `#F97316` fill | 1.5px orange | Name visible | `high-glow` subtle animation |
| **Rainfall mode** | Semi-transparent cyan heat | Blue gradient | Rainfall mm badge | Rain animation overlay |
| **River mode** | Neutral fill | Standard | Flow lines animate | Discharge meter tooltip |
| **Historical event** | Sepia/amber tint + hatch | Amber border | Event year badge | Hover shows event card |
| **Satellite** | Partially transparent | White dashed | SAR badge | Scan overlay pseudo-image |
| **Source stale** | Muted + diagonal lines | Amber dashed | ⚠ stale badge | Warning tooltip |
| **Source error** | Grey-out overlay | Red dashed | ✕ error badge | Error tooltip |

### 5.4 District Tooltip (on hover)

```
┌─────────────────────────────────────────┐
│  SUKKUR · SINDH                    🔴   │
│  Risk Score: 0.85      SEVERE           │
│  Confidence: 74%       ▓▓▓▓▓▓▓░░ 74%   │
│                                         │
│  7-day rainfall: +320% anomaly          │
│  River pressure: HIGH (sim)             │
│  Historical: flooded 2010, 2022         │
│                                         │
│  [Click to open AI Copilot →]           │
└─────────────────────────────────────────┘
```

---

## 6. Rainfall Intelligence Layer

### Visual Design

**Rain Effect (canvas/CSS animation):**
```css
/* Rain particles — rendered on <canvas> over the map */
/* Each particle: thin diagonal white-blue line, 40-80px, 15-20° angle */
/* Speed: 200-400ms per particle, staggered */
/* Density scales with rainfall anomaly level: */
/*   Low: 30 particles  Moderate: 80  High: 150  Severe: 250 */
/* Color: rgba(34, 211, 238, 0.4) at base, brighter in high-anomaly zones */
```

**Rainfall Heat Overlay:**
- Canvas layer over map districts
- Color gradient: `transparent → rgba(34,211,238,0.15) → rgba(34,211,238,0.45) → rgba(59,130,246,0.70)`
- Interpolated per district from `rainfall_1d` / `rainfall_7d` fields
- Label: `"IMERG-style rainfall simulation · Live mode disabled in demo"`

**District Rainfall Badges (visible on layer activation):**
```
┌──────────────────────┐
│  SUKKUR              │
│  1d  ████ 48mm       │
│  3d  ██████ 142mm    │
│  7d  ██████████ 320mm│
│  Anomaly: +340% ↑    │
└──────────────────────┘
```

**Rainfall Mini-Chart (in right panel):**
- 14-day bar chart, bars colored by intensity
- Baseline average line (dashed amber)
- Anomaly shading above baseline
- Labeled: "Prototype simulation · IMERG baseline educational model"

---

## 7. River Discharge Intelligence Layer

### Visual Design

**Animated River Lines:**
- SVG polylines along major Pakistan rivers: Indus, Jhelum, Chenab, Ravi, Sutlej
- Line width scales with discharge level: Normal 2px, Watch 3px, High 4.5px, Severe 6px
- Animated dashes flowing downstream using `stroke-dashoffset` animation:
  ```css
  @keyframes river-flow {
    from { stroke-dashoffset: 100; }
    to   { stroke-dashoffset: 0; }
  }
  /* Speed: Normal 3s, Watch 2s, High 1.5s, Severe 0.8s */
  ```
- Color: Normal `#60A5FA`, Watch `#F59E0B`, High `#F97316`, Severe `#EF4444`

**Discharge Meter (right panel):**
```
┌──────────────────────────────────────┐
│  INDUS AT SUKKUR                     │
│  GloFAS Alert Level                  │
│  ○─────────────────────●─────○       │
│  Normal    Watch    HIGH   Severe    │
│                                      │
│  Discharge: ~8,400 m³/s (sim)        │
│  Upstream pressure: ELEVATED         │
│  Source: GloFAS-ERA5 simulation      │
│  "Live source disabled in demo mode" │
└──────────────────────────────────────┘
```

**Upstream Pressure Indicator:**
- Animated fill gauge: 0–100% fill, color-coded
- Label: "Hydrological pressure relative to 10-year baseline"

---

## 8. AI Flood Copilot — Right Panel

### Panel Structure (tabbed)

```
┌─────────────────────────────────────────────────────┐
│  AI FLOOD COPILOT                            ✕ [⤢]  │
│  Sukkur · Sindh                     ● Model active  │
│  ──────────────────────────────────────────────────  │
│  [Brief] [Copilot] [Simulate] [Response] [Evidence] │
├─────────────────────────────────────────────────────┤
│                   TAB CONTENT                        │
└─────────────────────────────────────────────────────┘
```

### Tab 1: Executive Risk Brief

```
RISK ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴  SEVERE FLOOD RISK
    Score: 0.85 / 1.00
    Confidence: 74%
    Model: RandomForest baseline-v1.0
    Window: 72-hour forecast horizon

SOURCE HEALTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMERG        ● stale (4h)    rainfall
CHIRPS       ✓ fresh         anomaly
GloFAS       ✓ fresh         discharge
ReliefWeb    ✓ live          articles
FFD/PMD      ○ demo mode     bulletins

WHY THIS DISTRICT IS HIGH RISK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃ 7-day rainfall anomaly     ████████░ 0.91
┃ Near Indus floodplain      ███████░░ 0.78
┃ Historical flood frequency ██████░░░ 0.65
┃ Low elevation + slope      █████░░░░ 0.52
┃ High population density    ████░░░░░ 0.44

RAINFALL SIGNAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [14-day mini bar chart with baseline]
  Current 7d: +320% above baseline
  "IMERG-style simulation / live disabled"

RIVER DISCHARGE SIGNAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Discharge level meter]
  GloFAS level: HIGH
  Upstream: ELEVATED pressure

HISTORICAL EXPOSURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Severely flooded: 2010, 2011, 2022
  3 major events in 12 years
  → matches current signature

CONFIDENCE & LIMITATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  74% confidence
  Uncertainty sources:
  ⚠ IMERG data stale (4h)
  ⚠ Synthetic training data
  ⚠ No real-time PMD bulletins
  
  Operational validation requires
  official satellite + gauge datasets.

─────────────────────────────────────
⚠ Educational prototype.
  Not an official warning.
  Follow PMD · FFD · NDMA · PDMA.
─────────────────────────────────────
```

### Tab 2: AI Copilot Chat Interface

```
┌─────────────────────────────────────────────────────┐
│  FLOOD COPILOT                    baseline-v1.0 ●   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ 🤖 Sukkur has HIGH–SEVERE flood risk. The main  │ │
│  │    drivers are extreme 7-day rainfall anomaly   │ │
│  │    (+320%), proximity to the Indus floodplain,  │ │
│  │    and 3 major flood events since 2010...       │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  [Quick Actions]                                     │
│  ┌──────────────────┐ ┌──────────────────┐           │
│  │ 📢 Explain simply │ │ 🏃 Citizen steps  │           │
│  └──────────────────┘ └──────────────────┘           │
│  ┌──────────────────┐ ┌──────────────────┐           │
│  │ 🏛 Authority mon. │ │ ❓ Why limited?   │           │
│  └──────────────────┘ └──────────────────┘           │
│  ┌──────────────────┐ ┌──────────────────┐           │
│  │ 📊 Data missing?  │ │ 📄 Draft advisory │           │
│  └──────────────────┘ └──────────────────┘           │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ Ask about Sukkur...                     [→]  │   │
│  └──────────────────────────────────────────────┘   │
│  ⚠ AI responses are educational. Not official.      │
└─────────────────────────────────────────────────────┘
```

**Quick Action responses (deterministic rule-based, pre-computed):**

- **Explain simply** → "Sukkur is at severe flood risk because there has been extreme rainfall over 7 days — about 3× more than normal. The Indus River is flowing at high levels. This area has flooded badly before in 2010 and 2022."
- **What should citizens do?** → checklist: store water, charge devices, know evacuation route, avoid low-lying roads, follow NDMA/PDMA alerts
- **What should authorities monitor?** → river gauge at Sukkur barrage, early warning from FFD, review 2010 event evacuation routes
- **Why is confidence limited?** → stale IMERG, synthetic training data, no PMD live feed
- **What data is missing?** → live river gauge readings, PMD bulletin, current SAR imagery, real FFD discharge data
- **Generate draft advisory** → formatted advisory text (see Response Planner section)

### Tab 3: Forecast Simulation Lab

```
┌─────────────────────────────────────────────────────┐
│  WHAT-IF SIMULATION LAB                    ⚗ DEMO   │
│  "Prototype simulation — not official prediction"   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  SCENARIO PRESETS                                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ +25% Rainfall│ │ +50% Rainfall│ │ River Rising │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ Sources Stale│ │ Night Evac.  │ │ Road Blocked │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ │
│                                                      │
│  MANUAL CONTROLS                                     │
│  Rainfall intensity                                  │
│  ├──────────────●──────────────────┤ +25%           │
│                                                      │
│  River discharge level                               │
│  ├──────────────────●──────────────┤ HIGH           │
│                                                      │
│  Source freshness                                    │
│  ○ All fresh  ● Mixed  ○ All stale                   │
│                                                      │
│  PROJECTED IMPACT                                    │
│  ─────────────────────────────────────────────────  │
│  Risk score:      0.85 → 0.91  (+0.06) ↑           │
│  Confidence:      74%  → 61%   (-13%)  ↓           │
│  Risk level:      SEVERE (unchanged)                 │
│  Action priority: RESPONSE → EVACUATION ↑           │
│                                                      │
│  MINI-MAP PREVIEW                                    │
│  [thumbnail map showing simulated risk shift]        │
│                                                      │
│  ASSUMPTIONS                                         │
│  "All values are prototype simulations based        │
│   on baseline RandomForest model weights.           │
│   Not a calibrated hydrological model."             │
└─────────────────────────────────────────────────────┘
```

### Tab 4: Response Plan

```
┌─────────────────────────────────────────────────────┐
│  AI RESPONSE PLANNER          Sukkur · SEVERE       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  RESPONSE PRIORITY SCORE: 91 / 100                  │
│  ████████████████████████████████████░░░░           │
│                                                      │
│  CITIZEN PREPAREDNESS                                │
│  ─────────────────────────────────────────────────  │
│  ☐ Store 72h water supply in sealed containers      │
│  ☐ Charge all devices and power banks               │
│  ☐ Prepare emergency kit (documents, medicine)      │
│  ☐ Know nearest elevated evacuation shelter         │
│  ☐ Avoid travel on low-lying flood roads            │
│  ☐ Follow NDMA, PDMA, and local authority alerts    │
│                                                      │
│  LOCAL AUTHORITY ACTIONS                             │
│  ─────────────────────────────────────────────────  │
│  ☐ Monitor Sukkur Barrage gauge readings (FFD)      │
│  ☐ Pre-position rescue boats at high-risk wards     │
│  ☐ Review 2010 / 2022 event evacuation routes       │
│  ☐ Alert district PDMA for resource pre-staging     │
│  ☐ Ensure hospital backup power is tested           │
│                                                      │
│  MONITORING PRIORITY                                 │
│  ─────────────────────────────────────────────────  │
│  ☐ GloFAS discharge: next 24h update                │
│  ☐ PMD rainfall bulletin: next advisory             │
│  ☐ FFD river level alert threshold                  │
│  ☐ ReliefWeb: incoming situation reports            │
│                                                      │
│  VULNERABLE POPULATION                               │
│  ─────────────────────────────────────────────────  │
│  ● Rural Sindh communities near Indus banks          │
│  ● Agricultural workers — low mobility               │
│  ● Informal settlements at elevation < 10m           │
│  Source: historical 2010/2022 impact patterns        │
│                                                      │
│  DRAFT ADVISORY PREVIEW                              │
│  ─────────────────────────────────────────────────  │
│  ┌───────────────────────────────────────────────┐  │
│  │ [EDUCATIONAL DRAFT — NOT OFFICIAL]            │  │
│  │ FLOOD INTELLIGENCE ALERT — SUKKUR, SINDH     │  │
│  │ Issued: PakFlood AI Command Center (demo)    │  │
│  │                                               │  │
│  │ Current risk level: SEVERE (score 0.85)      │  │
│  │ Confidence: 74% | Model: baseline-v1.0       │  │
│  │                                               │  │
│  │ Key factors: extreme 7-day rainfall anomaly, │  │
│  │ Indus floodplain proximity, 3 prior events.  │  │
│  │                                               │  │
│  │ ⚠ Follow PMD, FFD, NDMA, PDMA for official  │  │
│  │   emergency instructions.                    │  │
│  └───────────────────────────────────────────────┘  │
│  [Copy] [Download PDF]                               │
└─────────────────────────────────────────────────────┘
```

### Tab 5: Evidence Pack

```
┌─────────────────────────────────────────────────────┐
│  EVIDENCE & SOURCE PACK          Sukkur · SEVERE    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  IMERG RAINFALL CARD                                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ 🛰 NASA GPM IMERG              ● stale (4h)   │  │
│  │ Role: Primary rainfall signal                 │  │
│  │ 1d: 48mm | 3d: 142mm | 7d: 320mm             │  │
│  │ 7d anomaly: +340% above 10yr baseline         │  │
│  │ [14-day rainfall bar chart mini]              │  │
│  │ Status: "Live source disabled in demo mode"   │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  GLOFAS DISCHARGE CARD                               │
│  ┌───────────────────────────────────────────────┐  │
│  │ 💧 GloFAS (ECMWF)              ✓ fresh        │  │
│  │ Role: River discharge forecast                │  │
│  │ Alert level: HIGH                             │  │
│  │ ~8,400 m³/s Indus at Sukkur (sim)            │  │
│  │ Upstream: ELEVATED 72h pressure               │  │
│  │ [Discharge level gauge]                       │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  RELIEFWEB INTELLIGENCE CARD                         │
│  ┌───────────────────────────────────────────────┐  │
│  │ 📰 ReliefWeb / OCHA            ✓ live         │  │
│  │ Role: Humanitarian situation reports          │  │
│  │ [Article title + excerpt + link]              │  │
│  │ Source confidence: available where ≥0.6       │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  CHIRPS ANOMALY CARD                                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ 🌍 CHIRPS (UCSB)               ✓ fresh        │  │
│  │ Role: Seasonal rainfall baseline              │  │
│  │ 30-year baseline for anomaly calc             │  │
│  │ Current anomaly: +2.8σ (extreme)              │  │
│  │ "Baseline educational model"                  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  HISTORICAL EVENT MATCH                              │
│  ┌───────────────────────────────────────────────┐  │
│  │ 📜 2010 Pakistan Floods — Sindh               │  │
│  │ Sukkur severely inundated July–Aug 2010       │  │
│  │ Indus overtopped, 1.5M affected in Sindh      │  │
│  │ Current signature matches 2010 pre-event      │  │
│  │ [View full Atlas entry →]                     │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  SATELLITE / SAR PREVIEW                             │
│  ┌───────────────────────────────────────────────┐  │
│  │ 🛰 Sentinel-1 SAR             ○ planned       │  │
│  │ [Greyscale radar scan SVG placeholder]        │  │
│  │ "Satellite/SAR detection planned for v2"      │  │
│  │ "Operational validation requires ESA feeds"   │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 9. Historical Flood Atlas — Expanded Section

Accessed from bottom timeline **or** left nav "Historical" section. Full-screen overlay or side panel expansion.

### Atlas Layout

```
┌──────────────────────────────────────────────────────────────┐
│  HISTORICAL FLOOD ATLAS — Pakistan                   [✕ map] │
│  "Every major flood leaves a signature. Learn to read it."   │
├─────────────┬────────────────────────────────────────────────┤
│  TIMELINE   │                                                 │
│             │   CASE STUDY: 2022 PAKISTAN FLOODS             │
│  ● 2010     │   "The Worst Flooding in Modern History"        │
│    Indus    │                                                 │
│    overflow │  ┌─────────────────────────────────────────┐   │
│             │  │ [event footprint map of affected         │   │
│  ● 2011     │  │  provinces — amber/red fill overlay]    │   │
│    Sindh    │  │  Sindh / KP / Balochistan / Punjab      │   │
│    repeat   │  └─────────────────────────────────────────┘   │
│             │                                                 │
│  ● 2014     │  CAUSES                                        │
│    Punjab   │  ● Record monsoon: 190% above 30-yr baseline   │
│    Chenab   │  ● La Niña intensified monsoon trough          │
│             │  ● Glacial melt added upstream discharge       │
│  ● 2022  ← │  ● Persistent low-pressure system over Sindh   │
│    All prov │                                                 │
│             │  IMPACT                                        │
│             │  ● 33M people affected                         │
│  [+ 2024?]  │  ● ~1,700 fatalities                          │
│    future   │  ● 2M homes destroyed                          │
│             │  ● $30B estimated economic damage              │
│             │  ● 700K+ displaced in Sindh alone              │
│             │                                                 │
│             │  LESSONS LEARNED                               │
│             │  ● Early warning: FFD bulletins 48h in advance │
│             │  ● Barrage operations: critical decision point  │
│             │  ● Sindh particularly vulnerable: flat terrain  │
│             │  ● NDMA pre-staging was underutilized          │
│             │                                                 │
│             │  CURRENT DISTRICT COMPARISON                   │
│             │  Sukkur today vs Sukkur pre-2022:              │
│             │  Rainfall anomaly: similar signature            │
│             │  River level: lower (but rising)               │
│             │  "Not a prediction — historical context only"  │
├─────────────┴────────────────────────────────────────────────┤
│  [← 2014] [2010] [2011] [2014] [2022] [2024 →]    [compare] │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. Data Sources Observatory — Full Section

```
┌──────────────────────────────────────────────────────────────┐
│  DATA SOURCES OBSERVATORY                                     │
│  "Where the intelligence comes from"                         │
├──────────────────────────────────────────────────────────────┤
│  PIPELINE DIAGRAM                                             │
│                                                               │
│  [IMERG]──┐                                                   │
│  [CHIRPS]─┼──► [Adapters + Circuit Breaker]                  │
│  [GloFAS]─┤         │                                         │
│  [Relief]─┤         ▼                                         │
│  [FFD]────┘    [Source Registry]                             │
│                     │                                         │
│                     ▼                                         │
│               [Feature Builder]                               │
│                     │                                         │
│                     ▼                                         │
│              [ML Risk Model]                                  │
│                     │                                         │
│                     ▼                                         │
│             [Explainer / RAG]                                 │
│                     │                                         │
│                     ▼                                         │
│                  [UI / API]                                   │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  SOURCE CARDS (grid)                                          │
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ 🛰 NASA GPM IMERG        │  │ 🌍 CHIRPS (UCSB)         │   │
│  │ Status: ● stale 4h       │  │ Status: ✓ fresh          │   │
│  │ Freshness: 4h ago         │  │ Freshness: 2h ago         │   │
│  │ Confidence: 0.72          │  │ Confidence: 0.80          │   │
│  │ Circuit: ✓ CLOSED         │  │ Circuit: ✓ CLOSED         │   │
│  │ Role: rainfall primary    │  │ Role: baseline anomaly    │   │
│  │ Features: rain_1d/3d/7d   │  │ Features: chirps_anomaly  │   │
│  │ Limit: 4h latency         │  │ Limit: 5-day delay        │   │
│  │ [● live] [stub enabled]   │  │ [● live] [stub enabled]   │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ 💧 GloFAS (ECMWF)        │  │ 📰 ReliefWeb / OCHA      │   │
│  │ Status: ✓ fresh          │  │ Status: ✓ live           │   │
│  │ Freshness: 1h ago         │  │ Freshness: 30min ago      │   │
│  │ Confidence: 0.78          │  │ Confidence: 0.65          │   │
│  │ Circuit: ✓ CLOSED         │  │ Circuit: ✓ CLOSED         │   │
│  │ Role: discharge forecast  │  │ Role: situational intel   │   │
│  │ Features: discharge_level │  │ Features: article context │   │
│  │ Limit: forecast ±20%      │  │ Limit: text quality var.  │   │
│  │ [● live] [stub enabled]   │  │ [● live] [live API]       │   │
│  └─────────────────────────┘  └─────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ 📡 FFD / PMD             │  │ 🛰 Sentinel SAR (ESA)    │   │
│  │ Status: ○ demo mode      │  │ Status: ○ planned        │   │
│  │ "Live source disabled"    │  │ "Satellite/SAR detection │   │
│  │ in demo mode"             │  │  planned for v2"         │   │
│  │ Role: official bulletins  │  │ Role: flood extent map   │   │
│  │ Limit: requires auth      │  │ Limit: ESA Copernicus    │   │
│  │ [○ demo] [stub only]     │  │ [○ planned] [not enabled]│   │
│  └─────────────────────────┘  └─────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Model & Limitations — Professional Presentation

```
┌──────────────────────────────────────────────────────────────┐
│  ML MODEL OBSERVATORY                                         │
│  "Architecture-first baseline — production path defined"     │
├──────────────────────────────────────────────────────────────┤
│  MODEL CARD                                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ RandomForest Flood Risk Classifier                    │    │
│  │ Version: baseline-v1.0                                │    │
│  │ Training data: synthetic seed (10 districts)          │    │
│  │ Features: 8 static + 4 dynamic                        │    │
│  │ AUC-ROC: 0.71 | Accuracy: 0.74                       │    │
│  │ Precision: 0.72 | Recall: 0.69                        │    │
│  │ Training date: [auto from artifact]                   │    │
│  │ Label: "Baseline educational model"                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  FEATURE IMPORTANCE                                           │
│  rain_7d_anomaly    ████████████████░░░░ 0.42               │
│  dist_to_river      ████████████░░░░░░░░ 0.31               │
│  flood_freq_hist    ████████░░░░░░░░░░░░ 0.18               │
│  elevation_norm     █████░░░░░░░░░░░░░░░ 0.14               │
│  discharge_level    ████░░░░░░░░░░░░░░░░ 0.12               │
│  pop_density_norm   ███░░░░░░░░░░░░░░░░░ 0.09               │
│  rain_1d_mm         ██░░░░░░░░░░░░░░░░░░ 0.07               │
│  slope_mean         █░░░░░░░░░░░░░░░░░░░ 0.04               │
│                                                               │
│  PRODUCTION READINESS                                         │
│  ☑ Clean architecture (Strategy Pattern)                     │
│  ☑ Version + artifact + metrics stored                       │
│  ☑ Explainable (top-3 SHAP factors)                          │
│  ☑ Fallback to rule-based if model absent                    │
│  ☐ Real training data (requires IMERG/CHIRPS/GloFAS API)    │
│  ☐ ≥140 district coverage (MVP = 10)                         │
│  ☐ Time-series cross-validation                              │
│  ☐ External expert validation                                │
│                                                               │
│  LIMITATIONS — HONESTLY STATED                               │
│  "Synthetic training data: model learned from seeded values, │
│   not real measured flood events. Risk scores are            │
│   illustrative. AUC of 0.71 on synthetic holdout overstates  │
│   real-world readiness. Operational deployment requires      │
│   official satellite datasets, hydrological gauge readings,  │
│   and expert validation."                                    │
│                                                               │
│  UPGRADE PATH                                                 │
│  v2: XGBoost + real IMERG/CHIRPS training data               │
│  v3: LSTM sequence model for 7-day time series               │
│  v4: U-Net flood extent segmentation (SAR/satellite)         │
└──────────────────────────────────────────────────────────────┘
```

---

## 12. Future Hazards Preview

```
┌──────────────────────────────────────────────────────────────┐
│  HAZARD MODULE REGISTRY          1 active · 6 planned        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 🌊 FLOODS     │  │ 🌡 HEATWAVES  │  │ 🏔 LANDSLIDES│       │
│  │ ● ACTIVE      │  │ ○ planned    │  │ ○ planned    │       │
│  │ 10 districts  │  │              │  │              │       │
│  │ RF baseline   │  │ LST + MODIS  │  │ Slope + rain │       │
│  │ IMERG/GloFAS  │  │ CHIRPS temp  │  │ DEM + soil   │       │
│  │ Full MVP      │  │ WHO guidance │  │ ALOS-PALSAR  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 🧊 GLOF       │  │ 🌵 DROUGHT   │  │ 🏙 URBAN FLD  │       │
│  │ ○ planned    │  │ ○ planned    │  │ ○ planned    │       │
│  │              │  │              │  │              │       │
│  │ ICIMOD data  │  │ SPI/SPEI     │  │ DEM + drain  │       │
│  │ MODIS ice    │  │ CHIRPS SMA   │  │ OSM + NDWI   │       │
│  │ GB districts │  │ FAO SoilM    │  │ City focus   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  ┌──────────────┐                                            │
│  │ ⚠ EARTHQUAKE │                                            │
│  │ ○ planned    │                                            │
│  │ USGS ShakeMap│                                            │
│  │ PMD seismic  │                                            │
│  │ Building exp.│                                            │
│  └──────────────┘                                            │
│                                                               │
│  Plugin architecture: each hazard is a HazardModule plugin.  │
│  Adding a new hazard = implement Protocol, register in       │
│  HazardModuleFactory. Zero changes to core platform.         │
└──────────────────────────────────────────────────────────────┘
```

---

## 13. Search & Navigation — Smart District Search

```
┌──────────────────────────────────────────────────────────────┐
│  🔍 Search districts, provinces, rivers...           [⌘K]    │
└──────────────────────────────────────────────────────────────┘

Result card (in dropdown):
┌──────────────────────────────────────────────────────────────┐
│  SUKKUR                                              🔴 SEVERE│
│  Sindh Province  ·  MVP dataset  ·  Risk score: 0.85         │
│  Sources: IMERG ● CHIRPS ✓ GloFAS ✓                          │
└──────────────────────────────────────────────────────────────┘

Out-of-scope message (e.g. Karachi):
┌──────────────────────────────────────────────────────────────┐
│  KARACHI                                                      │
│  ○ Outside current 10-district MVP dataset                   │
│  Full Pakistan district coverage is planned.                 │
│  [View MVP districts →]                                      │
└──────────────────────────────────────────────────────────────┘
```

The search input (`⌘K` keyboard shortcut):
- Matches district name, province, river name
- Shows risk badge, province, source status inline
- "Included in MVP" green badge for the 10 seeded districts
- Out-of-scope districts shown in grey with a clear "not in dataset" message — never erroneously selected
- Province-level search groups results by province heading

---

## 14. Animation Specifications

### 14.1 Rainfall Effect

```typescript
// RainCanvas.tsx — <canvas> overlay rendered on top of map
interface RainParticle {
  x: number;       // canvas X
  y: number;       // canvas Y
  speed: number;   // 3–6 px/frame
  length: number;  // 40–80px
  opacity: number; // 0.2–0.5
}

// Density by risk level:
const PARTICLE_COUNT = { Low: 30, Moderate: 80, High: 150, Severe: 250 };

// Angle: 15–20° from vertical (diagonal effect)
// Color: rgba(34, 211, 238, opacity) — cyan rain
// Reset: when particle exits bottom, respawn at top with random X
// Frame rate: requestAnimationFrame at 60fps, throttle to 30fps on low-perf
```

### 14.2 River Flow Animation

```css
.river-line {
  stroke-dasharray: 12 6;
  animation: river-flow var(--flow-speed) linear infinite;
}
/* --flow-speed: Normal=3s, Watch=2s, High=1.2s, Severe=0.6s */

@keyframes river-flow {
  from { stroke-dashoffset: 36; }
  to   { stroke-dashoffset: 0; }
}
```

### 14.3 Radar Sweep (Evidence section)

```css
.radar-sweep {
  position: absolute;
  width: 100%; height: 100%;
  background: conic-gradient(
    from 0deg,
    transparent 330deg,
    rgba(34,211,238,0.6) 355deg,
    rgba(34,211,238,0.2) 360deg
  );
  animation: radar-sweep 4s linear infinite;
  transform-origin: center;
}
```

### 14.4 Severe Risk Pulse (map polygon)

```css
/* Applied as SVG filter on Leaflet GeoJSON layer */
.district-severe {
  animation: severe-pulse 2s ease-in-out infinite;
}
/* severity pulse defined in Section 1.5 above */
```

### 14.5 Flood Wave Simulation (Evidence section)

```css
/* Expanding concentric rings — SVG circles */
.flood-wave circle {
  fill: none;
  stroke: rgba(34,211,238,0.5);
  stroke-width: 2;
  animation: flood-expand 3s ease-out infinite;
}
.flood-wave circle:nth-child(2) { animation-delay: 1s; }
.flood-wave circle:nth-child(3) { animation-delay: 2s; }

@keyframes flood-expand {
  from { r: 0; opacity: 0.8; }
  to   { r: 80; opacity: 0; }
}
```

### 14.6 Source Live Indicator

```css
.source-live-dot {
  animation: live-blink 1.5s ease-in-out infinite;
  border-radius: 50%;
  width: 8px; height: 8px;
}
/* color set by status: green=fresh, amber=stale, red=error */
```

---

## 15. Component Inventory

### Map Components

| Component | File | Description |
|---|---|---|
| `CommandMap` | `components/map/CommandMap.tsx` | Main Leaflet wrapper, layer management |
| `RiskLayer` | `components/map/RiskLayer.tsx` | District GeoJSON fill by risk level |
| `RainfallLayer` | `components/map/RainfallLayer.tsx` | Canvas heat overlay + rain animation |
| `RiverLayer` | `components/map/RiverLayer.tsx` | SVG river flow lines + discharge coloring |
| `HistoricalLayer` | `components/map/HistoricalLayer.tsx` | Event footprint overlays |
| `SatelliteLayer` | `components/map/SatelliteLayer.tsx` | SAR preview placeholder overlay |
| `SourceHealthLayer` | `components/map/SourceHealthLayer.tsx` | Per-district source status markers |
| `RainCanvas` | `components/map/RainCanvas.tsx` | Canvas rain particle animation |
| `DistrictTooltip` | `components/map/DistrictTooltip.tsx` | Hover tooltip with risk summary |
| `MapLegend` | `components/map/MapLegend.tsx` | Risk level legend (always visible) |
| `KPICards` | `components/map/KPICards.tsx` | Floating KPI cluster over map |
| `LayerRail` | `components/map/LayerRail.tsx` | Left collapsed/expanded layer rail |

### AI Copilot Panel Components

| Component | File | Description |
|---|---|---|
| `CopilotPanel` | `components/copilot/CopilotPanel.tsx` | Tab container, district header |
| `RiskBrief` | `components/copilot/RiskBrief.tsx` | Executive summary tab |
| `CopilotChat` | `components/copilot/CopilotChat.tsx` | Chat + quick action buttons |
| `SimulationLab` | `components/copilot/SimulationLab.tsx` | What-if sliders + scenario presets |
| `ResponsePlan` | `components/copilot/ResponsePlan.tsx` | Checklists + draft advisory |
| `EvidencePack` | `components/copilot/EvidencePack.tsx` | Source evidence cards |
| `RainfallChart` | `components/copilot/RainfallChart.tsx` | 14-day bar chart (recharts) |
| `DischargeMeter` | `components/copilot/DischargeMeter.tsx` | GloFAS level gauge |
| `FactorBars` | `components/copilot/FactorBars.tsx` | Top-factor horizontal bars |
| `ConfidenceGauge` | `components/copilot/ConfidenceGauge.tsx` | Confidence score arc |

### Layout & Shell Components

| Component | File | Description |
|---|---|---|
| `AppShell` | `components/layout/AppShell.tsx` | Full layout grid manager |
| `MissionHeader` | `components/layout/MissionHeader.tsx` | Top bar with branding + alert pills |
| `StatusBar` | `components/layout/StatusBar.tsx` | Source/model status strip |
| `SafetyDisclaimer` | `components/layout/SafetyDisclaimer.tsx` | Always-visible warning bar |
| `AlertPill` | `components/layout/AlertPill.tsx` | Severity count badge |

### Historical Atlas Components

| Component | File | Description |
|---|---|---|
| `FloodAtlas` | `components/atlas/FloodAtlas.tsx` | Full atlas section container |
| `EventCard` | `components/atlas/EventCard.tsx` | Case-study card (2010, 2011...) |
| `AtlasTimeline` | `components/atlas/AtlasTimeline.tsx` | Year timeline nav |
| `EventMap` | `components/atlas/EventMap.tsx` | Event footprint mini-map |
| `DistrictCompare` | `components/atlas/DistrictCompare.tsx` | Current vs historical comparison |

### Data Observatory Components

| Component | File | Description |
|---|---|---|
| `SourcesObservatory` | `components/observatory/SourcesObservatory.tsx` | Full sources section |
| `SourceCard` | `components/observatory/SourceCard.tsx` | Per-source status card |
| `PipelineDiagram` | `components/observatory/PipelineDiagram.tsx` | SVG pipeline flow |
| `CircuitStatus` | `components/observatory/CircuitStatus.tsx` | Circuit breaker state indicator |
| `ModelObservatory` | `components/observatory/ModelObservatory.tsx` | Model card + feature importance |
| `FeatureImportanceChart` | `components/observatory/FeatureImportanceChart.tsx` | Horizontal bar chart |

### Evidence Media Components

| Component | File | Description |
|---|---|---|
| `RadarSweep` | `components/media/RadarSweep.tsx` | CSS/SVG radar animation |
| `FloodWave` | `components/media/FloodWave.tsx` | SVG concentric wave animation |
| `SARPreview` | `components/media/SARPreview.tsx` | Greyscale SAR-style placeholder |
| `RainfallRadar` | `components/media/RainfallRadar.tsx` | Animated radar heat canvas |

### UI Primitives (shadcn-based / custom)

| Component | File | Description |
|---|---|---|
| `GlassCard` | `components/ui/GlassCard.tsx` | Glassmorphism card wrapper |
| `StatusDot` | `components/ui/StatusDot.tsx` | Colored dot with blink animation |
| `RiskBadge` | `components/ui/RiskBadge.tsx` | Risk level pill with glow |
| `DemoBadge` | `components/ui/DemoBadge.tsx` | "Demo mode" purple badge |
| `LiveBadge` | `components/ui/LiveBadge.tsx` | "Live" cyan badge |
| `SourceBadge` | `components/ui/SourceBadge.tsx` | Source name + freshness |
| `ConfidenceBar` | `components/ui/ConfidenceBar.tsx` | Progress bar for confidence |
| `ScoreGauge` | `components/ui/ScoreGauge.tsx` | Arc gauge (risk score, response priority) |
| `QuickActionBtn` | `components/ui/QuickActionBtn.tsx` | Copilot quick-action button |
| `Checklist` | `components/ui/Checklist.tsx` | Checkbox list with categories |

---

## 16. Implementation Notes — Next.js + Tailwind

### 16.1 Tailwind Configuration Extension

```typescript
// tailwind.config.ts additions
export default {
  theme: {
    extend: {
      colors: {
        navy: { 950: "#080E1A", 900: "#0D1526", 800: "#111E35", 700: "#162040" },
        cyan: { DEFAULT: "#22D3EE" },
      },
      animation: {
        "severe-pulse": "severe-pulse 2s ease-in-out infinite",
        "high-glow":    "high-glow 2.5s ease-in-out infinite",
        "radar-sweep":  "radar-sweep 4s linear infinite",
        "river-flow":   "river-flow 2s linear infinite",
        "live-blink":   "live-blink 1.5s ease-in-out infinite",
        "flood-expand": "flood-expand 3s ease-out infinite",
      },
      backdropBlur: { xs: "4px" },
      boxShadow: {
        "glow-cyan": "0 0 20px rgba(34,211,238,0.25), 0 0 40px rgba(34,211,238,0.10)",
        "glow-red":  "0 0 24px rgba(239,68,68,0.35), 0 0 48px rgba(239,68,68,0.15)",
      },
    },
  },
};
```

### 16.2 Leaflet Layer Management

```typescript
// Leaflet layers use React refs + useEffect for imperative control.
// Pattern: each layer component receives `map: L.Map` and `active: boolean` props.
// On `active` true: add to map. On `active` false: remove from map.
// GeoJSON risk layer: L.GeoJSON with `style()` function reading risk_level.
// Canvas layers: custom L.Layer subclass using createTile/onAdd/onRemove.
// River SVG: L.SVGOverlay with animated <line> elements.
// Always add layers in z-order: base tiles → satellite → risk → rainfall → rivers → labels.
```

### 16.3 State Architecture

```typescript
// Global state via Zustand (lightweight, no Context boilerplate)
interface MapStore {
  activeLayers: Set<LayerKey>;
  selectedDistrictId: string | null;
  rightPanelTab: CopilotTab;
  simulationParams: SimulationParams;
  atlasEventYear: number | null;
  toggleLayer: (key: LayerKey) => void;
  selectDistrict: (id: string | null) => void;
  setRightPanelTab: (tab: CopilotTab) => void;
}
```

### 16.4 API Integration Pattern

```typescript
// All data fetching via /lib/api.ts with mock fallback.
// New hooks pattern:
// useDistrictRisk(districtId) → ApiRiskResponse + loading + error
// useSourceStatus() → ApiDataSource[] + staleness detection
// useSimulation(params) → computed SimulationResult (client-side, no API call)
// useFloodEvents(districtId?) → ApiFloodEvent[]
// All hooks: SWR or TanStack Query with 60s revalidation.
```

### 16.5 Chart Library

Use **Recharts** (already React-native, no SSR issues):
- `BarChart` for 14-day rainfall, feature importance
- `AreaChart` for discharge over time
- `RadialBarChart` for confidence gauge
- All charts: custom dark theme matching design tokens

### 16.6 Performance

- Map tiles: loaded lazily via Leaflet (native)
- Rain canvas: `requestAnimationFrame` throttled to 30fps on battery-saver / reduced motion
- Right panel: lazy-load heavy tabs (Simulation, Observatory) via `next/dynamic`
- Historical atlas: lazy load on first open
- GeoJSON: ~10 districts = small, no chunking needed for MVP

### 16.7 Prefers-Reduced-Motion

```typescript
// All animation components check:
const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// If true: skip rain canvas, skip pulse animations, keep static glow
```

---

## 17. Testing Checklist

### Component Tests (Vitest + RTL)

- [ ] `MissionHeader` renders brand, subtitle, demo badge
- [ ] `StatusBar` shows all source names and freshness labels
- [ ] `RiskBrief` renders all 5 sections for a mock district
- [ ] `FactorBars` renders correct bar widths from factor weights
- [ ] `SimulationLab` sliders update projected risk score
- [ ] `ResponsePlan` renders all 3 checklists + draft advisory
- [ ] `EvidencePack` renders all 5 source cards
- [ ] `SourceCard` shows correct status dot, freshness, circuit state
- [ ] `EventCard` renders 2022 event correctly
- [ ] `GlassCard`, `RiskBadge`, `StatusDot` render correct colors per level
- [ ] Safety disclaimer always visible (not conditionally hidden)
- [ ] Out-of-scope search message shown for Karachi

### E2E Tests (Playwright)

- [ ] Page loads, no console errors
- [ ] Safety disclaimer visible on load
- [ ] Map container visible with district polygons
- [ ] Legend shows Low / Moderate / High / Severe
- [ ] Search "Sukkur" → listbox appears → click opens copilot panel
- [ ] Copilot panel shows risk score, confidence, top factors
- [ ] Simulation tab: moving rainfall slider updates projected risk
- [ ] Response plan tab shows checklist items
- [ ] Evidence tab shows IMERG, GloFAS, ReliefWeb cards
- [ ] Historical atlas: clicking 2022 shows event card with provinces
- [ ] Layer rail: toggling rainfall layer shows rain canvas
- [ ] Layer rail: toggling river shows animated river lines
- [ ] Search "Karachi" shows out-of-scope message, does not select district
- [ ] Disclaimer remains visible after district click
- [ ] All tabs in copilot panel are navigable by keyboard

### Accessibility

- [ ] All interactive elements have `aria-label`
- [ ] Map has `role="application"` + keyboard district nav
- [ ] Risk level conveyed as text + color + icon (not color alone)
- [ ] Color contrast ≥ 4.5:1 for all text on dark backgrounds
- [ ] Focus rings visible on all interactive elements
- [ ] Animated elements respect `prefers-reduced-motion`

### Security

- [ ] No API keys hardcoded in frontend source
- [ ] No `dangerouslySetInnerHTML` without sanitization
- [ ] CSP headers set in `next.config.ts`
- [ ] `npm audit` at level high: 0 issues

---

## 18. Screenshot Checklist for Demo

| # | Screen | Description |
|---|---|---|
| 01 | `01_command_center_overview.png` | Full dashboard, Severe district selected, all KPI cards visible |
| 02 | `02_map_risk_zones.png` | Risk color fill, severe district glowing, district tooltip open |
| 03 | `03_rainfall_layer_active.png` | Rainfall heat overlay + rain animation screenshot + district badges |
| 04 | `04_river_layer_active.png` | Animated river flow lines, discharge meter in copilot panel |
| 05 | `05_copilot_brief_tab.png` | AI Copilot: Executive Brief with all 5 sections, confidence bar |
| 06 | `06_copilot_chat_tab.png` | Copilot Chat: quick action buttons, AI response visible |
| 07 | `07_simulation_lab.png` | Simulation Lab: sliders, scenario buttons, projected risk shift |
| 08 | `08_response_plan.png` | Response Plan: all 3 checklists, draft advisory, priority score |
| 09 | `09_evidence_pack.png` | Evidence Pack: all 5 source cards with status and charts |
| 10 | `10_historical_atlas_2022.png` | Historical Atlas: 2022 event card, footprint map, impact summary |
| 11 | `11_sources_observatory.png` | Data Sources Observatory: all 6 source cards + pipeline diagram |
| 12 | `12_model_observatory.png` | Model card: feature importance chart, production readiness checklist |
| 13 | `13_future_hazards.png` | Future Hazards: 7 module cards, 1 active (floods), 6 planned |
| 14 | `14_smart_search.png` | Search open: Sukkur result with risk badge, Karachi out-of-scope |
| 15 | `15_mobile_responsive.png` | Mobile viewport: map full-screen, bottom sheet copilot panel |
| 16 | `16_disclaimer_always_visible.png` | Any state: disclaimer strip clearly visible at bottom |

---

## 19. Priority Implementation Order

Given the existing working codebase, implement in this order for maximum demo impact:

1. **Design tokens** — `design-tokens.ts`, update `tailwind.config.ts` (1 hour)
2. **AppShell + MissionHeader** — replace current header with branded command-center header (2 hours)
3. **StatusBar** — source/model status strip under header (1 hour)
4. **GlassCard + UI primitives** — RiskBadge, StatusDot, DemoBadge, ConfidenceBar (2 hours)
5. **LayerRail** — left icon rail with layer toggles (2 hours)
6. **KPICards** — floating cards over map (1 hour)
7. **RainCanvas** — rain particle animation + rainfall layer (3 hours)
8. **RiverLayer** — SVG river flow animation (2 hours)
9. **DistrictTooltip** — redesigned hover card with all fields (1 hour)
10. **CopilotPanel** — full right panel with all 5 tabs (6 hours)
11. **SimulationLab** — sliders + scenario logic (2 hours)
12. **FloodAtlas** — historical event section (3 hours)
13. **SourcesObservatory + ModelObservatory** — data/model sections (3 hours)
14. **FutureHazards** — preview cards (1 hour)
15. **SmartSearch** — enhanced search with out-of-scope handling (1 hour)
16. **E2E tests** — update all Playwright tests for new UI (2 hours)
17. **Screenshots** — capture all 16 demo screenshots (30 min)

**Total estimate: ~33 hours of focused implementation.**

---

*Document version: 1.0 — PakFlood AI Command Center Design Blueprint*
*Classification: educational prototype — not an official warning system*
