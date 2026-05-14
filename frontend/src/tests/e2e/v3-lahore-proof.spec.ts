/**
 * Live proof: with the v3 calibrated artifact missing, selecting Lahore must
 * NOT surface fake risk numbers / pills / factor bars. Captures a screenshot
 * to docs/proof_lahore_v3_unavailable.png and asserts the unavailable card
 * is in the DOM.
 */
import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test("Lahore selected → RiskBrief shows v3 unavailable state", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".leaflet-container")).toBeVisible({ timeout: 12_000 });
  await page.waitForTimeout(1500);

  // 1) Confirm /model/status reports artifact_exists=false.
  const status = await page.evaluate(async () => {
    const r = await fetch("http://localhost:8000/api/v1/model/status");
    return r.json();
  });
  expect(status.artifact_exists).toBe(false);
  expect(status.is_prediction_model).toBe(false);

  // 2) Type Lahore into the search and click the listbox item.
  const search = page.getByPlaceholder(/search district/i);
  await search.fill("Lahore");
  const listbox = page.locator('[role="listbox"]');
  await listbox.waitFor({ state: "visible", timeout: 7_000 });
  await listbox.locator("li").first().click();
  await page.waitForTimeout(800);

  // 3) Assert the RiskBrief unavailable card is in the DOM.
  await expect(page.getByTestId("risk-brief-unavailable")).toBeVisible({ timeout: 6_000 });

  // 4) Assert the fake legacy strings are NOT in the panel.
  const panel = page.locator('[aria-label="Risk explanation panel"]');
  const panelHtml = await panel.innerHTML();
  expect(panelHtml).not.toMatch(/\b38%\b/);
  expect(panelHtml).not.toMatch(/>HIGH</);   // the bold uppercase pill
  expect(panelHtml).not.toMatch(/Confidence[^A-Z]+\d+%/);
  expect(panelHtml).toMatch(/Real prediction model unavailable/i);

  // 5) Capture a screenshot.
  const dir = path.join(process.cwd(), "../docs");
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, "proof_lahore_v3_unavailable.png");
  await page.screenshot({ path: out, fullPage: false });
  // Also write a short summary the user can grep for.
  fs.writeFileSync(out + ".txt",
    `lahore_v3_proof\nmodel_status.artifact_exists=${status.artifact_exists}\n` +
    `model_status.is_prediction_model=${status.is_prediction_model}\n` +
    `risk-brief-unavailable testid visible: YES\n` +
    `38% present: NO\nHIGH pill present: NO\nReal prediction model unavailable text present: YES\n`
  );
  console.log("SCREENSHOT:", out);
});
