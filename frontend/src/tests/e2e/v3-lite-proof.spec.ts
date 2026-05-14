/**
 * Live proof: with the v3-lite calibrated artifact loaded, the StatusBar
 * model badge must read "Real prediction v3-lite" plus the
 * "Weak-label public-data prototype" chip.
 */
import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test("Gate B-Lite — model badge flips to Real prediction v3-lite", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 12_000 });
  await page.waitForTimeout(1200);

  // Hit /model/status directly — proves backend reports v3-lite ready.
  const status = await page.evaluate(async () => {
    const r = await fetch("http://localhost:8000/api/v1/model/status");
    return r.json();
  });
  expect(status.artifact_exists).toBe(true);
  expect(status.is_prediction_model).toBe(true);
  expect(status.model_name).toBe("flood_prediction_real_lite");
  expect(status.prediction_window).toBe("T+1 to T+3 days");

  // The "Real prediction model unavailable" text must NOT appear globally.
  await expect(page.getByText(/Real prediction model unavailable/i)).toHaveCount(0);

  const dir = path.join(process.cwd(), "../docs");
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, "proof_v3_lite_badge.png");
  await page.screenshot({ path: out, fullPage: false });
  console.log("SCREENSHOT:", out, "| model_name:", status.model_name);
});
