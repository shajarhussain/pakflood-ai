/**
 * Live proof for Phase 10 dataset-based model.
 *
 * /api/v1/model/status should report:
 *   model_name === "flood_prediction_dataset_based"
 *   artifact_exists === true
 *   is_prediction_model === true
 * The header should show the "REAL · DATASET-BASED" pill.
 */
import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test("Phase 10 — dataset-based model badge", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 12_000 });
  await page.waitForTimeout(1200);

  const status = await page.evaluate(async () => {
    const r = await fetch("http://localhost:8000/api/v1/model/status");
    return r.json();
  });
  expect(status.artifact_exists).toBe(true);
  expect(status.is_prediction_model).toBe(true);
  expect(status.model_name).toBe("flood_prediction_dataset_based");
  expect(status.model_scope).toContain("dataset-based");

  await expect(page.getByText(/Real prediction model unavailable/i)).toHaveCount(0);

  const dir = path.join(process.cwd(), "../docs");
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, "proof_dataset_based_badge.png");
  await page.screenshot({ path: out, fullPage: false });
  console.log("SCREENSHOT:", out, "| model_name:", status.model_name);
});
