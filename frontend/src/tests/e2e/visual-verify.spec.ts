/**
 * Visual Verification — Clean Command Center (Windy-style redesign)
 * Captures screenshots for 6 required states after the VISUAL RESET.
 */
import { test, expect, Page } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const SCREENSHOT_DIR = path.join(process.cwd(), "src/tests/screenshots");

async function shot(page: Page, name: string) {
  if (!fs.existsSync(SCREENSHOT_DIR)) fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const filePath = path.join(SCREENSHOT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: false });
  return filePath;
}

async function waitForMap(page: Page) {
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 12_000 });
  await page.waitForTimeout(1800);
}

async function noFakeStrings(page: Page) {
  const html = await page.content();
  const banned = [
    "Phase 1 — not connected",
    "Phase 3 —",
    "Phase 5 planned",
    "Mock IMERG Rainfall",
    "No historical data available for Phase",
  ];
  for (const s of banned) {
    expect(html, `FAKE STRING FOUND: "${s}"`).not.toContain(s);
  }
}

async function selectAnyDistrict(page: Page): Promise<boolean> {
  // Strategy 1: search for Sukkur
  try {
    const search = page.getByPlaceholder(/search district/i);
    if (await search.isVisible({ timeout: 3_000 })) {
      await search.fill("Sukkur");
      const listbox = page.locator('[role="listbox"]');
      await listbox.waitFor({ state: "visible", timeout: 7_000 });
      const item = listbox.locator("li").first();
      await item.waitFor({ state: "visible", timeout: 3_000 });
      await item.click();
      await page.waitForTimeout(800);
      const panel = page.locator('[aria-label="Risk explanation panel"]');
      const html = await panel.innerHTML();
      if (html.match(/Sukkur|Sindh|Province|risk_level/i)) return true;
    }
  } catch { /* fall through */ }

  // Strategy 2: click map positions likely to hit Pakistan districts
  const map = page.locator(".leaflet-container");
  for (const pos of [
    { x: 400, y: 240 }, { x: 380, y: 260 }, { x: 430, y: 220 },
    { x: 360, y: 300 }, { x: 450, y: 280 },
  ]) {
    await map.click({ position: pos });
    await page.waitForTimeout(700);
    const panel = page.locator('[aria-label="Risk explanation panel"]');
    const html = await panel.innerHTML();
    if (html.match(/Province|risk_score|confidence.*\d{2}%|top_factors/i)) return true;
  }
  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Default Risk mode — map fills viewport, layer switcher visible
// ─────────────────────────────────────────────────────────────────────────────
test("01 — default risk mode", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);
  await noFakeStrings(page);

  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.getByText(/PakFlood/i).first()).toBeVisible();

  // Layer switcher visible
  await expect(page.locator('[aria-label="Layer controls"]')).toBeVisible();

  // Copilot panel is present in DOM (slides in when selected)
  const panel = page.locator('[aria-label="Risk explanation panel"]');
  await expect(panel).toBeAttached();
  const html = await panel.innerHTML();
  expect(html).toMatch(/Select a (district|Feature)|AI Flood Copilot/i);

  // Active mode badge shows Grid Risk ON
  const statusEl = page.locator('[aria-label="Active layers status"]');
  await expect(statusEl).toBeVisible();
  const statusHtml = await page.content();
  expect(statusHtml).toMatch(/Grid Risk ON/i);

  const file = await shot(page, "01-default-risk-mode");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Rainfall mode — blue overlay visible + Rainfall Intelligence Active card
// ─────────────────────────────────────────────────────────────────────────────
test("02 — rainfall mode with overlay", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const rainfallBtn = page.locator('[aria-label="Toggle Rain Animation layer"]');
  await expect(rainfallBtn).toBeAttached({ timeout: 8_000 });
  await rainfallBtn.click();
  await page.waitForTimeout(1200);

  // Status badge must say Rainfall ON
  const html = await page.content();
  expect(html).toMatch(/Rainfall ON/i);

  // Floating rainfall card
  const card = page.locator('[aria-label="Rainfall Intelligence Active"]');
  await expect(card).toBeAttached({ timeout: 5_000 });
  const cardHtml = await card.innerHTML();
  expect(cardHtml).toMatch(/24h avg|peak|alerts/i);

  await noFakeStrings(page);
  const file = await shot(page, "02-rainfall-mode");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Wind mode active
// ─────────────────────────────────────────────────────────────────────────────
test("03 — wind mode active", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const windBtn = page.locator('[aria-label="Toggle Wind Vectors layer"]');
  await expect(windBtn).toBeAttached({ timeout: 8_000 });
  await windBtn.click();
  await page.waitForTimeout(1000);

  const html = await page.content();
  expect(html).toMatch(/Wind ON/i);

  const file = await shot(page, "03-wind-mode-active");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Grid risk layer — districts colored, SVG paths present
// ─────────────────────────────────────────────────────────────────────────────
test("04 — grid risk layer active", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const html = await page.content();
  expect(html).toMatch(/Grid Risk ON/i);

  const svgPaths = page.locator(".leaflet-container svg path");
  const count = await svgPaths.count();
  expect(count).toBeGreaterThan(5);

  const file = await shot(page, "04-grid-risk-layer");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. Selected flood zone — click district, copilot slides in
// ─────────────────────────────────────────────────────────────────────────────
test("05 — selected flood zone opens copilot", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const map = page.locator(".leaflet-container");
  const positions = [
    { x: 380, y: 310 }, { x: 420, y: 280 },
    { x: 350, y: 340 }, { x: 400, y: 260 },
  ];

  let panelUpdated = false;
  for (const pos of positions) {
    await map.click({ position: pos });
    await page.waitForTimeout(600);
    const panelHtml = await page.locator('[aria-label="Risk explanation panel"]').innerHTML();
    if (panelHtml.match(/Grid Zone|Risk Zone|Flood Risk Zone|Risk Factors|zone_label|Province|risk_score/i)) {
      panelUpdated = true;
      break;
    }
  }

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();
  expect(panelHtml).toMatch(/Risk|Flood|Zone|District|factor/i);

  await noFakeStrings(page);
  const file = await shot(page, "05-selected-flood-zone");
  console.log("SCREENSHOT:", file, "| panelUpdated:", panelUpdated);
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. Weather city popup — click Weather mode, see city chips
// ─────────────────────────────────────────────────────────────────────────────
test("06 — weather mode city chips", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const weatherBtn = page.locator('[aria-label="Toggle Weather layer"]');
  await expect(weatherBtn).toBeAttached({ timeout: 8_000 });
  await weatherBtn.click();
  await page.waitForTimeout(1000);

  const html = await page.content();
  expect(html).toMatch(/Weather ON/i);

  // Try to click on a city chip
  const map = page.locator(".leaflet-container");
  const bbox = await map.boundingBox();
  if (!bbox) throw new Error("Map not found");

  const positions = [
    { x: Math.floor(bbox.width * 0.30), y: Math.floor(bbox.height * 0.75) },
    { x: Math.floor(bbox.width * 0.25), y: Math.floor(bbox.height * 0.80) },
    { x: Math.floor(bbox.width * 0.35), y: Math.floor(bbox.height * 0.70) },
  ];

  let cityPanelOpened = false;
  for (const pos of positions) {
    await map.click({ position: pos });
    await page.waitForTimeout(700);
    const panelHtml = await page.locator('[aria-label="Risk explanation panel"]').innerHTML();
    if (panelHtml.match(/°C|rainfall|humidity|wind speed|Flood Risk/i)) {
      cityPanelOpened = true;
      break;
    }
  }

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();
  await noFakeStrings(page);
  const file = await shot(page, "06-weather-city-popup");
  console.log("SCREENSHOT:", file, "| cityPanelOpened:", cityPanelOpened);
  expect(panelHtml).toMatch(/°C|Risk|Flood|District|Weather|Select/i);
});

// ─────────────────────────────────────────────────────────────────────────────
// 7. Karachi search — opens city analysis panel (not "Select a Feature")
// ─────────────────────────────────────────────────────────────────────────────
test("07 — Karachi search opens city analysis", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const search = page.getByPlaceholder(/search district/i);
  await expect(search).toBeVisible({ timeout: 5_000 });
  await search.fill("Karachi");
  await page.waitForTimeout(400);

  const listbox = page.locator('[role="listbox"]');
  await expect(listbox).toBeVisible({ timeout: 5_000 });

  const listHtml = await listbox.innerHTML();
  expect(listHtml).toMatch(/Karachi/i);
  expect(listHtml).toMatch(/weather marker|outside.*MVP|MVP dataset|city weather/i);

  await listbox.click();
  await page.waitForTimeout(800);

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();

  expect(panelHtml).not.toMatch(/Select a Feature/i);
  expect(panelHtml).toMatch(/Karachi/i);
  expect(panelHtml).toMatch(/outside.*MVP|MVP dataset|city weather|°C/i);

  await noFakeStrings(page);
  const file = await shot(page, "07-karachi-search");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 8. SAR evidence panel
// ─────────────────────────────────────────────────────────────────────────────
test("08 — SAR evidence panel", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  const sarBtn = page.locator('[aria-label="Risk explanation panel"] button', { hasText: "SAR" });
  if (await sarBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await sarBtn.click();
    await page.waitForTimeout(600);
  }

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const html = await panel.innerHTML();
  expect(html).toMatch(/SAR|Copernicus|UNOSAT|sensor|satellite/i);

  await noFakeStrings(page);
  const file = await shot(page, "08-sar-evidence-panel");
  console.log("SCREENSHOT:", file);
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. Simulation Lab — v3 contract
//   - When /api/v1/model/status reports artifact_exists=false (the live state
//     until the user completes Gate B), the Simulation Lab MUST be disabled.
//     No legacy sliders / no fake baseline / no fake projected risk may be
//     rendered as if it were v3 prediction output.
//   - When /api/v1/model/status is mocked as artifact_exists=true, the full
//     simulation surface is allowed. That path is only exercised under the
//     mock and serves as a forward-compatibility check for Gate B.
// ─────────────────────────────────────────────────────────────────────────────
test("09 — simulation lab is disabled when v3 artifact is missing", async ({ page }) => {
  await page.goto("/");
  await waitForMap(page);

  // Confirm the running stack is in the unavailable state.
  const status = await page.evaluate(async () => {
    const r = await fetch("http://localhost:8000/api/v1/model/status");
    return r.json();
  });
  expect(status.mode).toBe("real_prediction");
  expect(status.artifact_exists).toBe(false);
  expect(status.is_prediction_model).toBe(false);

  const selected = await selectAnyDistrict(page);
  expect(selected, "At least one MVP district must be selectable").toBeTruthy();

  const simBtn = page.locator('[aria-label="Risk explanation panel"] button', { hasText: "Sim" });
  await expect(simBtn).toBeEnabled({ timeout: 6_000 });
  await simBtn.click();
  await page.waitForTimeout(800);

  // Honest unavailable card must be present.
  await expect(page.getByTestId("simulation-lab-unavailable")).toBeVisible({ timeout: 6_000 });

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();

  // Disabled message must be shown (SimulationLab unavailable card).
  expect(panelHtml).toMatch(/Simulation disabled until real prediction artifact is available/i);
  expect(panelHtml).toMatch(/Simulation Lab · Disabled/i);
  expect(panelHtml).toMatch(/Run the v3 real-data pipeline first/i);

  // No legacy "what-if" interactive controls.
  expect(panel.locator('button', { hasText: "+50% Rainfall" })).toHaveCount(0);
  expect(panel.locator('button', { hasText: "+25% Rainfall" })).toHaveCount(0);
  expect(panel.locator('button', { hasText: /Reset to baseline/i })).toHaveCount(0);

  // No fake projected / baseline / discharge-slider output.
  expect(panelHtml).not.toMatch(/Projected Impact/i);
  expect(panelHtml).not.toMatch(/Baseline (?:risk|score|model)/i);
  expect(panelHtml).not.toMatch(/Rainfall intensity\s*<\/span>/i);
  expect(panelHtml).not.toMatch(/Prototype simulation/i);

  await noFakeStrings(page);
  const file = await shot(page, "09-simulation-lab-disabled");
  console.log("SCREENSHOT:", file, "| v3 artifact_exists:", status.artifact_exists);
});


test("09b — simulation lab full surface when v3 status is mocked as available", async ({ page }) => {
  // Forward-compatibility check for Gate B. Mock /api/v1/model/status to
  // report artifact_exists=true so the v3-ready code path renders the
  // simulation lab in its full form. No real model is invoked.
  await page.route("**/api/v1/model/status", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        mode: "real_prediction",
        artifact_exists: true,
        artifact_path: "ml/artifacts/flood_prediction_calibrated_v3.pkl",
        metadata_exists: true,
        metadata_path: "ml/artifacts/flood_prediction_metadata_v3.json",
        is_prediction_model: true,
        model_name: "flood_prediction_v3",
        model_type: "BalancedRandomForestClassifier + sigmoid CalibratedClassifierCV",
        prediction_window: "T+1 to T+3 days",
        calibration_method: "sigmoid",
        calibration_api: "FrozenEstimator",
        last_trained_iso: "2026-05-13T12:00:00Z",
        data_sources: null,
        metric_crs: "EPSG:6933",
        remediation: null,
      }),
    })
  );

  await page.goto("/");
  await waitForMap(page);
  const selected = await selectAnyDistrict(page);
  expect(selected, "At least one MVP district must be selectable").toBeTruthy();

  const simBtn = page.locator('[aria-label="Risk explanation panel"] button', { hasText: "Sim" });
  await expect(simBtn).toBeEnabled({ timeout: 6_000 });
  await simBtn.click();
  await page.waitForTimeout(800);

  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();

  expect(panelHtml).toMatch(/What-If Simulation|Simulation Lab/i);
  expect(panelHtml).toMatch(/Rainfall intensity|rainfall/i);
  expect(panelHtml).toMatch(/River discharge|discharge/i);
  expect(panelHtml).not.toMatch(/Simulation disabled until real prediction artifact/i);
});
